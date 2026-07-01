import hashlib
import json
import tempfile
from pathlib import Path

from src.execute.sandbox import Sandbox


class Validator:
    # Compile + run an untrusted C++ submission against a problem's tests and return a verdict
    # (CE > RE > TLE > WA > AC) with rich signals (first failing test, per-test vector, peak time).
    # Results are cached by (problem_id, hash(source), language) so re-runs are free and deterministic.
    def __init__(self, config):
        self.config = config
        self.sandbox = Sandbox(config)
        self.cache = Path(config["paths"]["artifacts"]) / "exec_cache"
        self.cap = config["execution"]["first_failing_cap_chars"]
        self.default_tl = config["execution"]["default_time_limit_s"]

    def judge(self, problem_dir, source, language="cpp"):
        problem_dir = Path(problem_dir)
        meta = json.loads((problem_dir / "meta.json").read_text(encoding="utf-8"))
        tests = [json.loads(l) for l in
                 (problem_dir / "tests.jsonl").read_text(encoding="utf-8").split("\n") if l]
        key = self._key(meta["problem_id"], source, language, tests)
        cached = self._read_cache(key)
        if cached is not None:
            return cached
        tl = meta.get("time_limit_s") or self.default_tl
        result = self._execute(source, tests, tl)
        self._write_cache(key, result)
        return result

    def public_results(self, problem_dir, source, language="cpp"):
        # Run the submission on the PUBLIC example tests only and return each test's actual output
        # (no early stop). This is the feedback a contestant sees for the samples on an online judge,
        # and is what self-refine is given. Distinct from judge(), which decides AC over all tests.
        problem_dir = Path(problem_dir)
        meta = json.loads((problem_dir / "meta.json").read_text(encoding="utf-8"))
        tests = [json.loads(l) for l in
                 (problem_dir / "tests.jsonl").read_text(encoding="utf-8").split("\n") if l]
        pub = [t for t in tests if t.get("kind") == "public"]
        tl = meta.get("time_limit_s") or self.default_tl
        with tempfile.TemporaryDirectory() as td:
            workdir = Path(td)
            ok, cerr, binp = self.sandbox.compile_cpp(source, workdir)
            if not ok:
                return {"compiled": False, "compiler_stderr": cerr[:self.cap], "tests": []}
            out = []
            for t in pub:
                res = self.sandbox.run([str(binp)], t["input"], tl, workdir)
                out.append({"input": t["input"][:self.cap], "expected": t["output"][:self.cap],
                            "actual": res["stdout"][:self.cap], "pass": self._classify(res, t["output"]) == "AC"})
            return {"compiled": True, "compiler_stderr": "", "tests": out}

    def _execute(self, source, tests, tl):
        with tempfile.TemporaryDirectory() as td:
            workdir = Path(td)
            ok, cerr, binp = self.sandbox.compile_cpp(source, workdir)
            if not ok:
                return self._result("CE", compiler_stderr=cerr)
            cmd = [str(binp)]
            per_test, peak = [], 0
            for i, t in enumerate(tests):
                res = self.sandbox.run(cmd, t["input"], tl, workdir)
                peak = max(peak, res["time_ms"])
                verdict = self._classify(res, t["output"])
                per_test.append({"idx": i, "pass": verdict == "AC"})
                if verdict != "AC":
                    return self._result(verdict, per_test=per_test, peak_time_ms=peak,
                                        runtime_error=(res["stderr"] if verdict == "RE" else None),
                                        first_failing_test={"input": t["input"][:self.cap],
                                                            "expected": t["output"][:self.cap],
                                                            "actual": res["stdout"][:self.cap]})
            return self._result("AC", per_test=per_test, peak_time_ms=peak)

    def _classify(self, res, expected):
        if res["timed_out"]:
            return "TLE"
        if res["returncode"] != 0:
            return "RE"
        return "AC" if self._match(res["stdout"], expected) else "WA"

    def _match(self, got, expected):
        # whitespace-token comparison matching competitive conventions: case-insensitive
        # (YES/No etc.), numeric tokens at 1e-4 tolerance (stored answers are approximations).
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

    def _result(self, verdict, first_failing_test=None, compiler_stderr=None,
                runtime_error=None, peak_time_ms=0, per_test=None):
        return {"verdict": verdict, "first_failing_test": first_failing_test,
                "compiler_stderr": compiler_stderr, "runtime_error": runtime_error,
                "peak_time_ms": peak_time_ms, "peak_mem_kb": 0, "per_test": per_test or []}

    def _key(self, problem_id, source, language, tests):
        # the test set is part of the key: changing which tests are used (e.g. dropping generated)
        # must not reuse a verdict computed against a different suite
        th = hashlib.sha256(json.dumps(tests, sort_keys=True).encode("utf-8")).hexdigest()[:16]
        blob = f"{problem_id}\x00{language}\x00{th}\x00{source}"
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()

    def _read_cache(self, key):
        f = self.cache / f"{key}.json"
        return json.loads(f.read_text(encoding="utf-8")) if f.exists() else None

    def _write_cache(self, key, result):
        self.cache.mkdir(parents=True, exist_ok=True)
        (self.cache / f"{key}.json").write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
