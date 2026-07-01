#!/usr/bin/env python3
"""Evidence-augmented taxonomy audit.

This script samples wrong-answer submissions from the three zero-shot arms and
relabels them with stronger evidence than the original taxonomy judge received:
the first failing test and one accepted reference implementation.  It is meant
to quantify whether statement+code+verdict labels are stable when a root-cause
oracle is partially approximated.
"""

import argparse
import asyncio
import csv
import hashlib
import json
import random
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.execute.validator import Validator
from src.models.gpt import Gpt
from src.taxonomy.taxonomy import TAXONOMY


ARMS = ["human", "gpt-3.5-turbo-0125", "gpt-5.4-nano"]
OUT_COLS = [
    "item_id",
    "problem_id",
    "cf_rating",
    "tags",
    "model",
    "idx",
    "verdict",
    "first_fail_kind",
    "original_labels",
    "root_labels",
    "leaf_changed",
    "family_changed",
    "original_rationale",
    "root_rationale",
]


SYSTEM_TEMPLATE = """You are an independent senior competitive-programming root-cause auditor.

Label the demonstrated bug(s) in ONE rejected C++ submission using the fixed taxonomy below.
Unlike the original taxonomy judge, you are given privileged execution evidence: the first failing
test observed by the sandbox and one accepted C++ reference implementation. Use this evidence to
identify the root cause that explains the observed failure. Do not label stylistic differences or
harmless deviations from the reference implementation.

Return STRICT JSON only, with no markdown:
{{"labels":["AE1.1"],"rationale":"..."}}

Rules:
- labels is a MULTI-LABEL list of one or more leaf codes. Include every independent root cause that
  is clearly supported by the code plus the failing test/reference evidence.
- Use ["UNCOVERED"] if no taxonomy leaf is clearly supported.
- Prefer the most specific leaf. If an AE* leaf precisely describes the bug, prefer it over GE1.1.
- Do not infer from verdict alone. The failing test and reference implementation are evidence, but
  the submitted code must still contain the labeled mechanism.
- Do not add downstream consequences or broad parent-like labels.

Taxonomy:
{rubric}
"""


USER_TEMPLATE = """Problem statement:
{description}

Submitted rejected C++ code:
```cpp
{submission}
```

Accepted reference C++ implementation:
```cpp
{reference}
```

Sandbox verdict: {verdict}
First failing test kind: {test_kind}
First failing test input:
```
{fail_input}
```
Expected output:
```
{fail_expected}
```
Actual output:
```
{fail_actual}
```

Rationale requirement: one or two concise sentences naming the concrete mistake in the submitted
code and why the failing test/reference evidence supports that label.
"""


def clip(text, cap):
    text = text or ""
    if len(text) <= cap:
        return text
    half = cap // 2
    return text[:half] + "\n...[clipped]...\n" + text[-half:]


def load_config(path):
    with Path(path).open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def read_jsonl(path):
    if not Path(path).exists():
        return []
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line]


def item_id_for(model, pid, idx):
    key = f"{model}:{pid}:{idx}"
    return hashlib.sha1(key.encode("utf-8")).hexdigest()[:10]


def source_for(data_root, row):
    pid = row["problem_id"]
    idx = int(row["idx"])
    if row["model"] == "human":
        path = data_root / pid / "human" / "incorrect.jsonl"
    else:
        path = data_root / pid / "ai" / row["model"] / "incorrect.jsonl"
    return read_jsonl(path)[idx]["source"]


def reference_for(data_root, pid):
    correct = read_jsonl(data_root / pid / "human" / "correct.jsonl")
    if not correct:
        return ""
    return correct[0]["source"]


def family_set(labels):
    out = set()
    for label in labels:
        if label in TAXONOMY:
            out.add(label.split(".")[0])
    return out


def parse_labels(text):
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return [], ""
    try:
        obj = json.loads(match.group(0))
    except json.JSONDecodeError:
        return [], ""
    labels = []
    for label in obj.get("labels", []):
        if label in TAXONOMY and label not in labels:
            labels.append(label)
    return labels, obj.get("rationale", "")


def rubric():
    return "\n".join(f"{code} {body[0]}: {body[1]}" for code, body in TAXONOMY.items())


def rating_bin(rating):
    try:
        r = int(rating)
    except (TypeError, ValueError):
        return "unknown"
    if r < 1200:
        return "<1200"
    if r < 1600:
        return "1200-1599"
    if r < 2000:
        return "1600-1999"
    if r < 2400:
        return "2000-2399"
    return "2400+"


