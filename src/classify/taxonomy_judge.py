import json
import math
import re
from collections import Counter
from pathlib import Path

from src.common.llm_client import LlmClient
from src.judge.submission_judge import SubmissionJudge
from src.taxonomy.taxonomy import TAXONOMY, VERDICT_CANDIDATES

PROMPT = (
    "You are labeling a bug in a competitive-programming submission using a FIXED taxonomy.\n"
    "You may assign MULTIPLE leaves. Choose ONLY from the candidate set when possible.\n"
    'Return STRICT JSON: {{"leaves":["GE1.2"], "rationale":"...", "uncovered":false}}\n\n'
    "Problem: {description}\n"
    "Submission verdict: {verdict}\n"
    "First failing test: input={inp} expected={exp} actual={act}\n"
    "Compiler/runtime messages: {msg}\n"
    "Reference correct solution (for your judgment only): {oracle}\n"
    "Candidate leaves (from verdict): {candidates}\n"
    "Taxonomy with one example per leaf:\n{rubric}\n"
)


class TaxonomyJudge:
    # Phase E classification. Tier 1 narrows leaves by verdict; Tier 2 asks the (provenance-
    # blind) judge model to assign taxonomy leaves, with self-consistency over m samples
    # aggregated by majority vote. The arm (human/AI) is never put in the prompt.
    def __init__(self, config):
        self.config = config
        self.client = LlmClient(config)
        self.exec = SubmissionJudge(config)
        self.m = config["judge"]["m"]
        self.temperature = config["judge"].get("temperature", 0.4)
        self.max_tokens = config["judge"].get("max_tokens", 1024)
        self.size_cap = config["prompt"]["size_cap_chars"]
        self.lang = config["languages"]["primary"]
        self.problems = Path(config["paths"]["data"]) / "problems"
        self.rubric = self._rubric()

    @staticmethod
    def tier1_candidates(verdict):
        return VERDICT_CANDIDATES.get(verdict, list(TAXONOMY))

    def classify(self, submission, model, dry_run=False):
        prompt = self._prompt(submission)
        if dry_run:
            return {"submission_id": submission["submission_id"], "model": model,
                    "prompt_chars": len(prompt), "dry_run": True}
        samples = []
        for i in range(self.m):
            r = self.client.complete(model, [{"role": "user", "content": prompt}],
                                     temperature=self.temperature, max_tokens=self.max_tokens,
                                     n=1, nonce=i)
            samples.append(self._parse(r["texts"][0]))
        agg = self._aggregate(samples)
        return {"submission_id": submission["submission_id"], "problem_id": submission["problem_id"],
                "arm": submission.get("arm"), "verdict": submission["verdict"], "model": model,
                "leaves": agg["leaves"], "uncovered": agg["uncovered"],
                "needs_review": agg["needs_review"], "per_sample": [s["leaves"] for s in samples],
                "rationale": next((s["rationale"] for s in samples if s["rationale"]), "")}

    def _prompt(self, submission):
        pid = submission["problem_id"]
        v = self.exec.judge(self.problems / pid, submission["source"], self.lang)
        ff = v["first_failing_test"] or {}
        oracle = json.loads([l for l in (self.problems / pid / self.lang / "correct.jsonl")
                            .read_text(encoding="utf-8").split("\n") if l][0])["code"]
        desc = self._clip((self.problems / pid / "description.txt").read_text(encoding="utf-8"))
        msg = v.get("compiler_stderr") or v.get("runtime_error") or "(none)"
        return PROMPT.format(
            description=desc, verdict=submission["verdict"],
            inp=self._clip(ff.get("input", "(n/a)"), 800), exp=self._clip(ff.get("expected", "(n/a)"), 800),
            act=self._clip(ff.get("actual", "(n/a)"), 800), msg=self._clip(msg, 1200),
            oracle=self._clip(oracle), candidates=", ".join(self.tier1_candidates(submission["verdict"])),
            rubric=self.rubric)

    def _parse(self, text):
        leaves, rationale, uncovered = [], "", False
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if m:
            try:
                obj = json.loads(m.group(0))
                leaves = [c for c in obj.get("leaves", []) if c in TAXONOMY]
                rationale = str(obj.get("rationale", ""))[:500]
                uncovered = bool(obj.get("uncovered", False))
            except (ValueError, TypeError):
                pass
        return {"leaves": leaves, "rationale": rationale, "uncovered": uncovered}

    def _aggregate(self, samples):
        thresh = math.ceil(self.m / 2)
        counts = Counter(leaf for s in samples for leaf in set(s["leaves"]))
        leaves = sorted(c for c, k in counts.items() if k >= thresh)
        uncovered = sum(1 for s in samples if s["uncovered"]) >= thresh
        needs_review = not leaves and not uncovered
        return {"leaves": leaves, "uncovered": uncovered, "needs_review": needs_review}

    def _rubric(self):
        return "\n".join(f"{c} {v[0]}: {v[1]}" for c, v in TAXONOMY.items())

    def _clip(self, s, cap=None):
        cap = cap or self.size_cap
        s = s if s is not None else ""
        return s if len(s) <= cap else s[: cap // 2] + " …[clipped]… " + s[-cap // 2:]
