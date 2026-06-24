"""Re-judge existing gpt-3.5-turbo generations against ConDefects FULL hidden tests.

Tests live at /Users/cdw/VSCode/aria/data/ConDefects/Test/<contest>/<LETTER>/{in,out}/<name>.txt
(63GB → referenced in place, not copied). Short-circuit on first failing test.

Input : results/window_generations.jsonl  (2,140 gens with code)
Output: results/fulltest_generations.jsonl, fulltest_failures.jsonl, fulltest_summary.json,
        fulltest_taxonomy.json ; per task: data/<task>/ai/fulltest.json
"""
from __future__ import annotations
import json, sys, time, collections
from pathlib import Path

sys.path.insert(0, "src")
from aitaxo.execution.runner import run_python_code
from aitaxo.problems.schema import TestCase

TEST = Path("/Users/cdw/VSCode/aria/data/ConDefects/Test")
RESULTS = Path("results")
TIMEOUT = 3.0


def test_names(task):
    contest, letter = task.rsplit("_", 1)
    ind = TEST / contest / letter.upper() / "in"
    outd = TEST / contest / letter.upper() / "out"
    if not ind.is_dir() or not outd.is_dir():
        return None, None
    names = sorted(p.name for p in ind.iterdir() if p.suffix == ".txt" and (outd / p.name).exists())
    return (contest, letter.upper()), names


def judge(code, task, loc, names):
    """Run code vs full tests, short-circuit on first non-pass. Returns (status, n_tests, n_passed)."""
    contest, letter = loc
    ind = TEST / contest / letter / "in"
    outd = TEST / contest / letter / "out"
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
    gens = [json.loads(l) for l in open("results/window_generations.jsonl")]
    by_task = collections.OrderedDict()
    for g in gens:
        by_task.setdefault(g["task_id"], []).append(g)

    gen_f = open(RESULTS / "fulltest_generations.jsonl", "w")
    fail_f = open(RESULTS / "fulltest_failures.jsonl", "w")
    log = open(RESULTS / "fulltest_log.txt", "w")
    stats = collections.Counter()
    no_test = []
    t0 = time.perf_counter()

    for k, (task, glist) in enumerate(by_task.items(), 1):
        loc, names = test_names(task)
        if not names:
            no_test.append(task); stats["task_no_test"] += 1
            log.write(f"[{k}] {task} NO-FULLTEST\n"); continue
        nf = 0
        for g in glist:
            status, nt, npass = judge(g["code"], task, loc, names)
            stats[status] += 1; stats["generations"] += 1
            rec = {"task_id": task, "sample_idx": g["sample_idx"], "status": status,
                   "n_tests": nt, "n_passed": npass, "difficulty": None, "code": g["code"]}
            gen_f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            if status != "pass":
                nf += 1
                fail_f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        gen_f.flush(); fail_f.flush()
        stats["tasks"] += 1
        log.write(f"[{k}/{len(by_task)}] {task} tests={len(names)} fail={nf}/{len(glist)}\n"); log.flush()
        if k % 20 == 0:
            print(f"[{k}/{len(by_task)}] {task} ({len(names)} tests) elapsed={time.perf_counter()-t0:.0f}s")

    stats["elapsed_sec"] = round(time.perf_counter() - t0, 1)
    stats["no_fulltest_tasks"] = len(no_test)
    (RESULTS / "fulltest_summary.json").write_text(json.dumps(dict(stats), ensure_ascii=False, indent=2))
    gen_f.close(); fail_f.close(); log.close()
    print("\n=== FULL-TEST 재채점 summary ===")
    print(json.dumps(dict(stats), ensure_ascii=False, indent=2))
    print("no-fulltest tasks:", len(no_test), no_test[:8])


if __name__ == "__main__":
    main()
