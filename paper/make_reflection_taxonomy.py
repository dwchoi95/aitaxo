#!/usr/bin/env python3
"""Build a taxonomy-aware self-reflection figure without external Python deps.

The script first validates whether the AI judge labels are reliable enough for a
family-level RQ3 figure. If the judge passes a bootstrap lower-bound criterion on
the 375-item human gold set, the figure uses the full clean-model trajectory. If
not, it falls back to the human-labeled clean-model gold subset.
"""

import csv
import hashlib
import html
import json
import random
import subprocess
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
CLS = DATA / "classifications"
FIGS = ROOT / "paper" / "figs"
OUT_STATS = ROOT / "paper" / "reflection_taxonomy_stats.json"

FAMILY_NAMES = {
    "GE1": "Design",
    "GE2": "Boundary",
    "GE3": "Condition",
    "GE4": "Data type",
    "GE5": "Syntax",
    "GE6": "I/O",
    "AE1": "Math",
    "AE2": "Greedy",
    "AE3": "Graph",
    "AE4": "Rec/D&C",
    "AE5": "DP",
    "AE6": "Search",
}
FAMILY_ORDER = ["GE1", "GE2", "GE5", "AE1", "AE2", "AE5"]
ALL_FAMILIES = ["GE1", "GE2", "GE3", "GE4", "GE5", "GE6", "AE1", "AE2", "AE3", "AE4", "AE5", "AE6"]
DIFF_ORDER = ["Easy", "Medium", "Hard", "All"]

KAPPA_THRESHOLD = 0.60
F1_THRESHOLD = 0.70
BOOTSTRAPS = 2000
SEED = 13


def read_csv(path):
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def label_list(raw):
    return [x.strip() for x in str(raw).split(",") if x.strip() and x.strip() != "UNCOVERED"]


def family_of_leaf(leaf):
    return leaf.split(".")[0] if leaf else "UNCOVERED"


def primary_family(raw):
    labels = label_list(raw)
    return family_of_leaf(labels[0]) if labels else "UNCOVERED"


def family_set(raw):
    families = {family_of_leaf(x) for x in label_list(raw)}
    return families or {"UNCOVERED"}


def cf_band(rating):
    rating = int(rating)
    if rating <= 1599:
        return "Easy"
    if rating <= 2399:
        return "Medium"
    return "Hard"


def cohen_kappa(a, b):
    cats = sorted(set(a) | set(b))
    n = len(a)
    ca = Counter(a)
    cb = Counter(b)
    po = sum(x == y for x, y in zip(a, b)) / n
    pe = sum(ca[c] * cb[c] for c in cats) / (n * n)
    return (po - pe) / (1 - pe) if pe < 1 else 1.0


def micro_f1(pred_sets, gold_sets):
    tp = fp = fn = 0
    for pred, gold in zip(pred_sets, gold_sets):
        tp += len(pred & gold)
        fp += len(pred - gold)
        fn += len(gold - pred)
    prec = tp / (tp + fp) if tp + fp else 0.0
    rec = tp / (tp + fn) if tp + fn else 0.0
    return 2 * prec * rec / (prec + rec) if prec + rec else 0.0


def binary_family_kappa(sample, left_by_id, right_by_id):
    left = []
    right = []
    for item_id in sample:
        left_families = family_set(left_by_id[item_id]["labels"])
        right_families = family_set(right_by_id[item_id]["labels"])
        for fam in ALL_FAMILIES:
            left.append(1 if fam in left_families else 0)
            right.append(1 if fam in right_families else 0)
    return cohen_kappa(left, right)


def percentile(xs, p):
    xs = sorted(xs)
    k = int(round((len(xs) - 1) * p))
    return xs[max(0, min(len(xs) - 1, k))]


