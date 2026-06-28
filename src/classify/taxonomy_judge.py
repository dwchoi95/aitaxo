import hashlib
import json
import math
import re
from collections import Counter
from pathlib import Path

from src.common.llm_client import LlmClient
from src.judge.submission_judge import SubmissionJudge
from src.taxonomy.taxonomy import TAXONOMY, VERDICT_CANDIDATES

PROMPT = (
    "You are a senior competitive-programming bug taxonomist. "
    "Label the bug in ONE failed C++ submission using a FIXED taxonomy.\n\n"

    "Your task is to identify the bug mechanism that best explains the FIRST failing test. "
    "Use the buggy submission as the primary evidence. Use the reference solution only to understand "
    "the intended algorithm/edge cases; do not label stylistic differences.\n\n"

    "Return STRICT JSON only, with no markdown:\n"
    '{{"primary":"AE1.1","secondary":[],"rationale":"..."}}\n\n'

    "Labeling rules:\n"
    "- primary must be exactly one leaf code, or \"UNCOVERED\" if no leaf clearly fits.\n"
    "- secondary is usually []. Add secondary leaf codes only for clearly distinct, independent bugs. "
    "Do NOT add downstream consequences, near-synonyms, or broad parent-like labels.\n"
    "- Prefer the most-specific leaf that explains the failure. If an AE* leaf precisely describes the bug, "
    "prefer it over generic GE1.1.\n"
    "- Do not infer labels from verdict alone. Verdict is only a weak hint.\n"
    "- Do not label the reference solution; label the submitted code.\n"
    "- If the evidence is ambiguous between a generic and a specific leaf, choose the specific leaf only when "
    "the submitted code shows that algorithmic pattern clearly.\n\n"

    "Important disambiguation:\n"
    "- GE1.1 Incorrect Algorithm: solves the right problem with a fundamentally wrong method/model.\n"
    "- GE1.2 Misunderstanding Requirements: use ONLY when the code is solving a different interpretation of "
    "the statement, ignoring a required constraint/output/objective, or assuming an input property not stated.\n"
    "- GE1.3 Inefficient Design: use for TLE caused by asymptotic inefficiency despite aiming at the right logic.\n"
    "- GE2.1 Compilation Errors: use for actual compile failure.\n"
    "- GE2.2 Language-specific Syntax Misuse: compiles, but C++ semantics/API/undefined behavior causes the bug.\n"
    "- GE3.1 Input Format Handling: wrong parsing, wrong number/order of tokens, treating test cases incorrectly.\n"
    "- GE3.2 Output Format Mismatch: computed content may be right, but printed shape/tokens/precision are wrong.\n"
    "- GE4.1 Edge/Boundary Handling: special case such as n=1, all equal, empty/min/max, first/last case mishandled.\n"
    "- GE4.2 Off-by-one/Indexing: wrong bounds, 0/1-index confusion, out-of-range access, wrong adjacent position.\n"
    "- GE5.1 Faulty Condition: a branch predicate is wrong while the intended structure is otherwise recognizable.\n"
    "- GE5.2 Logical Operators/Precedence: wrong &&/||/!, grouping, or boolean composition.\n"
    "- GE6.1 Overflow/Precision: wrong numeric type or precision causes the failure.\n"
    "- GE6.2 Implicit Conversion: silent C++ conversion/truncation/sign behavior changes the result.\n"
    "- AE1.* Math: wrong formula, modular arithmetic, parity/gcd/prime/combinatorics/probability derivation.\n"
    "- AE2.* Greedy: local choice/order/selection strategy is wrong or unjustified.\n"
    "- AE3.* DP: state, transition, or base initialization is wrong.\n"
    "- AE4.* Divide-and-conquer: base/merge/recursive split problem.\n"
    "- AE5.* Recursion/memoization: recursive base/merge/depth/memoization problem.\n"
    "- AE6.* Graph/search: traversal state, transitions, pruning, BFS/DFS/Dijkstra/visited handling.\n\n"

    "Decision procedure, follow internally:\n"
    "1. Locate the submitted-code behavior that causes the first failing test.\n"
    "2. Decide whether it is parsing/format/compile/runtime, boundary/indexing, control condition, datatype, "
    "or algorithmic reasoning.\n"
    "3. If algorithmic, choose the specific AE family when applicable; otherwise GE1.1/GE1.2/GE1.3.\n"
    "4. Add secondary only if another independent root bug would still remain after fixing the primary.\n\n"

    "Item id: {item_id}\n\n"
    "Problem statement:\n{description}\n\n"
    "Buggy submission code:\n```cpp\n{submission}\n```\n\n"
    "Submission verdict: {verdict}\n"
    "First failing test:\n"
    "input={inp}\n"
    "expected={exp}\n"
    "actual={act}\n"
    "Compiler/runtime messages:\n{msg}\n\n"
    "Reference correct solution, for judgment only:\n```cpp\n{oracle}\n```\n\n"
    "Weak verdict-based candidate hints, not restrictions:\n{candidates}\n\n"
    "Full taxonomy:\n{rubric}\n\n"
    "Rationale requirements: one or two concise sentences. Mention the concrete submitted-code mistake, "
    "not just the symptom."
)
UNCOVERED = "UNCOVERED"


