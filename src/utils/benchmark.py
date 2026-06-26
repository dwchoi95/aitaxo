"""Build the AIBugBench v0.2 dataset from DeepMind code_contests (HuggingFace).

code_contests' test/valid splits cover late-2021 Codeforces problems and, for each,
ship the full problem (statement + public/private/generated tests), the human CORRECT
solutions, and the human INCORRECT solutions WITH SOURCE -- a fair human bug baseline
(all failures, not near-miss filtered). We keep the leakage-free window (contests on
or after Codeforces Round 1575, 2021-10-04, i.e. after the Sep-2021 model cutoff and
before the Nov-2022 ChatGPT release) and Python 3 solutions, storing one self-contained
directory per problem.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
from huggingface_hub import HfApi, hf_hub_download


class Benchmark:
    REPO = "deepmind/code_contests"
    SPLITS = ("test", "valid")
    MIN_CONTEST = 1575          # 2021-10-04, first CF round safely after the Sep-2021 cutoff
    MAX_CONTEST = 1900          # well past code_contests' newest (1623); keeps the upper window open
    PY3 = 3                     # code_contests Language enum: PYTHON3
    MAX_TESTS = 100             # cap tests/problem (public+private first, then generated)

    COLS = ["name", "description", "public_tests", "private_tests", "generated_tests",
            "solutions", "incorrect_solutions", "cf_contest_id", "cf_index", "cf_rating",
            "cf_tags", "cf_points", "time_limit", "memory_limit_bytes"]

    def __init__(self, data_root: str = "data"):
        self.root = Path(data_root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.pids: list[str] = []
        self.api = HfApi()

    # ---- orchestration -------------------------------------------------------
    def build(self):
        self.fetch()
        self.write_manifest()
        return self.stats()

    def fetch(self):
        for split in self.SPLITS:
            for fn in self._split_files(split):
                path = hf_hub_download(self.REPO, fn, repo_type="dataset")
                df = pd.read_parquet(path, columns=self.COLS)
                w = df[(df.cf_contest_id >= self.MIN_CONTEST) & (df.cf_contest_id <= self.MAX_CONTEST)]
                n = 0
                for _, row in w.iterrows():
                    if self._write_problem(row):
                        n += 1
                print(f"[{split}] {fn.split('/')[-1]}: +{n} (total {len(self.pids)})", flush=True)

    def _write_problem(self, row) -> bool:
        human = self._py_solutions(row["incorrect_solutions"])
        correct = self._py_solutions(row["solutions"])
        tests = self._collect_tests(row)
        if not human or not correct or not tests:
            return False  # require a fair comparison point: >=1 human bug, >=1 correct, tests
        pid = f"{int(row['cf_contest_id'])}{row['cf_index']}"
        d = self.root / pid
        (d / "tests").mkdir(parents=True, exist_ok=True)
        for i, (inp, out) in enumerate(tests, 1):
            (d / "tests" / f"{i:03d}.in").write_text(inp, encoding="utf-8")
            (d / "tests" / f"{i:03d}.out").write_text(out, encoding="utf-8")
        (d / "statement.txt").write_text(self._s(row["description"]), encoding="utf-8")
        with (d / "human.jsonl").open("w", encoding="utf-8") as f:
            for i, src in enumerate(human):
                f.write(json.dumps({"idx": i, "source": src}, ensure_ascii=False) + "\n")
        with (d / "correct.jsonl").open("w", encoding="utf-8") as f:
            for i, src in enumerate(correct):
                f.write(json.dumps({"idx": i, "source": src}, ensure_ascii=False) + "\n")
        meta = {
            "pid": pid, "contest_id": int(row["cf_contest_id"]), "index": row["cf_index"],
            "name": self._s(row["name"]),
            "rating": (None if pd.isna(row["cf_rating"]) else int(row["cf_rating"])),
            "tags": list(row["cf_tags"]) if row["cf_tags"] is not None else [],
            "points": (None if pd.isna(row["cf_points"]) else float(row["cf_points"])),
            "time_limit_s": self._time_limit(row["time_limit"]),
            "memory_limit_mb": (None if pd.isna(row["memory_limit_bytes"])
                                else round(int(row["memory_limit_bytes"]) / 1e6, 1)),
            "n_tests": len(tests), "n_human": len(human), "n_correct": len(correct),
        }
        (d / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
        self.pids.append(pid)
        return True

    def _collect_tests(self, row):
        tests = []
        for key in ("public_tests", "private_tests", "generated_tests"):
            t = row[key]
            if t is None or "input" not in t:
                continue
            for inp, out in zip(t["input"], t["output"]):
                tests.append((self._s(inp), self._s(out)))
                if len(tests) >= self.MAX_TESTS:
                    return tests
        return tests

    def _py_solutions(self, sols):
        if sols is None:
            return []
        langs = list(sols.get("language", []))
        srcs = list(sols.get("solution", []))
        return [self._s(s) for lg, s in zip(langs, srcs) if int(lg) == self.PY3]

    # ---- manifest / stats ----------------------------------------------------
    def write_manifest(self):
        items = [json.loads((self.root / p / "meta.json").read_text(encoding="utf-8"))
                 for p in sorted(self.pids)]
        manifest = {"source": self.REPO, "window": "leakage-free (>= CF round 1575, 2021-10)",
                    "language": "Python 3", "n_problems": len(items), "problems": items}
        (self.root / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    def stats(self):
        items = [json.loads((self.root / p / "meta.json").read_text()) for p in sorted(self.pids)]
        import statistics
        s = {
            "problems": len(items),
            "human_bugs_total": sum(m["n_human"] for m in items),
            "correct_total": sum(m["n_correct"] for m in items),
            "human_per_problem_median": int(statistics.median([m["n_human"] for m in items])) if items else 0,
            "tests_per_problem_median": int(statistics.median([m["n_tests"] for m in items])) if items else 0,
            "contests": len({m["contest_id"] for m in items}),
        }
        print("[stats]", json.dumps(s, ensure_ascii=False), flush=True)
        return s

    # ---- load API ------------------------------------------------------------
    def load(self, pid: str):
        d = self.root / pid
        meta = json.loads((d / "meta.json").read_text(encoding="utf-8"))
        statement = (d / "statement.txt").read_text(encoding="utf-8")
        tests = [( (d / "tests" / f).read_text(encoding="utf-8"),
                   (d / "tests" / f.replace(".in", ".out")).read_text(encoding="utf-8") )
                 for f in sorted(x.name for x in (d / "tests").glob("*.in"))]
        human = [json.loads(l) for l in (d / "human.jsonl").read_text(encoding="utf-8").splitlines()]
        correct = [json.loads(l) for l in (d / "correct.jsonl").read_text(encoding="utf-8").splitlines()]
        return {"meta": meta, "statement": statement, "tests": tests, "human": human, "correct": correct}

    def iter_problems(self):
        for mp in sorted(self.root.glob("*/meta.json")):
            yield json.loads(mp.read_text(encoding="utf-8"))

    # ---- helpers -------------------------------------------------------------
    def _split_files(self, split: str) -> list[str]:
        files = self.api.list_repo_files(self.REPO, repo_type="dataset")
        return sorted(f for f in files if f.startswith(f"data/{split}-") and f.endswith(".parquet"))

    @staticmethod
    def _time_limit(tl):
        if tl is None:
            return None
        try:
            return round(float(tl.get("seconds", 0)) + float(tl.get("nanos", 0)) / 1e9, 2)
        except Exception:
            return None

    @staticmethod
    def _s(x) -> str:
        return "" if x is None else str(x)


if __name__ == "__main__":
    Benchmark().build()