def validate_labels(full_by_id, gold1_by_id, gold2_by_id):
    ids = [i for i in gold1_by_id if i in gold2_by_id and i in full_by_id]

    def calc(sample):
        judge_sets = [family_set(full_by_id[i]["labels"]) for i in sample]
        h1_sets = [family_set(gold1_by_id[i]["labels"]) for i in sample]
        h2_sets = [family_set(gold2_by_id[i]["labels"]) for i in sample]
        return {
            "human1_human2_family_kappa": binary_family_kappa(sample, gold1_by_id, gold2_by_id),
            "judge_human1_family_kappa": binary_family_kappa(sample, full_by_id, gold1_by_id),
            "judge_human2_family_kappa": binary_family_kappa(sample, full_by_id, gold2_by_id),
            "judge_human1_family_f1": micro_f1(judge_sets, h1_sets),
            "judge_human2_family_f1": micro_f1(judge_sets, h2_sets),
        }

    base = calc(ids)
    rng = random.Random(SEED)
    boot = {k: [] for k in base}
    for _ in range(BOOTSTRAPS):
        sample = [ids[rng.randrange(len(ids))] for _ in ids]
        stat = calc(sample)
        for k, v in stat.items():
            boot[k].append(v)

    ci = {k: [percentile(v, 0.025), percentile(v, 0.975)] for k, v in boot.items()}
    clean_ids = [
        i for i in ids
        if full_by_id[i]["model"] == "gpt-3.5-turbo-0125"
        and full_by_id[i]["stage"] == "zero_shot"
    ]
    clean = {
        "n": len(clean_ids),
        "judge_human1_family_kappa": binary_family_kappa(clean_ids, full_by_id, gold1_by_id),
        "judge_human2_family_kappa": binary_family_kappa(clean_ids, full_by_id, gold2_by_id),
    }

    passes = (
        ci["judge_human1_family_kappa"][0] > KAPPA_THRESHOLD
        and ci["judge_human2_family_kappa"][0] > KAPPA_THRESHOLD
        and ci["judge_human1_family_f1"][0] > F1_THRESHOLD
        and ci["judge_human2_family_f1"][0] > F1_THRESHOLD
        and clean["judge_human1_family_kappa"] > KAPPA_THRESHOLD
        and clean["judge_human2_family_kappa"] > KAPPA_THRESHOLD
    )
    return {"n": len(ids), "base": base, "ci95": ci, "clean_arm": clean, "passes": passes}


def reflect_fixed_map():
    out = {}
    for path in (DATA / "problems").glob("*/ai/gpt-3.5-turbo-0125/reflect.jsonl"):
        pid = path.parts[-4]
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line:
                continue
            rec = json.loads(line)
            out[(pid, str(rec["idx"]))] = bool(rec["fixed"])
    return out


def collect_full_judge_rows(full_rows):
    fixed = reflect_fixed_map()
    rows = []
    for row in full_rows:
        if row["model"] != "gpt-3.5-turbo-0125" or row["stage"] != "zero_shot":
            continue
        key = (row["problem_id"], row["idx"])
        rows.append({
            "family": primary_family(row["labels"]),
            "difficulty": cf_band(row["cf_rating"]),
            "fixed": fixed.get(key, False),
            "item_id": row["item_id"],
        })
    return rows


def collect_human_gold_rows(full_by_id, gold1_by_id, gold2_by_id):
    fixed = reflect_fixed_map()
    rows = []
    for item_id, row in full_by_id.items():
        if row["model"] != "gpt-3.5-turbo-0125" or row["stage"] != "zero_shot":
            continue
        if item_id not in gold1_by_id or item_id not in gold2_by_id:
            continue
        f1 = primary_family(gold1_by_id[item_id]["labels"])
        f2 = primary_family(gold2_by_id[item_id]["labels"])
        if f1 != f2:
            continue
        rows.append({
            "family": f1,
            "difficulty": cf_band(row["cf_rating"]),
            "fixed": fixed.get((row["problem_id"], row["idx"]), False),
            "item_id": item_id,
        })
    return rows


def summarize(rows):
    total = defaultdict(int)
    fixed = defaultdict(int)
    for row in rows:
        fam = row["family"]
        diff = row["difficulty"]
        total[(fam, diff)] += 1
        total[(fam, "All")] += 1
        fixed[(fam, diff)] += int(row["fixed"])
        fixed[(fam, "All")] += int(row["fixed"])
    return {"total": dict(total), "fixed": dict(fixed)}


def cell_color(rate):
    # Green ramp tuned for low repair rates; rates above 20% saturate.
    t = max(0.0, min(rate / 0.22, 1.0))
    r0, g0, b0 = (246, 248, 245)
    r1, g1, b1 = (63, 145, 98)
    r = round(r0 + (r1 - r0) * t)
    g = round(g0 + (g1 - g0) * t)
    b = round(b0 + (b1 - b0) * t)
    return f"#{r:02x}{g:02x}{b:02x}"


def svg_text(x, y, text, size=16, weight="400", anchor="middle", fill="#1f2933"):
    return (
        f'<text x="{x}" y="{y}" font-family="Helvetica,Arial,sans-serif" '
        f'font-size="{size}" font-weight="{weight}" text-anchor="{anchor}" '
        f'fill="{fill}">{html.escape(text)}</text>'
    )


