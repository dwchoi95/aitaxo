#!/usr/bin/env python3
"""Summarize completed root-cause human audit labels.

The pack can contain:
- label_1.csv and label_2.csv: independent annotator labels
- adjudicated_disagreements.csv: disagreement resolution notes
- label.csv: final adjudicated labels
"""

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path


ARMS = ["human", "gpt-3.5-turbo-0125", "gpt-5.4-nano"]
FAMILIES = ["GE1", "GE2", "GE3", "GE4", "GE5", "GE6", "AE1", "AE2", "AE3", "AE4", "AE5", "AE6"]
MATH_DESIGN = {"AE1", "GE1"}


def labels(cell):
    return {x.strip() for x in (cell or "").split(",") if x.strip()}


def label_list(cell):
    return [x.strip() for x in (cell or "").split(",") if x.strip()]


def families(label_set):
    return {x.split(".")[0] for x in label_set if "." in x}


def pct(n, d):
    return 100.0 * n / d if d else 0.0


def primary(label_values):
    return label_values[0] if label_values else ""


def primary_family(label_values):
    first = primary(label_values)
    return first.split(".")[0] if first else ""


def cohen_kappa(xs, ys, cats=None):
    assert len(xs) == len(ys)
    n = len(xs)
    if n == 0:
        return {"kappa": 0.0, "po": 0.0, "pe": 0.0}
    po = sum(x == y for x, y in zip(xs, ys)) / n
    cx = Counter(xs)
    cy = Counter(ys)
    cats = set(cats or []) | set(cx) | set(cy)
    pe = sum((cx[c] / n) * (cy[c] / n) for c in cats)
    kappa = (po - pe) / (1 - pe) if (1 - pe) else 1.0
    return {"kappa": kappa, "po": po, "pe": pe}


def binary_multilabel_kappa(rows_a, rows_b, label_space, family=False):
    xs = []
    ys = []
    for item_id, row_a in rows_a.items():
        row_b = rows_b[item_id]
        la = families(labels(row_a["root_labels"])) if family else labels(row_a["root_labels"])
        lb = families(labels(row_b["root_labels"])) if family else labels(row_b["root_labels"])
        for label in label_space:
            xs.append(1 if label in la else 0)
            ys.append(1 if label in lb else 0)
    return cohen_kappa(xs, ys, {0, 1})


