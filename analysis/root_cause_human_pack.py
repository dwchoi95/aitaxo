#!/usr/bin/env python3
"""Create a local human-labeling pack for the root-cause audit."""

import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from analysis.root_cause_relabel import (  # noqa: E402
    ARMS,
    TAXONOMY,
    clip,
    first_fail_kind,
    load_config,
    load_full_labels,
    reference_for,
    source_for,
    stratified_sample,
)
from src.execute.validator import Validator  # noqa: E402
from src.taxonomy.taxonomy import FAMILIES, FAMILY_DEFINITIONS  # noqa: E402


PACK_COLS = [
    "item_id",
    "problem_id",
    "model",
    "idx",
    "cf_rating",
    "tags",
    "verdict",
    "first_fail_kind",
    "original_labels",
    "root_labels",
    "root_rationale",
]


def taxonomy_text():
    lines = []
    for code, (name, definition, _) in TAXONOMY.items():
        lines.append(f"- {code} {name}: {definition}")
    return "\n".join(lines)


def write_codebook(out_dir):
    family_lines = []
    for code, name in FAMILIES.items():
        family_lines.append(f"### {code}: {name}\n{FAMILY_DEFINITIONS[code]}\n")

    leaf_lines = []
    for code, (name, definition, language_dependent) in TAXONOMY.items():
        lang = "yes" if language_dependent else "no"
        leaf_lines.append(
            f"### {code}: {name}\n"
            f"- Family: {code.split('.')[0]} ({FAMILIES[code.split('.')[0]]})\n"
            f"- Language-dependent: {lang}\n"
            f"- Definition: {definition}\n"
        )

    (out_dir / "codebook.md").write_text(
        f"""# Root-Cause Audit Codebook

Use this codebook when filling `label.csv`.

The family names and leaf definitions below are the original Wei et al. taxonomy definitions used
by the paper; this audit only changes the evidence available to the annotator.

## What To Label
Assign `root_labels` from the fixed 32-leaf taxonomy below. Use one or more comma-separated leaf
codes, such as `AE1.1` or `AE1.1,GE2.1`.

The audit item gives stronger evidence than the original labeler: the rejected code, sandbox
verdict, first failing test, expected/actual output, and one accepted reference implementation.
Label the concrete bug mechanism in the rejected code that is supported by that evidence.

## Decision Rules
- Prefer the most specific leaf that explains the demonstrated failure.
- Use an algorithm-specific `AE*` label when the code clearly implements that paradigm.
- Use a general `GE*` label for parsing, formatting, compilation, boundary, condition, data-type,
  or broad design failures.
- Multi-label only when there are multiple independent root causes.
- Do not label downstream symptoms. For example, if a wrong formula causes a wrong branch later,
  label the wrong formula, not both.
- If the evidence remains ambiguous even with the failing test and reference implementation, choose
  the best-supported label and state the ambiguity briefly in `root_rationale`.

## Families
{chr(10).join(family_lines)}
## Leaf Labels
{chr(10).join(leaf_lines)}
""",
        encoding="utf-8",
    )

    with (out_dir / "taxonomy.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "code", "family", "family_name", "name", "definition", "language_dependent",
        ])
        writer.writeheader()
        for code, (name, definition, language_dependent) in TAXONOMY.items():
            family = code.split(".")[0]
            writer.writerow({
                "code": code,
                "family": family,
                "family_name": FAMILIES[family],
                "name": name,
                "definition": definition,
                "language_dependent": language_dependent,
            })


