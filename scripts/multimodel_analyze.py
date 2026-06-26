"""Compare the bug profile across models (capability spectrum + recall regime).

gpt-3.5-turbo (10/problem, leakage-free, weak) vs gpt-4-0613 (5/problem, leakage-free,
strong) vs gpt-5.5 (5/problem, modern, RECALL regime = has seen these problems).
Reports pass rate, bug-category distribution, and per-problem systematicity for each.
"""
import json, collections, statistics
from pathlib import Path

SRC = {
    "gpt-3.5-turbo": ["results/fulltest_generations.jsonl", "results/gen2_generations.jsonl"],
    "gpt-4-0613":    ["results/gpt-4-0613_generations.jsonl"],
    "gpt-5.5":       ["results/gpt-5.5_generations.jsonl"],
}
ORDER = ["gpt-3.5-turbo", "gpt-4-0613", "gpt-5.5"]


def load(files):
    rows = []
    for f in files:
        p = Path(f)
        if p.exists():
            rows += [json.loads(l) for l in p.open()]
    return rows


def main():
    out = {}
    for model in ORDER:
        rows = load(SRC[model])
        if not rows:
            continue
        st = collections.Counter(r["status"] for r in rows)
        tot = len(rows); pas = st.get("pass", 0); bugs = tot - pas
        # per-problem systematicity over bug categories
        byp = collections.defaultdict(list)
        for r in rows:
            if r["status"] != "pass":
                byp[r["task_id"]].append(r["status"])
        ms = [max(collections.Counter(v).values()) / len(v) for v in byp.values() if len(v) >= 2]
        out[model] = {
            "gens": tot, "pass": pas, "pass_rate": round(100 * pas / tot, 1),
            "bugs": bugs,
            "dist": {k: round(100 * st.get(k, 0) / bugs, 1) for k in
                     ("wrong_answer", "timeout", "runtime_error", "compile_error")},
            "modal_share": round(statistics.mean(ms), 3) if ms else None,
            "fully_consistent_pct": round(100 * sum(m == 1.0 for m in ms) / len(ms), 1) if ms else None,
            "problems_ge2_bugs": len(ms),
        }
    Path("results/multimodel_summary.json").write_text(json.dumps(out, ensure_ascii=False, indent=2))
    # print table
    print(f"{'model':16} {'pass%':>6} {'bugs':>6} {'WA%':>6} {'TLE%':>6} {'RE%':>6} {'CE%':>6} {'modal':>6} {'consist%':>8}")
    for m in ORDER:
        if m not in out:
            continue
        o = out[m]; d = o["dist"]
        print(f"{m:16} {o['pass_rate']:>6} {o['bugs']:>6} {d['wrong_answer']:>6} {d['timeout']:>6} "
              f"{d['runtime_error']:>6} {d['compile_error']:>6} {str(o['modal_share']):>6} {str(o['fully_consistent_pct']):>8}")


if __name__ == "__main__":
    main()
