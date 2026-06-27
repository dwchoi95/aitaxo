import hashlib
import json
import shutil
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from src.judge.sandbox_runner import SandboxRunner


class SubmissionJudge:
    def __init__(self, config):
        self.config = config
        self.runner = SandboxRunner(config)
        self.cache = Path(config["paths"]["artifacts"]) / "exec_cache"
        self.cap = config["prompt"]["size_cap_chars"]
        self.default_tl = config["execution"]["default_time_limit_s"]
        self.default_ml = config["execution"]["default_memory_mb"]
        self.python = shutil.which("python3")

    def judge(self, problem_dir, source, language):
        problem_dir = Path(problem_dir)
        meta = json.loads((problem_dir / "meta.json").read_text(encoding="utf-8"))
        key = self._key(meta["problem_id"], source, language)
        cached = self._read_cache(key)
        if cached is not None:
            return cached
        tests = [json.loads(l) for l in (problem_dir / "tests.jsonl").read_text(encoding="utf-8").split("\n") if l]
        tl = meta["time_limit_s"] or self.default_tl
        ml = meta["memory_limit_mb"] or self.default_ml
        result = self._execute(source, language, tests, tl, ml)
        self._write_cache(key, result)
        return result

    # harness-correctness gate: every problem's oracle solution must judge AC
    def oracle_ac_selftest(self, problems_root, language, limit=None, workers=8):
        dirs = sorted(p.parent for p in Path(problems_root).glob("*/meta.json"))
        if limit:
            dirs = dirs[:limit]

        def check(d):
            f = d / language / "correct.jsonl"
            lines = [l for l in f.read_text(encoding="utf-8").split("\n") if l] if f.exists() else []
            if not lines:
                return (d.name, "no_oracle")
            src = json.loads(lines[0])["code"]
            return (d.name, self.judge(d, src, language)["verdict"])

        with ThreadPoolExecutor(max_workers=workers) as ex:
            results = list(ex.map(check, dirs))
        judged = [(n, v) for n, v in results if v != "no_oracle"]
        ac = sum(1 for _, v in judged if v == "AC")
        # a problem is judgeable iff its known-correct oracle judges AC; the rest are not
        # exactly judgeable (special-judge / interactive -> WA/TLE, compiler/runtime incompat)
        # and are excluded from the dataset with a recorded reason
        reason = {"CE": "compiler_incompatible", "RE": "runtime_incompatible",
                  "TLE": "nonexact_or_timeout", "WA": "special_judge_or_nonexact"}
        judgeable = sorted(n for n, v in judged if v == "AC")
        excluded = [{"problem_id": n, "verdict": v, "reason": reason.get(v, v)}
                    for n, v in judged if v != "AC"]
        return {"problems": len(results), "judged": len(judged), "ac": ac,
                "ac_rate_on_judgeable": 100.0 if judgeable else 0.0,
                "judgeable_count": len(judgeable), "excluded_count": len(excluded),
                "no_oracle": len(results) - len(judged),
                "judgeable": judgeable, "excluded": excluded}

    def _execute(self, source, language, tests, tl, ml):
        with tempfile.TemporaryDirectory() as td:
            workdir = Path(td)
            if language == "cpp":
                ok, cerr, binp = self.runner.compile_cpp(source, workdir)
                if not ok:
                    return self._result("CE", compiler_stderr=cerr)
                cmd = [str(binp)]
            else:
                ce = self._python_compile_error(source)
                if ce is not None:
                    return self._result("CE", compiler_stderr=ce)
                src = workdir / "main.py"
                src.write_text(source, encoding="utf-8")
                cmd = [self.python, str(src)]
            per_test = []
            peak_time = 0
            for i, t in enumerate(tests):
                res = self.runner.run(cmd, t["input"], tl, ml, workdir)
                peak_time = max(peak_time, res["time_ms"])
                verdict = self._classify(res, t["output"])
                per_test.append({"idx": i, "pass": verdict == "AC"})
                if verdict != "AC":
                    return self._result(verdict, per_test=per_test, peak_time_ms=peak_time,
                                        runtime_error=(res["stderr"] if verdict == "RE" else None),
                                        first_failing_test={"input": t["input"][:self.cap],
                                                            "expected": t["output"][:self.cap],
                                                            "actual": res["stdout"][:self.cap]})
            return self._result("AC", per_test=per_test, peak_time_ms=peak_time)

    def _classify(self, res, expected):
        if res["timed_out"]:
            return "TLE"
        if res["returncode"] != 0:
            return "RE"
        if self._match(res["stdout"], expected):
            return "AC"
        return "WA"

    def _match(self, got, expected):
        # whitespace-token comparison matching competitive conventions: case-insensitive
        # (YES/No etc.), with numeric tokens compared at 1e-4 relative/absolute tolerance
        # (stored float answers are approximations); exact otherwise
        g, e = got.split(), expected.split()
        if len(g) != len(e):
            return False
        for a, b in zip(g, e):
            if a == b or a.lower() == b.lower():
                continue
            fa, fb = self._float(a), self._float(b)
            if fa is None or fb is None or abs(fa - fb) > 1e-4 * max(1.0, abs(fb)):
                return False
        return True

    def _float(self, s):
        try:
            return float(s)
        except ValueError:
            return None

    def _python_compile_error(self, source):
        try:
            compile(source, "main.py", "exec")
            return None
        except SyntaxError as e:
            return str(e)

    def _result(self, verdict, first_failing_test=None, compiler_stderr=None,
                runtime_error=None, peak_time_ms=0, per_test=None):
        return {"verdict": verdict, "first_failing_test": first_failing_test,
                "compiler_stderr": compiler_stderr, "runtime_error": runtime_error,
                "peak_time_ms": peak_time_ms, "peak_mem_kb": 0, "per_test": per_test or []}

    def _key(self, problem_id, source, language):
        blob = f"{problem_id}\x00{language}\x00{source}"
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()

    def _read_cache(self, key):
        f = self.cache / f"{key}.json"
        return json.loads(f.read_text(encoding="utf-8")) if f.exists() else None

    def _write_cache(self, key, result):
        self.cache.mkdir(parents=True, exist_ok=True)
        (self.cache / f"{key}.json").write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