def load_full_labels(path):
    rows = []
    with Path(path).open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            if row["stage"] != "zero_shot":
                continue
            if row["model"] not in ARMS:
                continue
            if row["verdict"] != "WA":
                continue
            labels = [x for x in row["labels"].split(",") if x in TAXONOMY]
            if not labels:
                continue
            row["label_list"] = labels
            row["family_key"] = ",".join(sorted(family_set(labels)))
            row["rating_bin"] = rating_bin(row["cf_rating"])
            rows.append(row)
    return rows


def stratified_sample(rows, n_per_arm, seed, per_problem_cap):
    rng = random.Random(seed)
    selected = []
    for arm in ARMS:
        arm_rows = [r for r in rows if r["model"] == arm]
        groups = defaultdict(list)
        for row in arm_rows:
            groups[(row["family_key"], row["rating_bin"])].append(row)
        for group in groups.values():
            rng.shuffle(group)
        keys = sorted(groups, key=lambda k: (len(groups[k]), k))
        problem_counts = Counter()
        arm_selected = []
        changed = True
        while len(arm_selected) < n_per_arm and changed:
            changed = False
            for key in keys:
                while groups[key]:
                    cand = groups[key].pop()
                    if problem_counts[cand["problem_id"]] >= per_problem_cap:
                        continue
                    arm_selected.append(cand)
                    problem_counts[cand["problem_id"]] += 1
                    changed = True
                    break
                if len(arm_selected) >= n_per_arm:
                    break
        if len(arm_selected) < n_per_arm:
            rest = [r for r in arm_rows if r not in arm_selected]
            rng.shuffle(rest)
            for cand in rest:
                if len(arm_selected) >= n_per_arm:
                    break
                if problem_counts[cand["problem_id"]] >= per_problem_cap:
                    continue
                arm_selected.append(cand)
                problem_counts[cand["problem_id"]] += 1
        selected.extend(arm_selected)
    return selected


def done_ids(path):
    path = Path(path)
    if not path.exists():
        return set()
    with path.open(encoding="utf-8", newline="") as f:
        return {row["item_id"] for row in csv.DictReader(f)}


