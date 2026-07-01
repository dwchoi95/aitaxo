#!/usr/bin/env python3
"""Scope and heterogeneity checks for the paper.

The script deliberately uses only the Python standard library so the artifact can
be rerun without analysis-stack setup.
"""

from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FULL = ROOT / "data" / "classifications" / "full.csv"
DATA = ROOT / "data" / "problems"
AUDIT = ROOT / "analysis" / "root_cause_human_audit" / "label.csv"
OUT_JSON = ROOT / "analysis" / "scope_checks_summary.json"
OUT_TEX = ROOT / "analysis" / "scope_checks_summary.tex"

ARMS = ["human", "gpt-3.5-turbo-0125", "gpt-5.4-nano"]
ARM_LABEL = {
    "human": "Human",
    "gpt-3.5-turbo-0125": "Proxy",
    "gpt-5.4-nano": "Modern",
}
MD = {"AE1", "GE1"}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def family(raw: str) -> str:
    if not raw or not raw.strip():
        return "UNCOVERED"
    return raw.split(",")[0].strip().split(".")[0]


def families(raw: str) -> set[str]:
    return {x.strip().split(".")[0] for x in (raw or "").split(",") if "." in x.strip()}


def difficulty(rating: str) -> str:
    r = int(rating)
    if r <= 1199:
        return "Easy"
    if r <= 2399:
        return "Medium"
    return "Hard"


def correct_count(problem_id: str, arm: str) -> int:
    if arm == "human":
        path = DATA / problem_id / "human" / "correct.jsonl"
    else:
        path = DATA / problem_id / "ai" / arm / "correct.jsonl"
    if not path.exists():
        return 0
    with path.open(encoding="utf-8") as f:
        return sum(1 for line in f if line.strip())


def rate(rows: list[dict[str, str]], fams: set[str]) -> float:
    return 100 * sum(1 for r in rows if r["family"] in fams) / len(rows) if rows else 0.0


def row_for_slice(name: str, rows: list[dict[str, str]]) -> dict[str, object]:
    out: dict[str, object] = {"slice": name}
    for arm in ARMS:
        arm_rows = [r for r in rows if r["model"] == arm]
        out[f"{arm}_n"] = len(arm_rows)
        out[f"{arm}_md"] = rate(arm_rows, MD)
        out[f"{arm}_syntax"] = rate(arm_rows, {"GE5"})
    return out


def audit_changed(row: dict[str, str]) -> bool:
    return families(row["original_labels"]) != families(row["root_labels"])


def main() -> None:
    rows = read_csv(FULL)
    for row in rows:
        row["family"] = family(row["labels"])
    zs = [r for r in rows if r["stage"] == "zero_shot"]
    wa = [r for r in zs if r["verdict"] == "WA"]

    proxy_ac_problems = {
        pid.name for pid in DATA.iterdir() if pid.is_dir() and correct_count(pid.name, "gpt-3.5-turbo-0125") > 0
    }
    modern_ac_problems = {
        pid.name for pid in DATA.iterdir() if pid.is_dir() and correct_count(pid.name, "gpt-5.4-nano") > 0
    }

    slices = [
        row_for_slice("All non-AC", zs),
        row_for_slice("WA only", wa),
        row_for_slice(
            "Proxy AC-problems",
            [r for r in wa if r["problem_id"] in proxy_ac_problems and r["model"] in {"human", "gpt-3.5-turbo-0125"}],
        ),
        row_for_slice(
            "Modern AC-problems",
            [r for r in wa if r["problem_id"] in modern_ac_problems and r["model"] in {"human", "gpt-5.4-nano"}],
        ),
    ]

    audit = read_csv(AUDIT)
    for row in audit:
        row["orig_family"] = family(row["original_labels"])
        row["root_family"] = family(row["root_labels"])
        row["changed"] = audit_changed(row)
        row["difficulty"] = difficulty(row["cf_rating"])

    hetero = []
    group_specs = [
        ("Source", "model"),
        ("Difficulty", "difficulty"),
        ("First fail", "first_fail_kind"),
    ]
    for group_name, field in group_specs:
        by_val: dict[str, list[dict[str, str]]] = defaultdict(list)
        for row in audit:
            by_val[row[field]].append(row)
        for value, group_rows in sorted(by_val.items()):
            hetero.append(
                {
                    "group": group_name,
                    "value": ARM_LABEL.get(value, value.title() if value else value),
                    "n": len(group_rows),
                    "changed": sum(1 for r in group_rows if r["changed"]),
                    "rate": 100 * sum(1 for r in group_rows if r["changed"]) / len(group_rows),
                }
            )

    by_orig: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in audit:
        by_orig[row["orig_family"]].append(row)
    fam_changes = []
    for fam, group_rows in sorted(by_orig.items()):
        if len(group_rows) < 8:
            continue
        dest = Counter(r["root_family"] for r in group_rows if r["root_family"] != fam)
        fam_changes.append(
            {
                "family": fam,
                "n": len(group_rows),
                "changed": sum(1 for r in group_rows if r["changed"]),
                "rate": 100 * sum(1 for r in group_rows if r["changed"]) / len(group_rows),
                "top_dest": ", ".join(f"{k} {v}" for k, v in dest.most_common(2)) or "--",
            }
        )

    OUT_JSON.write_text(
        json.dumps({"slices": slices, "heterogeneity": hetero, "family_changes": fam_changes}, indent=2),
        encoding="utf-8",
    )

    def fmt(x: float) -> str:
        return f"{x:.1f}"

    lines = [
        "% Auto-generated by analysis/scope_checks.py",
        r"\begin{table}[t]",
        r"\centering",
        r"\caption{Scope checks for the coarse AE1+GE1 claim. Values are \% of bugs in mathematics or design; parenthesized counts are bugs in the slice. AC-problem slices keep only WA bugs from problems where that model has at least one accepted sample.}",
        r"\label{tab:scopechecks}",
        r"\scriptsize",
        r"\setlength{\tabcolsep}{3pt}",
        r"\begin{tabular}{lrrr}",
        r"\toprule",
        r"Slice & Human & Proxy & Modern \\",
        r"\midrule",
    ]
    for s in slices:
        vals = []
        for arm in ARMS:
            n = int(s[f"{arm}_n"])
            vals.append("--" if n == 0 else f"{fmt(float(s[f'{arm}_md']))} ({n})")
        lines.append(f"{s['slice']} & {vals[0]} & {vals[1]} & {vals[2]} \\\\")
    lines += [r"\bottomrule", r"\end{tabular}", r"\end{table}", ""]

    OUT_TEX.write_text("\n".join(lines), encoding="utf-8")

    print(json.dumps({"slices": slices, "heterogeneity": hetero, "family_changes": fam_changes}, indent=2))
    print(f"wrote {OUT_JSON}")
    print(f"wrote {OUT_TEX}")


if __name__ == "__main__":
    main()
