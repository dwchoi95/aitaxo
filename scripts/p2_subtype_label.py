"""P2: Label all WA (Spec-Misinterpretation) bugs into sub-types S1-S5, plus reliability.

Labeler uses a different model (gpt-4o-mini) from the studied one. Each WA bug is shown
the problem, the buggy AI code, and a correct human solution; the labeler picks S1-S5.
Labeler B re-labels a random sample to estimate Cohen's kappa.

Output: results/p2_subtypes.jsonl, results/p2_subtype_summary.json
"""
from __future__ import annotations
import json, re, random, collections
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from openai import OpenAI

DATA = Path("data"); RESULTS = Path("results")
LABELER = "gpt-4o-mini"
LABELS = ["S1", "S2", "S3", "S4", "S5"]
SYSTEM = (
    "You classify WHY an AI-generated competitive-programming solution gives a wrong answer. "
    "You see the problem statement, the buggy AI code, and a correct human solution. "
    "Choose the single best sub-type of specification misinterpretation:\n"
    "S1 output/case oversimplification: collapses required output branches/cases into one rule, "
    "or prints the wrong thing/format.\n"
    "S2 core-condition oversimplification: replaces the real requirement with an easier proxy "
    "condition (solves a simpler related problem).\n"
    "S3 wrong algorithm/formula: applies an incorrect mathematical model or formula.\n"
    "S4 failed paradigm recognition: does not recognize the required algorithm/paradigm and uses "
    "brute force or an ad-hoc heuristic.\n"
    "S5 edge/language-semantics: overall approach is right but it fails on edge cases due to "
    "language behavior (rounding, integer/precision, off-by-one at boundaries).\n"
    "Answer with ONLY the label: S1, S2, S3, S4, or S5."
)


def correct_of(task):
    hd = DATA / task / "human"
    if hd.is_dir():
        for sub in sorted(hd.iterdir()):
            c = sub / "correct.py"
            if c.exists():
                return c.read_text(errors="replace")
    return ""


def load_wa():
    seen = {}
    for fn in ("results/fulltest_generations.jsonl", "results/gen2_generations.jsonl"):
        for l in open(fn):
            g = json.loads(l)
            if g["status"] == "wrong_answer":
                seen[(g["task_id"], g["sample_idx"])] = g["code"]
    return [{"task_id": t, "idx": i, "code": c} for (t, i), c in seen.items()]


def make_prompt(b):
    prob = (DATA / b["task_id"] / "problem.txt")
    p = prob.read_text(errors="replace")[:900] if prob.exists() else ""
    return (f"# Problem\n{p}\n\n# Buggy AI solution\n{b['code'][:800]}\n\n"
            f"# A correct human solution\n{correct_of(b['task_id'])[:600]}\n\n"
            "Label (S1-S5):")


def label_one(client, b, temperature):
    try:
        r = client.chat.completions.create(
            model=LABELER, temperature=temperature, max_tokens=4,
            messages=[{"role": "system", "content": SYSTEM},
                      {"role": "user", "content": make_prompt(b)}])
        m = re.search(r"S[1-5]", r.choices[0].message.content or "")
        return m.group(0) if m else "S?"
    except Exception:
        return "S?"


def kappa(a, b):
    cats = sorted(set(a) | set(b))
    n = len(a)
    po = sum(x == y for x, y in zip(a, b)) / n
    pa = collections.Counter(a); pb = collections.Counter(b)
    pe = sum((pa[c]/n) * (pb[c]/n) for c in cats)
    return (po - pe) / (1 - pe) if pe < 1 else 1.0, po


def main():
    client = OpenAI()
    bugs = load_wa()
    print(f"WA bugs: {len(bugs)}")
    # Labeler A (all)
    with ThreadPoolExecutor(max_workers=12) as ex:
        labelsA = list(ex.map(lambda b: label_one(client, b, 0.0), bugs))
    with open(RESULTS / "p2_subtypes.jsonl", "w") as f:
        for b, la in zip(bugs, labelsA):
            f.write(json.dumps({**{k: b[k] for k in ("task_id", "idx")}, "subtype": la}, ensure_ascii=False) + "\n")
    distA = collections.Counter(labelsA)
    # Labeler B on a random sample for kappa
    random.seed(42)
    sample = random.sample(range(len(bugs)), min(300, len(bugs)))
    with ThreadPoolExecutor(max_workers=12) as ex:
        labelsB = list(ex.map(lambda i: label_one(client, bugs[i], 0.4), sample))
    aA = [labelsA[i] for i in sample]
    k, po = kappa(aA, labelsB)

    summ = {"n_wa": len(bugs), "labeler": LABELER,
            "distribution": {s: distA.get(s, 0) for s in LABELS + ["S?"]},
            "share": {s: round(distA.get(s, 0) / len(bugs), 3) for s in LABELS},
            "kappa_sample_n": len(sample), "cohens_kappa": round(k, 3), "raw_agreement": round(po, 3)}
    (RESULTS / "p2_subtype_summary.json").write_text(json.dumps(summ, ensure_ascii=False, indent=2))
    print(json.dumps(summ, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
