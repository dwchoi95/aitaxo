"""Phase 1 — ConDefects → data/raw/ substrate builder.

For each selected ConDefects Python task:
  - scrape AtCoder English statement + sample I/O  (공백①: AtCoder, CodeNet는 시기불일치로 기각)
  - materialize:
      data/raw/<task>/problem.txt            # statement (LLM 입력)
      data/raw/<task>/meta.json              # date, difficulty, contest, url, counts
      data/raw/<task>/testcases/<i>/{in,out}.txt   # AtCoder sample I/O (오라클; full=Test.zip 필요)
      data/raw/<task>/human/<subid>/{faulty.py,correct.py,faultLocation.txt}
  - append to data/raw/manifest.json and results/phase1_log.txt

Run: PYTHONPATH=src .venv/bin/python scripts/phase1_build_raw.py --limit 30 --per-bucket 4
"""
from __future__ import annotations
import argparse, json, time, urllib.request, socket, sys, shutil
from pathlib import Path
from bs4 import BeautifulSoup

CONDEFECTS = Path("/Users/cdw/VSCode/aria/data/ConDefects")
OUT = Path("data/raw")
RESULTS = Path("results")
UA = "Mozilla/5.0 (research; aitaxo ConDefects taxonomy study)"
socket.setdefaulttimeout(25)


def load_meta_tables():
    date = {}
    for line in (CONDEFECTS / "date.txt").read_text().splitlines():
        if line.strip():
            t, d = line.split(); date[t] = d
    diff = {}
    for line in (CONDEFECTS / "difficulty.txt").read_text().splitlines():
        if line.strip():
            parts = line.split()
            try: diff[parts[0]] = int(parts[1])
            except (IndexError, ValueError): diff[parts[0]] = None
    return date, diff


def python_tasks():
    code = CONDEFECTS / "Code"
    out = []
    for t in sorted(code.iterdir()):
        if (t / "Python").is_dir():
            subs = [s for s in (t / "Python").iterdir() if s.is_dir()]
            if subs:
                out.append((t.name, subs))
    return out


def stratified(tasks, diff, per_bucket, limit):
    """Pick ~per_bucket tasks per difficulty bucket (rated bands), capped at limit."""
    bands = [(0, 100), (100, 400), (400, 800), (800, 1200), (1200, 2000), (2000, 9999)]
    buckets = {b: [] for b in bands}
    for name, subs in tasks:
        d = diff.get(name)
        if d is None:
            continue
        for lo, hi in bands:
            if lo <= d < hi:
                buckets[(lo, hi)].append((name, subs)); break
    picked = []
    for b in bands:
        picked.extend(buckets[b][:per_bucket])
    return picked[:limit]


def fetch_atcoder(task: str, retries=3):
    contest = task.rsplit("_", 1)[0]
    url = f"https://atcoder.jp/contests/{contest}/tasks/{task}?lang=en"
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            html = urllib.request.urlopen(req).read().decode("utf-8", "replace")
            return url, html
        except Exception as e:
            if i == retries - 1:
                raise
            time.sleep(2 * (i + 1))


def parse_statement(html: str):
    soup = BeautifulSoup(html, "lxml")
    ts = soup.find(id="task-statement")
    scope = ts.find("span", class_="lang-en") or ts
    # statement text (full English block)
    statement = scope.get_text("\n")
    statement = "\n".join(l.rstrip() for l in statement.splitlines())
    statement = "\n".join(s for s in statement.split("\n\n") if True).strip()
    # sample I/O: pair "Sample Input N" h3 with following <pre>
    samples = []
    cur_in = None
    for el in scope.find_all(["h3", "pre"]):
        if el.name == "h3":
            label = el.get_text(strip=True).lower()
            cur = ("in" if "sample input" in label else
                   "out" if "sample output" in label else None)
        else:  # pre
            if cur == "in":
                cur_in = el.get_text()
            elif cur == "out" and cur_in is not None:
                samples.append((cur_in, el.get_text())); cur_in = None
            cur = None
    return statement, samples


def materialize(task, subs, date, diff, url, statement, samples):
    d = OUT / task
    if d.exists():
        shutil.rmtree(d)
    (d).mkdir(parents=True)
    (d / "problem.txt").write_text(statement, encoding="utf-8")
    # testcases (AtCoder samples)
    for i, (inp, out) in enumerate(samples, 1):
        tc = d / "testcases" / f"{i:03d}"
        tc.mkdir(parents=True)
        (tc / "in.txt").write_text(inp, encoding="utf-8")
        (tc / "out.txt").write_text(out, encoding="utf-8")
    # human programs
    n_human = 0
    for s in subs:
        hd = d / "human" / s.name
        hd.mkdir(parents=True)
        for src, dst in [("faultyVersion.py", "faulty.py"),
                         ("correctVersion.py", "correct.py"),
                         ("faultLocation.txt", "faultLocation.txt")]:
            p = s / src
            if p.exists():
                shutil.copy(p, hd / dst)
        n_human += 1
    meta = {
        "task_id": task, "source": "condefects",
        "contest": task.rsplit("_", 1)[0], "atcoder_url": url,
        "date": date.get(task), "difficulty": diff.get(task),
        "n_human": n_human, "n_sample_tests": len(samples),
        "tests_note": "AtCoder sample I/O only; full hidden tests require ConDefects Test.zip",
    }
    (d / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2))
    return meta


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=30)
    ap.add_argument("--per-bucket", type=int, default=5)
    ap.add_argument("--delay", type=float, default=1.0)
    args = ap.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    RESULTS.mkdir(parents=True, exist_ok=True)
    date, diff = load_meta_tables()
    tasks = python_tasks()
    picked = stratified(tasks, diff, args.per_bucket, args.limit)
    print(f"Python tasks total: {len(tasks)} | selected (stratified): {len(picked)}")

    log = RESULTS / "phase1_log.txt"
    manifest = []
    with log.open("w", encoding="utf-8") as lg:
        for i, (task, subs) in enumerate(picked, 1):
            try:
                url, html = fetch_atcoder(task)
                statement, samples = parse_statement(html)
                if not statement or not samples:
                    raise ValueError(f"empty statement={not statement} samples={len(samples)}")
                meta = materialize(task, subs, date, diff, url, statement, samples)
                manifest.append(meta)
                msg = (f"[{i}/{len(picked)}] OK {task} diff={meta['difficulty']} "
                       f"human={meta['n_human']} samples={meta['n_sample_tests']} stmt={len(statement)}c")
            except Exception as e:
                msg = f"[{i}/{len(picked)}] FAIL {task}: {type(e).__name__}: {e}"
            print(msg); lg.write(msg + "\n"); lg.flush()
            time.sleep(args.delay)

    (OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2))
    print(f"\nDONE. {len(manifest)}/{len(picked)} tasks materialized → {OUT}/")
    print(f"manifest: {OUT}/manifest.json | log: {log}")


if __name__ == "__main__":
    main()
