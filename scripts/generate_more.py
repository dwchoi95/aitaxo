"""Generate 5 MORE solutions per task (gen_6..10) → 10 total, judge on FULL hidden tests.

Same setup: gpt-3.5-turbo, system+user (problem.txt), temp 1.0, n=5.
Saves: data/<task>/ai/gen_6..10.py ; results/gen2_generations.jsonl, gen2_failures.jsonl
Resume: skips tasks that already have gen_10.py.
"""
from __future__ import annotations
import json, re, sys, time
from pathlib import Path
from openai import OpenAI

sys.path.insert(0, "src")
from execution.runner import run_python_code
from problems.schema import TestCase

TEST = Path("/Users/cdw/VSCode/aria/data/ConDefects/Test")
DATA = Path("data"); RESULTS = Path("results")
MODEL, TEMP, N, MAXTOK, TIMEOUT = "gpt-3.5-turbo", 1.0, 5, 1024, 3.0
START_IDX = 6
SYSTEM = ("You are a competitive programming assistant. Read from standard input and "
          "write to standard output. Output ONLY a complete Python 3 program inside a "
          "single ```python code block. No explanation.")
_CODE = re.compile(r"```(?:python)?\s*\n(.*?)```", re.DOTALL)


def extract_code(t):
    m = _CODE.search(t or ""); return (m.group(1) if m else (t or "")).strip()


def resolve(task):
    contest, letter = task.rsplit("_", 1)
    for L in (letter.upper(), "Ex"):       # ConDefects _h <-> AtCoder Ex
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
            return r.failure_type, len(names), passed
        passed += 1
    return "pass", len(names), passed


def main():
    tasks = [t["task_id"] for t in json.loads((DATA / "window_manifest.json").read_text())["tasks"]]
    client = OpenAI()
    gen_f = open(RESULTS / "gen2_generations.jsonl", "a")
    fail_f = open(RESULTS / "gen2_failures.jsonl", "a")
    log = open(RESULTS / "gen2_log.txt", "a")
    import collections
    stats = collections.Counter()
    t0 = time.perf_counter()

    for k, task in enumerate(tasks, 1):
        d = DATA / task
        if (d / "ai" / f"gen_{START_IDX + N - 1}.py").exists():
            stats["skipped"] += 1; continue
        problem = (d / "problem.txt").read_text(encoding="utf-8")
        tdir = resolve(task)
        if tdir is None:
            stats["no_test"] += 1; continue
        names = sorted(p.name for p in (tdir / "in").iterdir()
                       if p.suffix == ".txt" and (tdir / "out" / p.name).exists())
        try:
            resp = client.chat.completions.create(
                model=MODEL, temperature=TEMP, n=N, max_tokens=MAXTOK,
                messages=[{"role": "system", "content": SYSTEM},
                          {"role": "user", "content": problem}])
        except Exception as e:
            stats["gen_error"] += 1; log.write(f"[{k}] {task} GENERR {e}\n"); log.flush(); continue
        nf = 0
        for j, ch in enumerate(resp.choices, START_IDX):
            code = extract_code(ch.message.content or "")
            (d / "ai" / f"gen_{j}.py").write_text(code, encoding="utf-8")
            status, nt, npass = judge(code, tdir, names)
            stats[status] += 1; stats["generations"] += 1
            rec = {"task_id": task, "sample_idx": j, "status": status,
                   "n_tests": nt, "n_passed": npass, "code": code}
            gen_f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            if status != "pass":
                nf += 1; fail_f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        gen_f.flush(); fail_f.flush()
        stats["tasks"] += 1
        log.write(f"[{k}/{len(tasks)}] {task} fail={nf}/{N}\n"); log.flush()
        if k % 20 == 0:
            print(f"[{k}/{len(tasks)}] {task} elapsed={time.perf_counter()-t0:.0f}s gens={stats['generations']}")

    stats["elapsed_sec"] = round(time.perf_counter() - t0, 1)
    (RESULTS / "gen2_summary.json").write_text(json.dumps(dict(stats), ensure_ascii=False, indent=2))
    gen_f.close(); fail_f.close(); log.close()
    print("\n=== gen2 (gen_6..10) summary ===\n" + json.dumps(dict(stats), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
