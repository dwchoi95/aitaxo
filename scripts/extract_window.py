"""Extract ConDefects Python tasks in the chosen window [2021-09-01, 2022-11-30)
into data/<pid>/{human,ai}.

  data/<pid>/
    meta.json                       # task_id, contest, date, difficulty, n_human
    human/<subId>/faulty.py         # ConDefects faultyVersion (인간 버그, 누수-free·인간진정)
    human/<subId>/correct.py        # ConDefects correctVersion (paired fix / reference)
    human/<subId>/faultLocation.txt # bug line(s) (FL ground truth)
    ai/                             # (reserved for Phase 2 gpt-3.5-turbo generations)

Window rationale: gpt-3.5-turbo cutoff 2021-09 (no leakage) ↔ ChatGPT 2022-11-30 (human-authentic).
Local-only (no scraping / no Test.zip).
"""
from __future__ import annotations
import json, shutil
from pathlib import Path

CD = Path("/Users/cdw/VSCode/aria/data/ConDefects")
OUT = Path("data")
LO, HI = "2021-09-01", "2022-11-30"   # contest date in [LO, HI)


def load_tbl(name):
    d = {}
    for line in (CD / name).read_text().splitlines():
        if line.strip():
            parts = line.split()
            d[parts[0]] = parts[1] if len(parts) > 1 else None
    return d


def main():
    date = load_tbl("date.txt")
    diff = load_tbl("difficulty.txt")
    code = CD / "Code"

    n_tasks = n_human = 0
    tasks = []
    for t in sorted(code.iterdir()):
        pydir = t / "Python"
        if not pydir.is_dir():
            continue
        d = date.get(t.name)
        if not d or not (LO <= d < HI):       # window filter
            continue
        subs = [s for s in sorted(pydir.iterdir()) if (s / "faultyVersion.py").exists()]
        if not subs:
            continue
        dst = OUT / t.name
        if dst.exists():
            shutil.rmtree(dst)
        (dst / "ai").mkdir(parents=True)       # reserved for Phase 2
        for s in subs:
            hd = dst / "human" / s.name
            hd.mkdir(parents=True)
            for src, out in [("faultyVersion.py", "faulty.py"),
                             ("correctVersion.py", "correct.py"),
                             ("faultLocation.txt", "faultLocation.txt")]:
                p = s / src
                if p.exists():
                    shutil.copy(p, hd / out)
            n_human += 1
        meta = {"task_id": t.name, "contest": t.name.rsplit("_", 1)[0],
                "date": d, "difficulty": int(diff[t.name]) if diff.get(t.name) and diff[t.name].lstrip("-").isdigit() else None,
                "n_human": len(subs), "origin_note": "ConDefects local; window [2021-09,2022-11-30)"}
        (dst / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2))
        tasks.append(meta)
        n_tasks += 1

    (OUT / "window_manifest.json").write_text(json.dumps(
        {"window": [LO, HI], "n_tasks": n_tasks, "n_human": n_human, "tasks": tasks},
        ensure_ascii=False, indent=2))
    print(f"추출 완료: {n_tasks} tasks / {n_human} human programs → data/<pid>/")
    print(f"manifest: data/window_manifest.json")
    # date sanity
    ds = [m["date"] for m in tasks]
    print(f"date 범위: {min(ds)} ~ {max(ds)} (모두 < {HI})")


if __name__ == "__main__":
    main()
