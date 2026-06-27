import csv
import json
from pathlib import Path

import pandas as pd
from huggingface_hub import HfApi, hf_hub_download

from src.common.paths import Paths
from src.taxonomy.taxonomy import families_for_tags


class ProblemSetBuilder:
    # code_contests enums
    LANG = {"cpp": 2, "python3": 3}
    SOURCE_CODEFORCES = 2
    COLS = ["name", "description", "public_tests", "private_tests", "generated_tests",
            "solutions", "incorrect_solutions", "source", "difficulty",
            "cf_contest_id", "cf_index", "cf_rating", "cf_tags", "cf_points",
            "time_limit", "memory_limit_bytes"]

    def __init__(self, config):
        self.config = config
        self.paths = Paths(config)
        self.bins = config["difficulty_bins"]

    def run(self):
        self.paths.ensure()
        test = self._load_split(self.config["dataset"]["split"])
        rows = self._build(test, self.paths.data / "problems")
        self._write_manifest(rows, self.paths.data / "problems" / "manifest.csv")
        # validation split: kept separate for the contamination sensitivity probe only
        sens = self._load_split(self.config["dataset"]["sensitivity_split"])
        self._build(sens, self.paths.data / "sensitivity")
        self._report(rows)

    def _build(self, df, out_root):
        cf = df[df["source"] == self.SOURCE_CODEFORCES]
        return [self._write_problem(r, out_root) for _, r in cf.iterrows()]

    def _write_problem(self, r, out_root):
        pid = f"{int(r['cf_contest_id'])}{r['cf_index']}"
        d = out_root / pid
        d.mkdir(parents=True, exist_ok=True)
        tests = self._tests(r)
        self._write_jsonl(d / "tests.jsonl", tests)
        (d / "description.txt").write_text(self._s(r["description"]), encoding="utf-8")
        counts = {}
        for lang, code in self.LANG.items():
            ld = d / lang
            ld.mkdir(exist_ok=True)
            # code_contests provides only code+language; verdict/exec metrics are added by the
            # judge in later phases (userid/timestamp are not in the dataset)
            correct = [{"idx": i, "code": s} for i, s in enumerate(self._solutions(r["solutions"], code))]
            incorrect = [{"idx": i, "code": s} for i, s in enumerate(self._solutions(r["incorrect_solutions"], code))]
            self._write_jsonl(ld / "correct.jsonl", correct)
            self._write_jsonl(ld / "incorrect.jsonl", incorrect)
            counts[f"n_correct_{lang}"] = len(correct)
            counts[f"n_incorrect_{lang}"] = len(incorrect)
        meta = {
            "problem_id": pid, "name": self._s(r["name"]),
            "cf_rating": (None if pd.isna(r["cf_rating"]) else int(r["cf_rating"])),
            "difficulty_bin": self._difficulty_bin(r["cf_rating"]),
            "cf_tags": list(r["cf_tags"]) if r["cf_tags"] is not None else [],
            "algo_families": self._algo_families(r["cf_tags"]),
            "source": "CODEFORCES",
            "time_limit_s": self._time_limit(r["time_limit"]),
            "memory_limit_mb": (None if pd.isna(r["memory_limit_bytes"]) else round(int(r["memory_limit_bytes"]) / 1e6, 1)),
            "n_public": sum(1 for t in tests if t["kind"] == "public"),
            "n_private": sum(1 for t in tests if t["kind"] == "private"),
            "n_generated": sum(1 for t in tests if t["kind"] == "generated"),
            "n_tests": len(tests),
            **counts,
        }
        (d / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
        return meta

    def _tests(self, r):
        tests = []
        for key, kind in (("public_tests", "public"), ("private_tests", "private"), ("generated_tests", "generated")):
            t = r[key]
            if t is None or "input" not in t:
                continue
            for inp, out in zip(t["input"], t["output"]):
                tests.append({"kind": kind, "input": self._s(inp), "output": self._s(out)})
        return tests

    def _solutions(self, sols, lang_code):
        if sols is None:
            return []
        return [self._s(s) for lg, s in zip(list(sols["language"]), list(sols["solution"]))
                if int(lg) == lang_code]

    def _difficulty_bin(self, rating):
        if pd.isna(rating):
            return None
        r = int(rating)
        for i, e in enumerate(self.bins["edges"]):
            if r < e:
                return self.bins["labels"][i]
        return self.bins["labels"][-1]

    def _algo_families(self, tags):
        return families_for_tags(tags)

    def _write_jsonl(self, path, records):
        with open(path, "w", encoding="utf-8") as f:
            for rec in records:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    def _write_manifest(self, rows, path):
        path.parent.mkdir(parents=True, exist_ok=True)
        cols = ["problem_id", "cf_rating", "difficulty_bin", "algo_families", "cf_tags",
                "n_public", "n_private", "n_generated", "n_tests",
                "n_correct_cpp", "n_correct_python3", "n_incorrect_cpp", "n_incorrect_python3"]
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(cols)
            for m in rows:
                w.writerow([m["problem_id"], m["cf_rating"], m["difficulty_bin"],
                            "|".join(m["algo_families"]), "|".join(m["cf_tags"]),
                            m["n_public"], m["n_private"], m["n_generated"], m["n_tests"],
                            m["n_correct_cpp"], m["n_correct_python3"],
                            m["n_incorrect_cpp"], m["n_incorrect_python3"]])

    def _report(self, rows):
        n = len(rows)
        print(json.dumps({
            "problems": n,
            "missing_oracle": sum(1 for m in rows if m["n_correct_cpp"] + m["n_correct_python3"] == 0),
            "missing_tests": sum(1 for m in rows if m["n_tests"] == 0),
            "with_incorrect_cpp": sum(1 for m in rows if m["n_incorrect_cpp"] > 0),
            "with_incorrect_python3": sum(1 for m in rows if m["n_incorrect_python3"] > 0),
        }, ensure_ascii=False), flush=True)

    def _load_split(self, split):
        fn = self._split_file(split)
        path = hf_hub_download(self.config["dataset"]["name"], fn, repo_type="dataset")
        return pd.read_parquet(path, columns=self.COLS)

    def _split_file(self, split):
        files = HfApi().list_repo_files(self.config["dataset"]["name"], repo_type="dataset")
        return sorted(f for f in files if f.startswith(f"data/{split}-") and f.endswith(".parquet"))[0]

    def _time_limit(self, tl):
        if tl is None:
            return self.config["execution"]["default_time_limit_s"]
        return round(float(tl.get("seconds", 0)) + float(tl.get("nanos", 0)) / 1e9, 2)

    def _s(self, x):
        return "" if x is None else str(x)
