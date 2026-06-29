import json
import shutil
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd
from datasets import load_dataset

from src.execute.validator import Validator

LANG = {0: "unknown", 1: "python2", 2: "cpp", 3: "python3", 4: "java"}
SOURCE = {0: "unknown", 1: "codechef", 2: "codeforces", 3: "hackerearth", 4: "atcoder", 5: "aizu"}


class Builder:
    # Load the CodeContests test split (post-2021-09-21, contamination-clean), keep Codeforces
    # problems, and for each one validate its C++ submissions with the sandbox: corrects must judge
    # AC (the oracle / judgeability gate), incorrects must judge non-AC (confirmed human bugs). A
    # problem is kept only if it yields >= min_correct AC corrects AND >= min_incorrect non-AC
    # incorrects; only validated submissions are stored under data/<id>/. Non-C++ code is not stored
    # (its counts live in dataset_stats.json / manifest.csv).
    def __init__(self, config):
        self.config = config
        b = config["build"]
        self.dataset = b["dataset"]
        self.split = b["split"]
        self.cf_source = b["source_codeforces"]
        self.cpp = LANG.get(b["cpp_language"], "cpp")
        self.min_correct = b["min_correct"]
        self.min_incorrect = b["min_incorrect"]
        self.workers = b["workers"]
        self.out = Path(config["paths"]["data"])
        self.validator = Validator(config)

    def run(self):
        rows = list(self._load())
        stats = self._stats(rows)
        cf = [ex for ex in rows if ex["source"] == self.cf_source]
        with ThreadPoolExecutor(max_workers=self.workers) as pool:
            results = list(pool.map(self._process_problem, cf))
        kept = [r for r in results if r["kept"]]
        dropped = Counter(r["drop_reason"] for r in results if not r["kept"])
        # label-vs-sandbox disagreement totals over every judged C++ submission
        cj, ca = sum(r["cj"] for r in results), sum(r["ca"] for r in results)
        ij, ia = sum(r["ij"] for r in results), sum(r["ia"] for r in results)
        disagree = {"correct_judged": cj, "correct_disagree": cj - ca,
                    "correct_disagree_pct": round(100 * (cj - ca) / cj, 2) if cj else 0.0,
                    "incorrect_judged": ij, "incorrect_disagree_unexpected_ac": ia,
                    "incorrect_disagree_pct": round(100 * ia / ij, 2) if ij else 0.0}
        stats["kept_problems"] = len(kept)
        stats["dropped"] = dict(dropped)
        stats["disagreement"] = disagree
        self._write_stats(stats)
        self._write_manifest([r["manifest"] for r in kept])
        return {"test_problems": len(rows), "codeforces": len(cf), "kept_problems": len(kept),
                "dropped": dict(dropped), "disagreement": disagree, "out": str(self.out)}

    def _process_problem(self, ex):
        pid = self._pid(ex)
        d = self.out / pid
        d.mkdir(parents=True, exist_ok=True)
        (d / "description.txt").write_text(ex["description"], encoding="utf-8")
        self._write_jsonl(d / "tests.jsonl", self._tests(ex))
        self._write_meta(d, pid, ex)                       # judge() needs meta.json + tests.jsonl

        correct = self._by_lang(ex["solutions"]).get(self.cpp, [])
        incorrect = self._by_lang(ex["incorrect_solutions"]).get(self.cpp, [])

        # validate EVERY correct; keep those our sandbox confirms AC (drop label disagreements).
        # cj/ca/ij/ia = corrects judged / corrects AC / incorrects judged / incorrects AC(unexpected),
        # carried for every problem (kept or dropped) so run() can total the label disagreements.
        ac = [s for s in correct if self.validator.judge(d, s)["verdict"] == "AC"]
        res = {"problem_id": pid, "cj": len(correct), "ca": len(ac), "ij": 0, "ia": 0}
        # if none judge AC, the problem is not exactly judgeable -> delete it.
        if len(ac) < self.min_correct:
            shutil.rmtree(d)
            return {**res, "kept": False, "drop_reason": "not_judgeable"}

        # validate EVERY incorrect; keep those our sandbox confirms non-AC (drop unexpected-AC).
        bugs = [s for s in incorrect if self.validator.judge(d, s)["verdict"] != "AC"]
        res.update(ij=len(incorrect), ia=len(incorrect) - len(bugs))
        if len(bugs) < self.min_incorrect:
            shutil.rmtree(d)
            return {**res, "kept": False, "drop_reason": "too_few_bugs"}

        self._write_jsonl(d / "correct.jsonl", [{"source": s} for s in ac])
        self._write_jsonl(d / "incorrect.jsonl", [{"source": s} for s in bugs])
        self._write_meta(d, pid, ex, n_correct=len(ac), n_correct_dropped=res["cj"] - res["ca"],
                         n_incorrect=len(bugs), n_incorrect_dropped=res["ia"])
        return {**res, "kept": True, "drop_reason": None,
                "manifest": {"problem_id": pid, "cf_rating": ex["cf_rating"],
                             "cf_tags": "|".join(ex["cf_tags"]), "difficulty": ex["difficulty"],
                             "n_correct": len(ac), "n_correct_dropped": res["cj"] - res["ca"],
                             "n_incorrect": len(bugs), "n_incorrect_dropped": res["ia"]}}

    def _load(self):
        return load_dataset(self.dataset, split=self.split, streaming=True)

    def _pid(self, ex):
        return f"{ex['cf_contest_id']}{ex['cf_index']}"

    def _by_lang(self, sols):
        out = {}
        for code, src in zip(sols["language"], sols["solution"]):
            out.setdefault(LANG.get(code, str(code)), []).append(src)
        return out

    def _tests(self, ex):
        rows = []
        for kind in ("public", "private", "generated"):
            t = ex[f"{kind}_tests"]
            for inp, outp in zip(t["input"], t["output"]):
                rows.append({"input": inp, "output": outp, "kind": kind})
        return rows

    def _write_meta(self, d, pid, ex, **extra):
        tl = ex.get("time_limit") or {}
        meta = {"problem_id": pid, "name": ex["name"], "source": SOURCE.get(ex["source"]),
                "cf_contest_id": ex["cf_contest_id"], "cf_index": ex["cf_index"],
                "cf_rating": ex["cf_rating"], "cf_tags": list(ex["cf_tags"]),
                "difficulty": ex["difficulty"],
                "time_limit_s": tl.get("seconds", 0) + tl.get("nanos", 0) / 1e9,
                "memory_limit_bytes": ex["memory_limit_bytes"],
                "n_tests": {k: len(ex[f"{k}_tests"]["input"]) for k in ("public", "private", "generated")},
                **extra}
        (d / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    def _stats(self, rows):
        by_source = Counter(SOURCE.get(r["source"], str(r["source"])) for r in rows)
        corr, incorr = Counter(), Counter()
        for r in rows:
            for c in r["solutions"]["language"]:
                corr[LANG.get(c, str(c))] += 1
            for c in r["incorrect_solutions"]["language"]:
                incorr[LANG.get(c, str(c))] += 1
        cf = [r for r in rows if r["source"] == self.cf_source]
        ratings = [r["cf_rating"] for r in cf if r["cf_rating"]]
        return {"dataset": self.dataset, "split": self.split, "total_problems": len(rows),
                "by_source": dict(by_source), "codeforces_problems": len(cf),
                "submissions_by_language": {"correct": dict(corr), "incorrect": dict(incorr)},
                "cf_rating": ({"min": min(ratings), "max": max(ratings), "n_rated": len(ratings)}
                              if ratings else None)}

    def _write_jsonl(self, path, rows):
        with path.open("w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")

    def _write_stats(self, stats):
        self.out.mkdir(parents=True, exist_ok=True)
        (self.out / "dataset_stats.json").write_text(
            json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")

    def _write_manifest(self, manifest):
        self.out.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(manifest).to_csv(self.out / "manifest.csv", index=False)
