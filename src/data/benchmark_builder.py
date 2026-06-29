import json
from collections import Counter
from pathlib import Path

import pandas as pd
from datasets import load_dataset

LANG = {0: "unknown", 1: "python2", 2: "cpp", 3: "python3", 4: "java"}
SOURCE = {0: "unknown", 1: "codechef", 2: "codeforces", 3: "hackerearth", 4: "atcoder", 5: "aizu"}


class BenchmarkBuilder:
    # Phase A. Load the CodeContests test split (published post-2021-09-21, so contamination-clean
    # for gpt-3.5-turbo), keep Codeforces-sourced problems (only these carry cf_rating/cf_tags),
    # and store per problem its C++ correct (oracle) and incorrect (human-arm raw) solutions plus
    # all tests under benchmark/<id>/. Non-C++ submissions are counted in dataset_stats.json and the
    # manifest (descriptive language distribution) but their code is not stored.
    def __init__(self, config):
        self.config = config
        b = config["benchmark"]
        self.dataset = b["dataset"]
        self.split = b["split"]
        self.cf_source = b["source_codeforces"]
        self.cpp = b["cpp_language"]
        self.out = Path(config["paths"]["benchmark"])

    def run(self, limit=None):
        rows = []
        for i, ex in enumerate(self._load()):
            if limit and i >= limit:
                break
            rows.append(ex)
        stats = self._stats(rows)
        manifest = []
        for ex in rows:
            if ex["source"] != self.cf_source:
                continue
            pid = self._pid(ex)
            manifest.append(self._write_problem(pid, ex))
        stats["kept_codeforces_problems"] = len(manifest)
        self._write_stats(stats)
        self._write_manifest(manifest)
        return {"test_problems": len(rows), "kept_codeforces": len(manifest),
                "out": str(self.out)}

    def _load(self):
        # stream so only the test-split shards are fetched (not the full train split)
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

    def _cpp_name(self):
        return LANG.get(self.cpp, "cpp")

    def _write_problem(self, pid, ex):
        d = self.out / pid
        d.mkdir(parents=True, exist_ok=True)
        (d / "description.txt").write_text(ex["description"], encoding="utf-8")
        correct = self._by_lang(ex["solutions"])
        incorrect = self._by_lang(ex["incorrect_solutions"])
        cpp = self._cpp_name()
        self._write_jsonl(d / "tests.jsonl", self._tests(ex))
        self._write_jsonl(d / "correct.jsonl", [{"source": s} for s in correct.get(cpp, [])])
        self._write_jsonl(d / "incorrect.jsonl", [{"source": s} for s in incorrect.get(cpp, [])])
        tl = ex.get("time_limit") or {}
        meta = {"problem_id": pid, "name": ex["name"], "source": SOURCE.get(ex["source"]),
                "cf_contest_id": ex["cf_contest_id"], "cf_index": ex["cf_index"],
                "cf_rating": ex["cf_rating"], "cf_tags": list(ex["cf_tags"]),
                "difficulty": ex["difficulty"],
                "time_limit_s": tl.get("seconds", 0) + tl.get("nanos", 0) / 1e9,
                "memory_limit_bytes": ex["memory_limit_bytes"],
                "n_tests": {k: len(ex[f"{k}_tests"]["input"]) for k in ("public", "private", "generated")},
                "n_correct": {l: len(v) for l, v in correct.items()},
                "n_incorrect": {l: len(v) for l, v in incorrect.items()}}
        (d / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"problem_id": pid, "cf_rating": ex["cf_rating"],
                "cf_tags": "|".join(ex["cf_tags"]), "difficulty": ex["difficulty"],
                "n_public": meta["n_tests"]["public"], "n_private": meta["n_tests"]["private"],
                "n_generated": meta["n_tests"]["generated"],
                "n_correct_cpp": len(correct.get(cpp, [])),
                "n_incorrect_cpp": len(incorrect.get(cpp, [])),
                "n_incorrect_total": sum(len(v) for v in incorrect.values())}

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
                "by_source": dict(by_source),
                "codeforces_problems": len(cf),
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
