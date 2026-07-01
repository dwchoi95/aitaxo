#!/usr/bin/env python3
"""Summarize judge measurement error for the paper.

Inputs:
  data/classifications/full.csv
  data/classifications/gold_human1.csv
  data/classifications/gold_human2.csv

Outputs:
  analysis/measurement_error_summary.json
  analysis/measurement_error_summary.tex

The goal is not to estimate a definitive latent true distribution.  It gives the
paper a reproducible, conservative sensitivity check: per-family judge precision
and recall on the human agreement subset, plus an arm-specific additive bias
correction for full-corpus family rates.
"""

from __future__ import annotations

import json
import csv
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLS = ROOT / "data" / "classifications"
OUT_JSON = ROOT / "analysis" / "measurement_error_summary.json"
OUT_TEX = ROOT / "analysis" / "measurement_error_summary.tex"
BOOTSTRAPS = 2000
RNG_SEED = 20260701

FAMILY_ORDER = ["GE1", "GE2", "GE3", "GE4", "GE5", "GE6", "AE1", "AE2", "AE5"]
FAMILY_NAMES = {
    "GE1": "Design",
    "GE2": "Boundary",
    "GE3": "Implementation",
    "GE4": "Range",
    "GE5": "Syntax",
    "GE6": "I/O",
    "AE1": "Math",
    "AE2": "Greedy",
    "AE5": "DP",
}
ARMS = ["human", "gpt-3.5-turbo-0125", "gpt-5.4-nano"]
ARM_LABELS = {
    "human": "Human",
    "gpt-3.5-turbo-0125": "Proxy",
    "gpt-5.4-nano": "Modern",
}
FOCUS = ["GE1", "AE1", "GE2", "GE6"]


def primary_leaf(raw: str) -> str:
    if raw is None or not str(raw).strip():
        return "UNCOVERED"
    return str(raw).split(",")[0].strip()


def family_of(raw: str) -> str:
    leaf = primary_leaf(raw)
    return leaf.split(".")[0] if "." in leaf else leaf


def pct(x: float) -> str:
    return f"{x * 100:.1f}"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def mean(values: list[bool]) -> float:
    return sum(1 for v in values if v) / len(values) if values else 0.0


def percentile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    pos = (len(ordered) - 1) * q
    lo = int(pos)
    hi = min(lo + 1, len(ordered) - 1)
    frac = pos - lo
    return ordered[lo] * (1 - frac) + ordered[hi] * frac


def fmt_ci(values: list[float]) -> str:
    lo = percentile(values, 0.025) * 100
    hi = percentile(values, 0.975) * 100
    return f"[{lo:+.1f},{hi:+.1f}]"