class TaxonomyJudge:
    # Phase E classification. Tier 1 narrows leaves by verdict; Tier 2 asks the (provenance-
    # blind) judge model for a PRIMARY leaf plus optional SECONDARY leaves, with self-consistency
    # over m samples. Primary/secondary separation curbs the over-prediction that flattened
    # precision. The arm (human/AI) is never put in the prompt.
    def __init__(self, config):
        self.config = config
        self.client = LlmClient(config)
        self.exec = SubmissionJudge(config)
        self.m = config["judge"]["m"]
        self.temperature = config["judge"].get("temperature", 0.4)
        self.max_tokens = config["judge"].get("max_tokens", 2048)
        self.reasoning_effort = config["judge"].get("reasoning_effort")
        self.size_cap = config["prompt"]["size_cap_chars"]
        self.lang = config["languages"]["primary"]
        self.problems = Path(config["paths"]["data"]) / "problems"
        self.rubric = self._rubric()

    @staticmethod
    def tier1_candidates(verdict):
        return VERDICT_CANDIDATES.get(verdict, list(TAXONOMY))

    def classify(self, submission, model, dry_run=False, effort="inherit"):
        prompt = self._prompt(submission)
        if dry_run:
            return {"submission_id": submission["submission_id"], "model": model,
                    "prompt_chars": len(prompt), "dry_run": True}
        eff = self.reasoning_effort if effort == "inherit" else effort
        samples = []
        for i in range(self.m):
            r = self.client.complete(model, [{"role": "user", "content": prompt}],
                                     temperature=self.temperature, max_tokens=self.max_tokens,
                                     n=1, nonce=i, reasoning_effort=eff)
            samples.append(self._parse(r["texts"][0]))
        agg = self._aggregate(samples)
        return {"submission_id": submission["submission_id"], "problem_id": submission["problem_id"],
                "arm": submission.get("arm"), "verdict": submission["verdict"], "model": model,
                "primary": agg["primary"], "secondary": agg["secondary"], "leaves": agg["leaves"],
                "uncovered": agg["uncovered"], "needs_review": agg["needs_review"],
                "per_sample": [{"primary": s["primary"], "secondary": s["secondary"]} for s in samples],
                "rationale": next((s["rationale"] for s in samples if s["rationale"]), "")}

    def _prompt(self, submission):
        pid = submission["problem_id"]
        v = self.exec.judge(self.problems / pid, submission["source"], self.lang)
        ff = v["first_failing_test"] or {}
        oracle = json.loads([l for l in (self.problems / pid / self.lang / "correct.jsonl")
                            .read_text(encoding="utf-8").split("\n") if l][0])["code"]
        desc = self._clip((self.problems / pid / "description.txt").read_text(encoding="utf-8"))
        msg = v.get("compiler_stderr") or v.get("runtime_error") or "(none)"
        # opaque id: hash the submission_id so the arm-revealing prefix (ai:/human:) never
        # reaches the provenance-blind judge
        item_id = hashlib.sha1(submission["submission_id"].encode("utf-8")).hexdigest()[:10]
        return PROMPT.format(
            item_id=item_id, description=desc, verdict=submission["verdict"],
            submission=self._clip(submission["source"]),
            inp=self._clip(ff.get("input", "(n/a)"), 800), exp=self._clip(ff.get("expected", "(n/a)"), 800),
            act=self._clip(ff.get("actual", "(n/a)"), 800), msg=self._clip(msg, 1200),
            oracle=self._clip(oracle), candidates=", ".join(self.tier1_candidates(submission["verdict"])),
            rubric=self.rubric)

    def _parse(self, text):
        primary, secondary, rationale, uncovered = None, [], "", False
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if m:
            try:
                obj = json.loads(m.group(0))
                p = obj.get("primary")
                if isinstance(p, str) and p in TAXONOMY:
                    primary = p
                elif isinstance(p, str) and p.strip().upper() == UNCOVERED:
                    uncovered = True
                secondary = [c for c in (obj.get("secondary") or [])
                             if c in TAXONOMY and c != primary]
                rationale = str(obj.get("rationale", ""))[:500]
                uncovered = uncovered or bool(obj.get("uncovered", False))
            except (ValueError, TypeError):
                pass
        return {"primary": primary, "secondary": secondary, "uncovered": uncovered, "rationale": rationale}

    def _aggregate(self, samples):
        thresh = math.ceil(self.m / 2)
        primaries = [s["primary"] for s in samples if s["primary"]]
        primary = Counter(primaries).most_common(1)[0][0] if primaries else None
        sets = [({s["primary"]} if s["primary"] else set()) | set(s["secondary"]) for s in samples]
        counts = Counter(leaf for st in sets for leaf in st)
        full = {leaf for leaf, c in counts.items() if c >= thresh}
        if primary:
            full.add(primary)
        secondary = sorted(full - ({primary} if primary else set()))
        leaves = ([primary] if primary else []) + secondary
        uncovered = sum(1 for s in samples if s["uncovered"]) >= thresh
        return {"primary": primary, "secondary": secondary, "leaves": leaves,
                "uncovered": uncovered, "needs_review": not leaves and not uncovered}

    def _rubric(self):
        return "\n".join(f"{c} {v[0]}: {v[1]} e.g. {v[2]}" for c, v in TAXONOMY.items())

    def _clip(self, s, cap=None):
        cap = cap or self.size_cap
        s = s if s is not None else ""
        return s if len(s) <= cap else s[: cap // 2] + " …[clipped]… " + s[-cap // 2:]