def write_item(path, row, problem_dir, source, reference, result, args):
    fail = result["first_failing_test"]
    text = f"""# Root-Cause Audit Item {row['item_id']}

## Metadata
- problem_id: {row['problem_id']}
- model: {row['model']}
- idx: {row['idx']}
- rating: {row['cf_rating']}
- tags: {row['tags']}
- sandbox_verdict: {result['verdict']}
- first_fail_kind: {first_fail_kind(problem_dir, result)}
- original_labels: {row['labels']}
- original_rationale: {row['rationale']}

## Problem Statement
{clip((problem_dir / 'description.txt').read_text(encoding='utf-8'), args.statement_cap)}

## Submitted Rejected C++ Code
```cpp
{clip(source, args.code_cap)}
```

## Accepted Reference C++ Implementation
```cpp
{clip(reference, args.reference_cap)}
```

## First Failing Test
Input:
```text
{clip(fail.get('input', ''), args.test_cap)}
```

Expected output:
```text
{clip(fail.get('expected', ''), args.test_cap)}
```

Actual output:
```text
{clip(fail.get('actual', ''), args.test_cap)}
```

## Labeling Task
Fill `root_labels` and `root_rationale` in `label.csv`.
Use one or more leaf labels from the taxonomy. Prefer the most specific label supported by the
submitted code plus the failing test/reference evidence.

## Taxonomy
{taxonomy_text()}
"""
    path.write_text(text, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--out-dir", default="analysis/root_cause_human_audit")
    parser.add_argument("--n-per-arm", type=int, default=40)
    parser.add_argument("--per-problem-cap", type=int, default=2)
    parser.add_argument("--seed", type=int, default=20260701)
    parser.add_argument("--statement-cap", type=int, default=5000)
    parser.add_argument("--code-cap", type=int, default=5000)
    parser.add_argument("--reference-cap", type=int, default=5000)
    parser.add_argument("--test-cap", type=int, default=3000)
    parser.add_argument("--fresh-cache-dir", default="artifacts/root_cause_exec")
    args = parser.parse_args()

    config = load_config(args.config)
    config["paths"]["artifacts"] = args.fresh_cache_dir
    data_root = Path(config["paths"]["problems"])
    rows = load_full_labels(data_root.parent / "classifications" / "full.csv")
    sample = stratified_sample(rows, args.n_per_arm, args.seed, args.per_problem_cap)
    validator = Validator(config)

    out_dir = Path(args.out_dir)
    items_dir = out_dir / "items"
    items_dir.mkdir(parents=True, exist_ok=True)
    write_codebook(out_dir)

    label_rows = []
    skipped = []
    for row in sample:
        problem_dir = data_root / row["problem_id"]
        source = source_for(data_root, row)
        result = validator.judge(problem_dir, source)
        if result["verdict"] != "WA" or not result.get("first_failing_test"):
            skipped.append(row["item_id"])
            continue
        reference = reference_for(data_root, row["problem_id"])
        write_item(items_dir / f"{row['item_id']}.md", row, problem_dir, source, reference, result, args)
        label_rows.append({
            "item_id": row["item_id"],
            "problem_id": row["problem_id"],
            "model": row["model"],
            "idx": row["idx"],
            "cf_rating": row["cf_rating"],
            "tags": row["tags"],
            "verdict": result["verdict"],
            "first_fail_kind": first_fail_kind(problem_dir, result),
            "original_labels": row["labels"],
            "root_labels": "",
            "root_rationale": "",
        })

    with (out_dir / "label.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=PACK_COLS)
        writer.writeheader()
        writer.writerows(label_rows)

    (out_dir / "README.md").write_text(
        f"""# Root-Cause Human Audit Pack

This local pack contains {len(label_rows)} wrong-answer submissions sampled from the three
zero-shot arms: {", ".join(ARMS)}. Each item includes the problem
statement, rejected code, one accepted reference implementation, and the first failing test.

Before labeling, read `codebook.md`. A spreadsheet-friendly copy of the same taxonomy is in
`taxonomy.csv`.

Fill `label.csv`:
- `root_labels`: comma-separated taxonomy leaf labels, e.g., `AE1.1,GE2.1`
- `root_rationale`: one or two sentences explaining the demonstrated root cause

Skipped items without a reproducible WA first-failing test: {json.dumps(skipped)}
""",
        encoding="utf-8",
    )

    print(json.dumps({
        "out_dir": str(out_dir),
        "items": len(label_rows),
        "skipped": len(skipped),
    }, indent=2))


if __name__ == "__main__":
    main()
