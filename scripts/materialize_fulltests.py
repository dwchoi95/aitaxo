"""Replace sample testcases in data/<task>/testcases/ with ConDefects FULL hidden tests.

Source: /Users/cdw/VSCode/aria/data/ConDefects/Test/<contest>/<LETTER>/{in,out}/<name>.txt
Dest  : data/<task>/testcases/<name>/{in.txt,out.txt}   (one dir per test; existing samples removed)

22 window tasks without full tests keep their AtCoder samples (logged).
"""
from __future__ import annotations
import json, shutil
from pathlib import Path

TEST = Path("/Users/cdw/VSCode/aria/data/ConDefects/Test")
DATA = Path("data")


def main():
    tasks = [t["task_id"] for t in json.loads((DATA / "window_manifest.json").read_text())["tasks"]]
    replaced = kept_samples = ncopied = 0
    no_full = []
    for k, t in enumerate(tasks, 1):
        contest, letter = t.rsplit("_", 1)
        ind = TEST / contest / letter.upper() / "in"
        outd = TEST / contest / letter.upper() / "out"
        if not ind.is_dir() or not outd.is_dir():
            no_full.append(t); kept_samples += 1; continue
        tcdir = DATA / t / "testcases"
        if tcdir.exists():
            shutil.rmtree(tcdir)           # drop AtCoder samples
        tcdir.mkdir(parents=True)
        n = 0
        for f in sorted(ind.iterdir()):
            if f.suffix != ".txt":
                continue
            o = outd / f.name
            if not o.exists():
                continue
            dst = tcdir / f.stem
            dst.mkdir()
            shutil.copy(f, dst / "in.txt")
            shutil.copy(o, dst / "out.txt")
            n += 1
        ncopied += n
        replaced += 1
        if k % 25 == 0:
            print(f"[{k}/{len(tasks)}] {t}: {n} tests | total copied={ncopied}")
    manifest = {"source": "ConDefects/Test (full hidden tests)",
                "tasks_replaced": replaced, "tests_copied": ncopied,
                "tasks_kept_samples": kept_samples, "no_fulltest_tasks": no_full}
    (DATA / "testcases_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2))
    print(f"\nDONE. {replaced} tasks 교체 / {ncopied} tests 복사 | sample 유지 {kept_samples} (full 없음)")
    print("no-fulltest:", no_full)


if __name__ == "__main__":
    main()