def make_svg(rows, summary, validation, label_source):
    width, height = 1040, 370
    left, top = 170, 28
    cell_w, cell_h = 150, 36
    row_gap = 7
    all_x = left + 3 * cell_w + 28
    row_start = top + 58
    row_ys = [row_start + i * (cell_h + row_gap) for i in range(len(FAMILY_ORDER))]

    total = summary["total"]
    fixed = summary["fixed"]
    n = len(rows)
    repaired = sum(1 for r in rows if r["fixed"])
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        svg_text(left - 26, top + 15, "Original bug family", 13, "700", "end"),
        svg_text(left + 1.5 * cell_w, top + 15, "Repair rate by difficulty", 13, "700"),
        svg_text(all_x + cell_w / 2, top + 15, "All", 13, "700"),
    ]

    for j, diff in enumerate(DIFF_ORDER[:3]):
        x = left + j * cell_w
        parts.append(svg_text(x + cell_w / 2, top + 43, diff, 13, "700"))
    parts.append(svg_text(all_x + cell_w / 2, top + 43, f"{repaired}/{n} fixed", 12, "700"))

    for i, fam in enumerate(FAMILY_ORDER):
        y = row_ys[i]
        name = f"{fam} {FAMILY_NAMES[fam]}"
        parts.append(svg_text(left - 20, y + 28, name, 14, "700", "end"))
        for j, diff in enumerate(DIFF_ORDER):
            x = all_x if diff == "All" else left + j * cell_w
            t = total.get((fam, diff), 0)
            f = fixed.get((fam, diff), 0)
            rate = f / t if t else 0.0
            fill = cell_color(rate)
            stroke = "#253041" if diff == "All" else "#c7ced6"
            parts.append(
                f'<rect x="{x}" y="{y}" width="{cell_w - 6}" height="{cell_h}" '
                f'rx="4" fill="{fill}" stroke="{stroke}" stroke-width="1"/>'
            )
            pct = f"{rate * 100:.1f}%" if t else "-"
            count = f"{f}/{t}" if t else "0/0"
            text_fill = "#ffffff" if rate >= 0.15 else "#111827"
            parts.append(svg_text(x + (cell_w - 6) / 2, y + 15, pct, 13, "700", fill=text_fill))
            parts.append(svg_text(x + (cell_w - 6) / 2, y + 30, count, 10.5, "400", fill=text_fill))

    # Legend
    lx, ly = left, height - 32
    parts.append(svg_text(lx - 20, ly + 8, "Low", 11, "400", "end", "#4b5563"))
    for k in range(9):
        rate = k / 8 * 0.22
        parts.append(f'<rect x="{lx + k * 23}" y="{ly}" width="22" height="13" fill="{cell_color(rate)}"/>')
    parts.append(svg_text(lx + 9 * 23 + 8, ly + 10, "High repair rate", 11, "400", "start", "#4b5563"))
    parts.append("</svg>")
    return "\n".join(parts)


def main():
    full_rows = read_csv(CLS / "full.csv")
    gold1_rows = read_csv(CLS / "gold_human1.csv")
    gold2_rows = read_csv(CLS / "gold_human2.csv")
    full_by_id = {r["item_id"]: r for r in full_rows}
    gold1_by_id = {r["item_id"]: r for r in gold1_rows}
    gold2_by_id = {r["item_id"]: r for r in gold2_rows}

    validation = validate_labels(full_by_id, gold1_by_id, gold2_by_id)
    if validation["passes"]:
        label_source = "judge_full"
        rows = collect_full_judge_rows(full_rows)
    else:
        label_source = "human_gold_consensus"
        rows = collect_human_gold_rows(full_by_id, gold1_by_id, gold2_by_id)

    summary = summarize(rows)
    FIGS.mkdir(parents=True, exist_ok=True)
    svg_path = FIGS / "reflection_taxonomy_heatmap.svg"
    pdf_path = FIGS / "reflection_taxonomy_heatmap.pdf"
    raw_pdf_path = FIGS / "reflection_taxonomy_heatmap.raw.pdf"
    svg_path.write_text(make_svg(rows, summary, validation, label_source), encoding="utf-8")
    subprocess.run(["rsvg-convert", "-f", "pdf", "-o", str(raw_pdf_path), str(svg_path)], check=True)
    subprocess.run([
        "gs", "-q", "-dNOPAUSE", "-dBATCH", "-sDEVICE=pdfwrite",
        "-dCompatibilityLevel=1.5", f"-sOutputFile={pdf_path}", str(raw_pdf_path)
    ], check=True)
    raw_pdf_path.unlink(missing_ok=True)

    serial_summary = {
        "total": {f"{k[0]}:{k[1]}": v for k, v in summary["total"].items()},
        "fixed": {f"{k[0]}:{k[1]}": v for k, v in summary["fixed"].items()},
    }
    OUT_STATS.write_text(
        json.dumps({
            "label_source": label_source,
            "n_rows": len(rows),
            "n_fixed": sum(1 for r in rows if r["fixed"]),
            "criterion": {
                "family_kappa_ci95_low_must_exceed": KAPPA_THRESHOLD,
                "family_micro_f1_ci95_low_must_exceed": F1_THRESHOLD,
                "bootstraps": BOOTSTRAPS,
                "seed": SEED,
            },
            "validation": validation,
            "summary": serial_summary,
        }, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    print(f"label_source={label_source}")
    print(f"rows={len(rows)} fixed={sum(1 for r in rows if r['fixed'])}")
    print(f"wrote {pdf_path}")
    print(f"wrote {OUT_STATS}")


if __name__ == "__main__":
    main()
