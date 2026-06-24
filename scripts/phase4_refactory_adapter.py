"""Phase 4 — convert data/raw + AI Python bugs into Refactory tool input format.

Refactory expects:
  data/question_<task>/
    description.txt
    ans/input_NNN.txt, output_NNN.txt        # test suite (AtCoder sample I/O)
    code/correct/correct_<task>_<i>.py        # reference correct solutions (ConDefects correctVersion)
    code/wrong/wrong_<task>_<i>.py            # buggy programs to repair (AI-generated Python bugs)

Output: tools/refactory/data_condefects/
"""
from __future__ import annotations
import json, shutil
from pathlib import Path

RAW = Path("data/raw")
OUT = Path("tools/refactory/data_condefects")
BUGS = Path("results/phase3_python_bugs.jsonl")


def main():
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)
    bugs_by_task = {}
    for line in BUGS.read_text().splitlines():
        b = json.loads(line)
        bugs_by_task.setdefault(b["task_id"], []).append(b)

    built = 0
    for task, bugs in bugs_by_task.items():
        d = RAW / task
        tdir = d / "testcases"
        humans = sorted((d / "human").glob("*/correct.py")) if (d / "human").exists() else []
        tests = sorted(tdir.iterdir()) if tdir.exists() else []
        if not humans or not tests:
            continue
        q = OUT / f"question_{task}"
        (q / "ans").mkdir(parents=True)
        (q / "code" / "correct").mkdir(parents=True)
        (q / "code" / "wrong").mkdir(parents=True)
        (q / "code" / "reference").mkdir(parents=True)
        (q / "description.txt").write_text((d / "problem.txt").read_text())
        # test suite
        for i, tc in enumerate(tests, 1):
            shutil.copy(tc / "in.txt", q / "ans" / f"input_{i:03d}.txt")
            shutil.copy(tc / "out.txt", q / "ans" / f"output_{i:03d}.txt")
        # reference correct (Refactory uses a correct pool); also drop one into reference/
        for i, h in enumerate(humans, 1):
            shutil.copy(h, q / "code" / "correct" / f"correct_{task}_{i:03d}.py")
        shutil.copy(humans[0], q / "code" / "reference" / f"reference_{task}.py")
        # wrong (AI python bugs)
        for i, b in enumerate(bugs, 1):
            (q / "code" / "wrong" / f"wrong_{task}_{i:03d}.py").write_text(b["code"])
        built += 1
    print(f"Refactory 입력 생성: {built} questions → {OUT}/")
    print(f"  (각 question: correct={'ConDefects correctVersion'}, wrong=AI Python bugs, ans=AtCoder samples)")


if __name__ == "__main__":
    main()