def main() -> None:
    full = read_csv(CLS / "full.csv")
    g1 = read_csv(CLS / "gold_human1.csv")
    g2 = read_csv(CLS / "gold_human2.csv")
    for rows in (full, g1, g2):
        for row in rows:
            row["family"] = family_of(row.get("labels", ""))

    zs = [row for row in full if row.get("stage") == "zero_shot"]
    full_by_id = {row["item_id"]: row for row in zs}
    g1_by_id = {row["item_id"]: row for row in g1}
    g2_by_id = {row["item_id"]: row for row in g2}

    common = [i for i in g1_by_id if i in g2_by_id and i in full_by_id]
    agree = [i for i in common if g1_by_id[i]["family"] == g2_by_id[i]["family"]]

    # Confusion on human-agreement subset: rows=gold consensus, cols=judge.
    confusion = {gf: {jf: 0 for jf in FAMILY_ORDER} for gf in FAMILY_ORDER}
    for item_id in agree:
        gold_f = g1_by_id[item_id]["family"]
        judge_f = full_by_id[item_id]["family"]
        if gold_f in confusion and judge_f in confusion[gold_f]:
            confusion[gold_f][judge_f] += 1

    metrics = []
    for fam in FAMILY_ORDER:
        tp = confusion[fam][fam]
        pred = sum(confusion[gf][fam] for gf in FAMILY_ORDER)
        gold = sum(confusion[fam][jf] for jf in FAMILY_ORDER)
        precision = tp / pred if pred else None
        recall = tp / gold if gold else None
        metrics.append(
            {
                "family": fam,
                "name": FAMILY_NAMES[fam],
                "gold_n": gold,
                "judge_n": pred,
                "tp": tp,
                "precision": precision,
                "recall": recall,
            }
        )

    # Additive arm-specific bias: observed judge rate on gold minus mean human rate
    # for that arm.  Then subtract the bias from the full-corpus judge rate.
    correction = []
    for arm in ARMS:
        arm_ids = [i for i in common if full_by_id[i]["model"] == arm]
        full_arm = [row for row in zs if row["model"] == arm]
        n_full = len(full_arm)
        for fam in FAMILY_ORDER:
            judge_gold = mean([full_by_id[i]["family"] == fam for i in arm_ids])
            human_gold = (
                sum(1 for i in arm_ids if g1_by_id[i]["family"] == fam)
                + sum(1 for i in arm_ids if g2_by_id[i]["family"] == fam)
            ) / (2 * len(arm_ids))
            bias = judge_gold - human_gold
            raw = mean([row["family"] == fam for row in full_arm])
            corrected = max(0.0, min(1.0, raw - bias))
            correction.append(
                {
                    "arm": arm,
                    "family": fam,
                    "raw": raw,
                    "bias": bias,
                    "corrected": corrected,
                    "gold_n": len(arm_ids),
                    "full_n": n_full,
                }
            )

    deltas = []
    for fam in FOCUS:
        human = next(r for r in correction if r["arm"] == "human" and r["family"] == fam)
        for arm in ARMS[1:]:
            other = next(r for r in correction if r["arm"] == arm and r["family"] == fam)
            deltas.append(
                {
                    "family": fam,
                    "comparison": f"{ARM_LABELS[arm]}-Human",
                    "raw_delta": other["raw"] - human["raw"],
                    "corrected_delta": other["corrected"] - human["corrected"],
                    "other_bias": other["bias"],
                    "human_bias": human["bias"],
                }
            )

    math_design = []
    for arm in ARMS:
        arm_rows = [r for r in correction if r["arm"] == arm]
        raw = sum(r["raw"] for r in arm_rows if r["family"] in {"AE1", "GE1"})
        corrected = sum(r["corrected"] for r in arm_rows if r["family"] in {"AE1", "GE1"})
        math_design.append({"arm": arm, "raw": raw, "corrected": corrected})

    # Bootstrap only the gold-based bias estimate; the full-corpus judge rates are
    # fixed outputs in this artifact. Resample within arm so the arm-balanced gold
    # design is preserved.
    rng = random.Random(RNG_SEED)
    common_by_arm = {arm: [i for i in common if full_by_id[i]["model"] == arm] for arm in ARMS}
    raw_by_arm_family = {
        arm: {
            fam: mean([row["family"] == fam for row in zs if row["model"] == arm])
            for fam in FAMILY_ORDER
        }
        for arm in ARMS
    }
    boot_corr_delta: dict[tuple[str, str], list[float]] = {}
    for fam in FOCUS + ["AE1+GE1"]:
        for arm in ARMS[1:]:
            boot_corr_delta[(fam, f"{ARM_LABELS[arm]}-Human")] = []

    for _ in range(BOOTSTRAPS):
        corrected_by_arm: dict[str, dict[str, float]] = {arm: {} for arm in ARMS}
        for arm in ARMS:
            ids = common_by_arm[arm]
            sample = [rng.choice(ids) for _ in ids]
            for fam in FAMILY_ORDER:
                judge_gold = mean([full_by_id[i]["family"] == fam for i in sample])
                human_gold = (
                    sum(1 for i in sample if g1_by_id[i]["family"] == fam)
                    + sum(1 for i in sample if g2_by_id[i]["family"] == fam)
                ) / (2 * len(sample))
                bias = judge_gold - human_gold
                corrected_by_arm[arm][fam] = max(0.0, min(1.0, raw_by_arm_family[arm][fam] - bias))
        for arm in ARMS[1:]:
            comp = f"{ARM_LABELS[arm]}-Human"
            for fam in FOCUS:
                boot_corr_delta[(fam, comp)].append(
                    corrected_by_arm[arm][fam] - corrected_by_arm["human"][fam]
                )
            boot_corr_delta[("AE1+GE1", comp)].append(
                corrected_by_arm[arm]["AE1"]
                + corrected_by_arm[arm]["GE1"]
                - corrected_by_arm["human"]["AE1"]
                - corrected_by_arm["human"]["GE1"]
            )

    for d in deltas:
        d["corrected_delta_boot_ci"] = {
            "lo": percentile(boot_corr_delta[(d["family"], d["comparison"])], 0.025),
            "hi": percentile(boot_corr_delta[(d["family"], d["comparison"])], 0.975),
        }

    result = {
        "n_common": len(common),
        "n_agree": len(agree),
        "confusion": confusion,
        "metrics": metrics,
        "correction": correction,
        "deltas": deltas,
        "math_design": math_design,
        "bootstrap": {
            "replicates": BOOTSTRAPS,
            "seed": RNG_SEED,
            "corrected_delta_ci": {
                f"{fam}:{comp}": {
                    "lo": percentile(values, 0.025),
                    "hi": percentile(values, 0.975),
                }
                for (fam, comp), values in boot_corr_delta.items()
            },
        },
    }
    OUT_JSON.write_text(json.dumps(result, indent=2), encoding="utf-8")

    metric_by_fam = {m["family"]: m for m in metrics}
    delta_rows = {(d["family"], d["comparison"]): d for d in deltas}
    md_by_arm = {r["arm"]: r for r in math_design}

    lines = [
        "% Auto-generated by analysis/measurement_error_sensitivity.py",
        r"\begin{table}[t]",
        r"\centering",
        rf"\caption{{Judge measurement-error sensitivity. P/R use the {len(agree)} gold items with annotator-agreed primary families. Deltas are percentage points: raw$\to$bias-corrected, with 95\% bootstrap CIs for corrected deltas from the 375-item gold.}}",
        r"\label{tab:measerr}",
        r"\scriptsize",
        r"\setlength{\tabcolsep}{2pt}",
        r"\resizebox{\columnwidth}{!}{%",
        r"\begin{tabular}{lccc}",
        r"\toprule",
        r"Family & P/R & Proxy--H & Modern--H \\",
        r"\midrule",
    ]
    for fam in FOCUS:
        m = metric_by_fam[fam]
        dp = delta_rows[(fam, "Proxy-Human")]
        dm = delta_rows[(fam, "Modern-Human")]
        pr = (
            f"{pct(m['precision'])}/{pct(m['recall'])}"
            if m["precision"] is not None and m["recall"] is not None
            else "--"
        )
        lines.append(
            f"{fam} {FAMILY_NAMES[fam]} & "
            f"{pr} & "
            f"{dp['raw_delta'] * 100:+.1f}$\\to${dp['corrected_delta'] * 100:+.1f} {fmt_ci(boot_corr_delta[(fam, 'Proxy-Human')])} & "
            f"{dm['raw_delta'] * 100:+.1f}$\\to${dm['corrected_delta'] * 100:+.1f} {fmt_ci(boot_corr_delta[(fam, 'Modern-Human')])} \\\\"
        )
    md_raw_delta = md_by_arm["gpt-3.5-turbo-0125"]["raw"] - md_by_arm["human"]["raw"]
    md_corr_delta = (
        md_by_arm["gpt-3.5-turbo-0125"]["corrected"] - md_by_arm["human"]["corrected"]
    )
    md_mod_raw_delta = md_by_arm["gpt-5.4-nano"]["raw"] - md_by_arm["human"]["raw"]
    md_mod_corr_delta = (
        md_by_arm["gpt-5.4-nano"]["corrected"] - md_by_arm["human"]["corrected"]
    )
    lines += [
        r"\midrule",
        f"AE1+GE1 & -- & {md_raw_delta * 100:+.1f}$\\to${md_corr_delta * 100:+.1f} {fmt_ci(boot_corr_delta[('AE1+GE1', 'Proxy-Human')])} & "
        f"{md_mod_raw_delta * 100:+.1f}$\\to${md_mod_corr_delta * 100:+.1f} {fmt_ci(boot_corr_delta[('AE1+GE1', 'Modern-Human')])} \\\\",
        r"\bottomrule",
        r"\end{tabular}",
        r"}",
        r"\end{table}",
        "",
    ]
    OUT_TEX.write_text("\n".join(lines), encoding="utf-8")

    print(f"common={len(common)} agree={len(agree)}")
    for row in metrics:
        print(row)
    for row in deltas:
        print(row)
    for row in math_design:
        print(row)
    print(f"wrote {OUT_JSON}")
    print(f"wrote {OUT_TEX}")


if __name__ == "__main__":
    main()
