import json
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from src.common.llm_client import LlmClient
from src.judge.submission_judge import SubmissionJudge

ZERO_SHOT = ("You are a competitive programmer. Solve the problem in {language}.\n"
             "Output ONLY one {language} code block; no explanation.\n"
             "Problem:\n{description}\n"
             "Input/Output format and constraints are in the statement above.\n"
             "Example test:\nInput: {sample_input}\nOutput: {sample_output}")

REPAIR = ("Your previous {language} solution was judged {VERDICT}.\n"
          "It failed this test:\nInput: {failing_input}\nExpected: {expected_output}\n"
          "Your output: {actual_output}\n"
          "Revise your solution. Output ONLY one corrected {language} code block.")


class AiGenerator:
    # Phase D: gpt-3.5-turbo C++ generation. Zero-shot = one temperature-1.0 batch of k_max
    # samples per problem (kept non-AC = the bug corpus). Self-reflection = an initial attempt
    # plus up to n_iters repair turns fed verdict + one failing test, whole trajectory kept.
    # No oracle is ever shown to the generator; provenance is stored outside the code payload.
    def __init__(self, config):
        self.config = config
        self.client = LlmClient(config)
        self.judge = SubmissionJudge(config)
        self.model = config["generator"]["snapshot"]
        self.temp = config["generator"]["temperature"]
        self.k_max = config["generator"]["k_max"]
        self.max_tokens = config["generator"]["max_tokens"]
        self.n_iters = config["self_reflection"]["n_iters"]
        self.cap = config["human_arm"]["cap_per_problem"]
        self.size_cap = config["prompt"]["size_cap_chars"]
        self.language = "C++"
        self.problems = Path(config["paths"]["data"]) / "problems"
        self.out = Path(config["paths"]["artifacts"]) / "ai_submissions"

    def run(self, limit=None, dry_run=False):
        pids = self._judgeable()
        if limit:
            pids = pids[:limit]
        (self.out / "zero_shot").mkdir(parents=True, exist_ok=True)
        (self.out / "self_reflection").mkdir(parents=True, exist_ok=True)
        with ThreadPoolExecutor(max_workers=8) as ex:
            rows = list(ex.map(lambda p: self._one(p, dry_run), pids))
        report = self._report(rows)
        (self.out / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        return report

    def _one(self, pid, dry_run):
        zs = self._zero_shot(pid, dry_run)
        sr = self._self_reflection(pid, dry_run)
        (self.out / "zero_shot" / f"{pid}.json").write_text(json.dumps(zs, ensure_ascii=False), encoding="utf-8")
        (self.out / "self_reflection" / f"{pid}.json").write_text(json.dumps(sr, ensure_ascii=False), encoding="utf-8")
        non_ac = [s for s in zs if s["verdict"] not in ("AC", "NO_CODE")][:self.cap]
        return {"problem_id": pid, "zero_shot": zs, "kept_non_ac": len(non_ac),
                "zs_ac": sum(1 for s in zs if s["verdict"] == "AC"),
                "zs_no_code": sum(1 for s in zs if s["verdict"] == "NO_CODE"),
                "sr_turns": len(sr), "sr_final": sr[-1]["verdict"] if sr else None}

    def _zero_shot(self, pid, dry_run):
        prompt = self._prompt(pid)
        r = self.client.complete(self.model, [{"role": "user", "content": prompt}],
                                 temperature=self.temp, max_tokens=self.max_tokens,
                                 n=self.k_max, dry_run=dry_run)
        if dry_run:
            return []
        out = []
        for i, text in enumerate(r["texts"]):
            out.append(self._judge_text(pid, i, text))
        return out

    def _self_reflection(self, pid, dry_run):
        msgs = [{"role": "user", "content": self._prompt(pid)}]
        traj = []
        for turn in range(self.n_iters + 1):
            r = self.client.complete(self.model, msgs, temperature=self.temp,
                                     max_tokens=self.max_tokens, n=1, dry_run=dry_run)
            if dry_run:
                return []
            text = r["texts"][0]
            rec = self._judge_text(pid, turn, text)
            traj.append(rec)
            if rec["verdict"] in ("AC", "NO_CODE") or turn == self.n_iters:
                break
            ff = rec.get("first_failing_test") or {}
            fb = REPAIR.format(language=self.language, VERDICT=rec["verdict"],
                               failing_input=self._clip(ff.get("input", "")),
                               expected_output=self._clip(ff.get("expected", "")),
                               actual_output=self._clip(ff.get("actual", "")))
            msgs = msgs + [{"role": "assistant", "content": text},
                          {"role": "user", "content": fb}]
        return traj

    def _judge_text(self, pid, idx, text):
        code = self._extract(text)
        if code is None:
            return {"attempt": idx, "code": None, "verdict": "NO_CODE"}
        v = self.judge.judge(self.problems / pid, code, "cpp")
        return {"attempt": idx, "code": code, "verdict": v["verdict"],
                "peak_time_ms": v["peak_time_ms"],
                "first_failing_test": v["first_failing_test"]}

    def _prompt(self, pid):
        d = self.problems / pid
        desc = self._clip((d / "description.txt").read_text(encoding="utf-8"))
        t0 = json.loads((d / "tests.jsonl").read_text(encoding="utf-8").split("\n")[0])
        return ZERO_SHOT.format(language=self.language, description=desc,
                                sample_input=self._clip(t0["input"]),
                                sample_output=self._clip(t0["output"]))

    def _extract(self, text):
        m = re.search(r"```(?:[a-zA-Z+]*)\n(.*?)```", text, re.DOTALL)
        if m:
            return m.group(1).strip() or None
        if "#include" in text or "int main" in text:
            return text.strip()
        return None

    def _clip(self, s):
        return s if len(s) <= self.size_cap else s[: self.size_cap // 2] + "\n...[clipped]...\n" + s[-self.size_cap // 2:]

    def _judgeable(self):
        f = Path(self.config["paths"]["artifacts"]) / "judgeable_problems.json"
        return sorted(json.loads(f.read_text(encoding="utf-8"))["judgeable"])

    def _report(self, rows):
        n = len(rows)
        zs_total = sum(len(r["zero_shot"]) for r in rows)
        return {"problems": n,
                "zero_shot_samples": zs_total,
                "zero_shot_ac": sum(r["zs_ac"] for r in rows),
                "zero_shot_no_code": sum(r["zs_no_code"] for r in rows),
                "kept_non_ac_total": sum(r["kept_non_ac"] for r in rows),
                "problems_with_ge1_non_ac": sum(1 for r in rows if r["kept_non_ac"] >= 1),
                "self_reflection_solved": sum(1 for r in rows if r["sr_final"] == "AC"),
                "per_problem": {r["problem_id"]: {"kept_non_ac": r["kept_non_ac"],
                                "zs_ac": r["zs_ac"], "sr_final": r["sr_final"]} for r in rows}}
