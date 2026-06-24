"""Fix the ConDefects `_h` <-> AtCoder "Ex" letter mapping.

(1) Re-materialize testcases for the 22 `_h` tasks from Test/<contest>/Ex/ (replace samples).
(2) Re-judge those tasks' generations with full hidden tests; append to fulltest_*.jsonl.
(3) Recompute results/fulltest_summary.json from the merged corpus.
"""
from __future__ import annotations
import json, shutil, sys, collections
from pathlib import Path

sys.path.insert(0, "src")
from execution.runner import run_python_code
from problems.schema import TestCase

TEST = Path("/Users/cdw/VSCode/aria/data/ConDefects/Test")
DATA = Path("data"); RESULTS = Path("results"); TIMEOUT = 3.0


def resolve(task):
    """Map ConDefects task -> (contest, letter) trying H then Ex (AtCoder renamed last ABC problem)."""
    contest, letter = task.rsplit("_", 1)
    for L in (letter.upper(), "Ex"):
        if (TEST / contest / L / "in").is_dir() and (TEST / contest / L / "out").is_dir():
            return contest, L
    return None


def materialize(task, loc):
    contest, L = loc
    ind, outd = TEST / contest / L / "in", TEST / contest / L / "out"
    tcdir = DATA / task / "testcases"
    if tcdir.exists():
        shutil.rmtree(tcdir)
    tcdir.mkdir(parents=True)
    n = 0
    for f in sorted(ind.iterdir()):
        if f.suffix != ".txt" or not (outd / f.name).exists():
            continue
        d = tcdir / f.stem; d.mkdir()
        shutil.copy(f, d / "in.txt"); shutil.copy(outd / f.name, d / "out.txt")
        n += 1
    return n


def judge(code, loc, names):
    contest, L = loc
    ind, outd = TEST / contest / L / "in", TEST / contest / L / "out"
    passed = 0
    for nm in names:
        tc = TestCase(stdin=(ind / nm).read_text(errors="replace"),
                      expected_stdout=(outd / nm).read_text(errors="replace"), name=nm)
        r = run_python_code(code, tc, timeout_sec=TIMEOUT)
        if r.failure_type != "pass":
            return r.failure_type, len(names), passed
        passed += 1
    return "pass", len(names), passed


def main():
    window = [t["task_id"] for t in json.loads((DATA / "window_manifest.json").read_text())["tasks"]]
    fix = [t for t in window if (r := resolve(t)) and r[1] == "Ex"]
    print(f"Ex 매핑 대상: {len(fix)} tasks")

    gens = [json.loads(l) for l in open("results/window_generations.jsonl")]
    by_task = collections.defaultdict(list)
    for g in gens:
        by_task[g["task_id"]].append(g)

    gen_f = open(RESULTS / "fulltest_generations.jsonl", "a")
    fail_f = open(RESULTS / "fulltest_failures.jsonl", "a")
    added = 0
    for task in fix:
        loc = resolve(task)
        ntests = materialize(task, loc)
        ind = TEST / loc[0] / loc[1] / "in"
        names = sorted(p.name for p in ind.iterdir() if p.suffix == ".txt")
        nf = 0
        for g in by_task.get(task, []):
            status, nt, npass = judge(g["code"], loc, names)
            rec = {"task_id": task, "sample_idx": g["sample_idx"], "status": status,
                   "n_tests": nt, "n_passed": npass, "code": g["code"]}
            gen_f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            if status != "pass":
                nf += 1; fail_f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            added += 1
        print(f"  {task} (Ex, {ntests} tests): fail={nf}/{len(by_task.get(task,[]))}")
    gen_f.close(); fail_f.close()
    print(f"추가 재채점: {added} gens")

    # recompute summary from merged corpus
    allg = [json.loads(l) for l in open("results/fulltest_generations.jsonl")]
    st = collections.Counter(g["status"] for g in allg)
    st["generations"] = len(allg); st["tasks"] = len(set(g["task_id"] for g in allg))
    (RESULTS / "fulltest_summary.json").write_text(json.dumps(dict(st), ensure_ascii=False, indent=2))
    print("\n=== 병합 full-test summary ===\n" + json.dumps(dict(st), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