def load_by_id(path):
    rows = list(csv.DictReader(Path(path).open(encoding="utf-8")))
    return {row["item_id"]: row for row in rows}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--label-csv", default="analysis/root_cause_human_audit/label.csv")
    parser.add_argument("--label1-csv", default="analysis/root_cause_human_audit/label_1.csv")
    parser.add_argument("--label2-csv", default="analysis/root_cause_human_audit/label_2.csv")
    parser.add_argument("--adjudicated-csv", default="analysis/root_cause_human_audit/adjudicated_disagreements.csv")
    parser.add_argument("--out-prefix", default="analysis/root_cause_human_audit/summary")
    args = parser.parse_args()

    rows = list(csv.DictReader(Path(args.label_csv).open(encoding="utf-8")))
    completed = [r for r in rows if labels(r["root_labels"])]
    missing = [r["item_id"] for r in rows if not labels(r["root_labels"])]

    by_arm = defaultdict(lambda: Counter(n=0, leaf_changed=0, family_changed=0))
    coarse = Counter()
    primary_transitions = Counter()
    family_before = defaultdict(Counter)
    family_after = defaultdict(Counter)
    for row in completed:
        arm = row["model"]
        orig = labels(row["original_labels"])
        root = labels(row["root_labels"])
        primary_transitions[(primary_family(label_list(row["original_labels"])), primary_family(label_list(row["root_labels"])))] += 1
        orig_family = families(orig)
        root_family = families(root)
        orig_md = bool(orig_family & MATH_DESIGN)
        root_md = bool(root_family & MATH_DESIGN)
        by_arm[arm]["n"] += 1
        by_arm[arm]["leaf_changed"] += orig != root
        by_arm[arm]["family_changed"] += orig_family != root_family
        by_arm[arm]["math_design_before"] += orig_md
        by_arm[arm]["math_design_after"] += root_md
        by_arm[arm]["math_design_cross"] += orig_md != root_md
        by_arm[arm]["math_design_into"] += (not orig_md) and root_md
        by_arm[arm]["math_design_out"] += orig_md and (not root_md)
        coarse["math_design_before"] += orig_md
        coarse["math_design_after"] += root_md
        coarse["math_design_stable"] += orig_md == root_md
        coarse["math_design_cross"] += orig_md != root_md
        coarse["math_design_into"] += (not orig_md) and root_md
        coarse["math_design_out"] += orig_md and (not root_md)
        if orig_family != root_family:
            coarse["changed_math_design_stable"] += orig_md == root_md
            coarse["changed_math_design_cross"] += orig_md != root_md
            coarse["changed_math_design_into"] += (not orig_md) and root_md
            coarse["changed_math_design_out"] += orig_md and (not root_md)
        for fam in orig_family:
            family_before[arm][fam] += 1
        for fam in root_family:
            family_after[arm][fam] += 1

    summary = {
        "completed": len(completed),
        "missing": len(missing),
        "missing_item_ids": missing,
        "by_arm": {arm: dict(by_arm[arm]) for arm in ARMS},
        "coarse_math_design": dict(coarse),
        "primary_family_transitions": {f"{src}->{dst}": n for (src, dst), n in sorted(primary_transitions.items())},
        "family_before": {arm: dict(family_before[arm]) for arm in ARMS},
        "family_after": {arm: dict(family_after[arm]) for arm in ARMS},
    }

    label1_path = Path(args.label1_csv)
    label2_path = Path(args.label2_csv)
    adj_path = Path(args.adjudicated_csv)
    if label1_path.exists() and label2_path.exists():
        rows_a = load_by_id(label1_path)
        rows_b = load_by_id(label2_path)
        ids = sorted(set(rows_a) & set(rows_b))
        leaf_exact = sum(labels(rows_a[i]["root_labels"]) == labels(rows_b[i]["root_labels"]) for i in ids)
        family_exact = sum(
            families(labels(rows_a[i]["root_labels"])) == families(labels(rows_b[i]["root_labels"]))
            for i in ids
        )
        leaf_primary_a = [primary(label_list(rows_a[i]["root_labels"])) for i in ids]
        leaf_primary_b = [primary(label_list(rows_b[i]["root_labels"])) for i in ids]
        fam_primary_a = [primary(label_list(rows_a[i]["root_labels"])).split(".")[0] for i in ids]
        fam_primary_b = [primary(label_list(rows_b[i]["root_labels"])).split(".")[0] for i in ids]
        agreement = {
            "n": len(ids),
            "leaf_exact": leaf_exact,
            "leaf_exact_pct": pct(leaf_exact, len(ids)),
            "family_exact": family_exact,
            "family_exact_pct": pct(family_exact, len(ids)),
            "primary_leaf_kappa": cohen_kappa(leaf_primary_a, leaf_primary_b),
            "primary_family_kappa": cohen_kappa(fam_primary_a, fam_primary_b, FAMILIES),
            "binary_leaf_kappa": binary_multilabel_kappa(rows_a, rows_b, sorted({l for r in rows for l in labels(r["root_labels"])})),
            "binary_family_kappa": binary_multilabel_kappa(rows_a, rows_b, FAMILIES, family=True),
        }
        if adj_path.exists():
            adj_rows = list(csv.DictReader(adj_path.open(encoding="utf-8")))
            agreement["adjudicated_rows"] = len(adj_rows)
            agreement["adjudication_source"] = dict(Counter(r.get("source", "") for r in adj_rows))
        summary["agreement"] = agreement

    prefix = Path(args.out_prefix)
    prefix.parent.mkdir(parents=True, exist_ok=True)
    prefix.with_suffix(".json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    tex = [
        "% Auto-generated by analysis/summarize_root_cause_human.py",
        "\\begin{tabular}{lrr}",
        "\\toprule",
        "Metric & Count & Value \\\\",
        "\\midrule",
    ]
    if "agreement" in summary:
        a = summary["agreement"]
        tex.extend([
            f"Leaf exact agreement & {a['leaf_exact']}/{a['n']} & {a['leaf_exact_pct']:.1f}\\% \\\\",
            f"Family exact agreement & {a['family_exact']}/{a['n']} & {a['family_exact_pct']:.1f}\\% \\\\",
            f"Primary-leaf $\\kappa$ & -- & {a['primary_leaf_kappa']['kappa']:.2f} \\\\",
            f"Primary-family $\\kappa$ & -- & {a['primary_family_kappa']['kappa']:.2f} \\\\",
            f"Binary leaf $\\kappa$ & -- & {a['binary_leaf_kappa']['kappa']:.2f} \\\\",
            f"Binary family $\\kappa$ & -- & {a['binary_family_kappa']['kappa']:.2f} \\\\",
        ])
        if "adjudicated_rows" in a:
            tex.append(f"Adjudicated disagreements & {a['adjudicated_rows']}/{a['n']} & {pct(a['adjudicated_rows'], a['n']):.1f}\\% \\\\")
    tex.extend([
        "\\bottomrule",
        "\\end{tabular}",
        "",
        "\\vspace{0.5em}",
        "",
        "\\begin{tabular}{lrrr}",
        "\\toprule",
        "Arm & $n$ & Leaf changed & Family changed \\\\",
        "\\midrule",
    ])
    for arm in ARMS:
        s = by_arm[arm]
        n = s["n"]
        tex.append(
            f"{arm.replace('_', '\\_')} & {n} & "
            f"{s['leaf_changed']} ({pct(s['leaf_changed'], n):.1f}\\%) & "
            f"{s['family_changed']} ({pct(s['family_changed'], n):.1f}\\%) \\\\"
        )
    total_leaf = sum(by_arm[a]["leaf_changed"] for a in ARMS)
    total_family = sum(by_arm[a]["family_changed"] for a in ARMS)
    total_n = sum(by_arm[a]["n"] for a in ARMS)
    tex.extend([
        "\\midrule",
        f"All & {total_n} & {total_leaf} ({pct(total_leaf, total_n):.1f}\\%) & "
        f"{total_family} ({pct(total_family, total_n):.1f}\\%) \\\\",
        "\\bottomrule",
        "\\end{tabular}",
        "",
        "\\vspace{0.5em}",
        "",
        "\\begin{tabular}{lrr}",
        "\\toprule",
        "Math/design audit check & Count & Value \\\\",
        "\\midrule",
        f"Before stronger evidence & {coarse['math_design_before']}/{total_n} & {pct(coarse['math_design_before'], total_n):.1f}\\% \\\\",
        f"After stronger evidence & {coarse['math_design_after']}/{total_n} & {pct(coarse['math_design_after'], total_n):.1f}\\% \\\\",
        f"Bucket stable & {coarse['math_design_stable']}/{total_n} & {pct(coarse['math_design_stable'], total_n):.1f}\\% \\\\",
        f"Into math/design & {coarse['math_design_into']}/{total_n} & {pct(coarse['math_design_into'], total_n):.1f}\\% \\\\",
        f"Out of math/design & {coarse['math_design_out']}/{total_n} & {pct(coarse['math_design_out'], total_n):.1f}\\% \\\\",
        "\\bottomrule",
        "\\end{tabular}",
        "",
    ])
    prefix.with_suffix(".tex").write_text("\n".join(tex), encoding="utf-8")
    print(json.dumps({
        "completed": len(completed),
        "missing": len(missing),
        "summary_json": str(prefix.with_suffix(".json")),
        "summary_tex": str(prefix.with_suffix(".tex")),
    }, indent=2))


if __name__ == "__main__":
    main()