def ensure_out(path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        with path.open("w", encoding="utf-8", newline="") as f:
            csv.DictWriter(f, fieldnames=OUT_COLS).writeheader()


def first_fail_kind(problem_dir, result):
    if not result.get("per_test"):
        return ""
    idx = result["per_test"][-1]["idx"]
    tests = read_jsonl(problem_dir / "tests.jsonl")
    if 0 <= idx < len(tests):
        return tests[idx].get("kind", "")
    return ""


async def classify_one(gpt, model, system, user, sem, item_id, temperature):
    async with sem:
        return await gpt.complete(model, system, user, temperature, f"root-cause:{item_id}")


async def run(args):
    config = load_config(args.config)
    data_root = Path(config["paths"]["problems"])
    validator = Validator(config)
    gpt = Gpt(config)
    model = args.model or config["judge"]["model"]
    system = SYSTEM_TEMPLATE.format(rubric=rubric())

    rows = load_full_labels(data_root.parent / "classifications" / "full.csv")
    sample = stratified_sample(rows, args.n_per_arm, args.seed, args.per_problem_cap)
    ensure_out(args.output)
    seen = done_ids(args.output)
    todo = [row for row in sample if row["item_id"] not in seen]
    if args.limit:
        todo = todo[: args.limit]

    manifest = Path(args.output).with_suffix(".sample.jsonl")
    with manifest.open("w", encoding="utf-8") as f:
        for row in sample:
            f.write(json.dumps({k: row[k] for k in [
                "item_id", "problem_id", "cf_rating", "tags", "model", "idx",
                "verdict", "labels", "rationale", "family_key", "rating_bin",
            ]}, ensure_ascii=False) + "\n")

    print(json.dumps({
        "sampled": len(sample),
        "todo": len(todo),
        "already_done": len(sample) - len(todo),
        "model": model,
        "output": args.output,
        "manifest": str(manifest),
    }, indent=2))
    if args.dry_run:
        return

    sem = asyncio.Semaphore(args.concurrency)
    tasks = []
    prepared = []
    for row in todo:
        problem_dir = data_root / row["problem_id"]
        source = source_for(data_root, row)
        result = validator.judge(problem_dir, source)
        if result["verdict"] != "WA" or not result.get("first_failing_test"):
            continue
        fail = result["first_failing_test"]
        user = USER_TEMPLATE.format(
            description=clip((problem_dir / "description.txt").read_text(encoding="utf-8"), args.statement_cap),
            submission=clip(source, args.code_cap),
            reference=clip(reference_for(data_root, row["problem_id"]), args.reference_cap),
            verdict=result["verdict"],
            test_kind=first_fail_kind(problem_dir, result),
            fail_input=clip(fail.get("input", ""), args.test_cap),
            fail_expected=clip(fail.get("expected", ""), args.test_cap),
            fail_actual=clip(fail.get("actual", ""), args.test_cap),
        )
        tasks.append(classify_one(gpt, model, system, user, sem, row["item_id"], args.temperature))
        prepared.append((row, result))

    for (row, result), response in zip(prepared, await asyncio.gather(*tasks)):
        root_labels, root_rationale = parse_labels(response)
        original = set(row["label_list"])
        root = set(root_labels)
        out = {
            "item_id": row["item_id"],
            "problem_id": row["problem_id"],
            "cf_rating": row["cf_rating"],
            "tags": row["tags"],
            "model": row["model"],
            "idx": row["idx"],
            "verdict": result["verdict"],
            "first_fail_kind": first_fail_kind(data_root / row["problem_id"], result),
            "original_labels": ",".join(row["label_list"]),
            "root_labels": ",".join(root_labels) if root_labels else "UNCOVERED",
            "leaf_changed": str(original != root),
            "family_changed": str(family_set(original) != family_set(root)),
            "original_rationale": row["rationale"],
            "root_rationale": root_rationale,
        }
        with Path(args.output).open("a", encoding="utf-8", newline="") as f:
            csv.DictWriter(f, fieldnames=OUT_COLS).writerow(out)

    summarize(args.output)


def summarize(path):
    path = Path(path)
    rows = []
    with path.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        return

    def pct(n, d):
        return 100.0 * n / d if d else 0.0

    by_arm = {}
    for arm in ARMS:
        arm_rows = [r for r in rows if r["model"] == arm]
        by_arm[arm] = {
            "n": len(arm_rows),
            "leaf_changed": sum(r["leaf_changed"] == "True" for r in arm_rows),
            "family_changed": sum(r["family_changed"] == "True" for r in arm_rows),
        }
    overall = {
        "n": len(rows),
        "leaf_changed": sum(r["leaf_changed"] == "True" for r in rows),
        "family_changed": sum(r["family_changed"] == "True" for r in rows),
        "by_arm": by_arm,
    }
    summary_json = path.with_suffix(".summary.json")
    summary_json.write_text(json.dumps(overall, indent=2), encoding="utf-8")

    tex = [
        "% Auto-generated by analysis/root_cause_relabel.py",
        "\\begin{tabular}{lrrr}",
        "\\toprule",
        "Arm & $n$ & Leaf changed & Family changed \\\\",
        "\\midrule",
    ]
    for arm in ARMS:
        s = by_arm[arm]
        tex.append(
            f"{arm.replace('_', '\\_')} & {s['n']} & "
            f"{s['leaf_changed']} ({pct(s['leaf_changed'], s['n']):.1f}\\%) & "
            f"{s['family_changed']} ({pct(s['family_changed'], s['n']):.1f}\\%) \\\\"
        )
    tex.extend([
        "\\midrule",
        f"All & {overall['n']} & {overall['leaf_changed']} ({pct(overall['leaf_changed'], overall['n']):.1f}\\%) & "
        f"{overall['family_changed']} ({pct(overall['family_changed'], overall['n']):.1f}\\%) \\\\",
        "\\bottomrule",
        "\\end{tabular}",
        "",
    ])
    path.with_suffix(".summary.tex").write_text("\n".join(tex), encoding="utf-8")
    print(json.dumps(overall, indent=2))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--output", default="analysis/root_cause_audit.csv")
    parser.add_argument("--model", default=None)
    parser.add_argument("--n-per-arm", type=int, default=40)
    parser.add_argument("--per-problem-cap", type=int, default=2)
    parser.add_argument("--seed", type=int, default=20260701)
    parser.add_argument("--concurrency", type=int, default=8)
    parser.add_argument("--temperature", type=float, default=0.2)
    parser.add_argument("--statement-cap", type=int, default=5000)
    parser.add_argument("--code-cap", type=int, default=5000)
    parser.add_argument("--reference-cap", type=int, default=5000)
    parser.add_argument("--test-cap", type=int, default=3000)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
