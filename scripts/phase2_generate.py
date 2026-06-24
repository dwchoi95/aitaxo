"""Phase 2 — gpt-3.5-turbo generation + sample-I/O judging.

Per task in data/raw (manifest): prompt = problem.txt ONLY, temperature=1.0, n=5.
Judge each generation against AtCoder sample I/O (oracle; full tests need Test.zip).

Saves:
  results/phase2_generations.jsonl  # every (task, sample_idx) record
  results/phase2_failures.jsonl     # failing generations only (AI bug corpus → Phase 3)
  results/phase2_summary.json       # stats

Run: PYTHONPATH=src OPENAI_API_KEY=... .venv/bin/python scripts/phase2_generate.py
"""
from __future__ import annotations
import json, os, re, sys, time
from pathlib import Path
from openai import OpenAI

sys.path.insert(0, "src")
from aitaxo.execution.runner import run_python_code, classify_failure
from aitaxo.problems.schema import TestCase

OUT = Path("data/raw")
RESULTS = Path("results")
MODEL = "gpt-3.5-turbo"          # alias → -0125, knowledge cutoff Sep 2021 (leakage-free vs ConDefects)
TEMPERATURE = 1.0
N = 5
_CODE = re.compile(r"```(?:python)?\s*\n(.*?)```", re.DOTALL)


def extract_code(text: str) -> str:
    m = _CODE.search(text or "")
    return (m.group(1) if m else (text or "")).strip()


def load_tests(task_dir: Path):
    tcs = []
    tdir = task_dir / "testcases"
    if tdir.is_dir():
        for d in sorted(tdir.iterdir()):
            i, o = d / "in.txt", d / "out.txt"
            if i.exists() and o.exists():
                tcs.append(TestCase(stdin=i.read_text(), expected_stdout=o.read_text(), name=d.name))
    return tcs


def main():
    client = OpenAI()
    manifest = json.loads((OUT / "manifest.json").read_text())
    RESULTS.mkdir(exist_ok=True)
    gen_f = (RESULTS / "phase2_generations.jsonl").open("w", encoding="utf-8")
    fail_f = (RESULTS / "phase2_failures.jsonl").open("w", encoding="utf-8")
    log = (RESULTS / "phase2_log.txt").open("w", encoding="utf-8")

    stats = {"tasks": 0, "generations": 0, "pass": 0,
             "wrong_answer": 0, "runtime_error": 0, "compile_error": 0, "timeout": 0,
             "gen_error": 0, "tasks_with_any_fail": 0}
    t0 = time.perf_counter()

    for k, meta in enumerate(manifest, 1):
        task = meta["task_id"]
        d = OUT / task
        problem = (d / "problem.txt").read_text(encoding="utf-8")
        tests = load_tests(d)
        if not tests:
            continue
        stats["tasks"] += 1
        try:
            resp = client.chat.completions.create(
                model=MODEL, temperature=TEMPERATURE, n=N, max_tokens=1024,
                messages=[{"role": "user", "content": problem}],   # problem.txt 내용만
            )
        except Exception as e:
            stats["gen_error"] += 1
            log.write(f"[{k}] {task} GEN-ERROR {e}\n"); log.flush(); continue

        snapshot = resp.model
        task_fail = 0
        for idx, choice in enumerate(resp.choices, 1):
            raw = choice.message.content or ""
            code = extract_code(raw)
            results = [run_python_code(code, t, timeout_sec=5.0) for t in tests]
            status = classify_failure(results)
            stats["generations"] += 1
            stats[status] = stats.get(status, 0) + 1
            rec = {
                "task_id": task, "sample_idx": idx, "origin": "ai",
                "model": MODEL, "snapshot": snapshot, "temperature": TEMPERATURE,
                "difficulty": meta.get("difficulty"), "status": status,
                "code": code, "raw_response": raw,
                "test_results": [{"name": r.test_name, "type": r.failure_type,
                                  "stdout": r.stdout[:500], "stderr": r.stderr[:500]} for r in results],
            }
            gen_f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            if status != "pass":
                task_fail += 1
                fail_f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        gen_f.flush(); fail_f.flush()
        if task_fail:
            stats["tasks_with_any_fail"] += 1
        log.write(f"[{k}/{len(manifest)}] {task} diff={meta.get('difficulty')} "
                  f"fail={task_fail}/{N}\n"); log.flush()
        print(f"[{k}/{len(manifest)}] {task} fail={task_fail}/{N}")

    stats["elapsed_sec"] = round(time.perf_counter() - t0, 1)
    (RESULTS / "phase2_summary.json").write_text(json.dumps(stats, ensure_ascii=False, indent=2))
    gen_f.close(); fail_f.close(); log.close()
    print("\n=== Phase 2 summary ===")
    print(json.dumps(stats, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
