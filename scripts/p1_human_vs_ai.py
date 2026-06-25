"""P1: AI vs Human bug distribution comparison.

Judge each human faulty.py against the FULL hidden tests, classify into the same
coarse categories (WA/TLE/RE/CE) used for AI bugs, and compare the two distributions
with a chi-square test. Also summarize human fault-location locality (lines per bug).

Output: results/p1_human_bugs.jsonl, results/p1_comparison.json
"""
from __future__ import annotations
import json, sys, collections
from pathlib import Path
from scipy.stats import chi2_contingency

sys.path.insert(0, "src")
from execution.runner import run_python_code
from problems.schema import TestCase

TEST = Path("/Users/cdw/VSCode/aria/data/ConDefects/Test")
DATA = Path("data"); RESULTS = Path("results"); TIMEOUT = 3.0


def resolve(task):
    contest, letter = task.rsplit("_", 1)
    for L in (letter.upper(), "Ex"):
        if (TEST / contest / L / "in").is_dir() and (TEST / contest / L / "out").is_dir():
            return TEST / contest / L
    return None


def judge(code, tdir, names):
    ind, outd = tdir / "in", tdir / "out"
    passed = 0
    for nm in names:
        tc = TestCase(stdin=(ind / nm).read_text(errors="replace"),
                      expected_stdout=(outd / nm).read_text(errors="replace"), name=nm)
        r = run_python_code(code, tc, timeout_sec=TIMEOUT)
        if r.failure_type != "pass":
            return r.failure_type
        passed += 1
    return "pass"


def main():
    man = {t["task_id"]: t for t in json.loads((DATA / "window_manifest.json").read_text())["tasks"]}
    out = open(RESULTS / "p1_human_bugs.jsonl", "w")
    stat = collections.Counter()
    floc_lines = []
    npass = 0
    for k, (task, meta) in enumerate(man.items(), 1):
        tdir = resolve(task)
        if tdir is None:
            continue
        names = sorted(p.name for p in (tdir / "in").iterdir()
                       if p.suffix == ".txt" and (tdir / "out" / p.name).exists())
        hd = DATA / task / "human"
        if not hd.is_dir():
            continue
        for sub in sorted(hd.iterdir()):
            fp = sub / "faulty.py"
            if not fp.exists():
                continue
            status = judge(fp.read_text(errors="replace"), tdir, names)
            # fault-location locality
            fl = sub / "faultLocation.txt"
            nlines = None
            if fl.exists():
                toks = [t for t in fl.read_text().replace(",", " ").split() if t.strip().isdigit()]
                nlines = len(toks)
                if nlines:
                    floc_lines.append(nlines)
            if status == "pass":
                npass += 1
            else:
                stat[status] += 1
            out.write(json.dumps({"task_id": task, "sub": sub.name, "status": status,
                                  "difficulty": meta.get("difficulty"), "fault_lines": nlines},
                                 ensure_ascii=False) + "\n")
        if k % 50 == 0:
            print(f"[{k}/{len(man)}] human bugs so far: {sum(stat.values())}")
    out.close()

    # AI distribution (from full-test taxonomy)
    ai = {"wrong_answer": 2808, "timeout": 504, "runtime_error": 338, "compile_error": 41}
    hu = {c: stat.get(c, 0) for c in ai}
    cats = ["wrong_answer", "timeout", "runtime_error", "compile_error"]
    table = [[ai[c] for c in cats], [hu[c] for c in cats]]
    chi2, p, dof, _ = chi2_contingency(table)

    import statistics
    res = {
        "human_bugs": sum(hu.values()), "human_pass": npass,
        "human_dist": hu, "ai_dist": ai,
        "human_share": {c: round(hu[c] / sum(hu.values()), 3) for c in cats},
        "ai_share": {c: round(ai[c] / sum(ai.values()), 3) for c in cats},
        "chi2": round(chi2, 2), "p_value": p, "dof": dof,
        "human_fault_lines": {"median": statistics.median(floc_lines) if floc_lines else None,
                              "mean": round(sum(floc_lines) / len(floc_lines), 2) if floc_lines else None,
                              "pct_single_line": round(100 * sum(1 for x in floc_lines if x == 1) / len(floc_lines), 1) if floc_lines else None,
                              "n": len(floc_lines)},
    }
    (RESULTS / "p1_comparison.json").write_text(json.dumps(res, ensure_ascii=False, indent=2))
    print("\n=== P1: AI vs Human bug distribution ===")
    print(json.dumps(res, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
