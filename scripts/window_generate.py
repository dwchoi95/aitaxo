"""Full 432-window generation: scrape (normalized) → gpt-3.5-turbo (system+user) → judge.

Prompt policy (확정): system='write Python 3 only' + user=normalized problem.txt.
Saves per task: data/<task>/problem.txt, testcases/<i>/{in,out}.txt, ai/gen_<k>.py, ai/results.json
Global: results/window_generations.jsonl, window_failures.jsonl, window_summary.json
Resumable: skips tasks whose ai/results.json already exists.

Run: PYTHONPATH=src .venv/bin/python scripts/window_generate.py [--limit N] [--test-one TASK]
"""
from __future__ import annotations
import argparse, json, re, socket, sys, time, urllib.request
from pathlib import Path
from bs4 import BeautifulSoup
from openai import OpenAI

sys.path.insert(0, "src")
from execution.runner import run_python_code, classify_failure
from problems.schema import TestCase

socket.setdefaulttimeout(25)
DATA = Path("data")
RESULTS = Path("results")
MODEL, TEMP, N, MAXTOK = "gpt-3.5-turbo", 1.0, 5, 1024
SYSTEM = ("You are a competitive programming assistant. Read from standard input and "
          "write to standard output. Output ONLY a complete Python 3 program inside a "
          "single ```python code block. No explanation.")
UA = "Mozilla/5.0 (research; aitaxo ConDefects taxonomy study)"
_CODE = re.compile(r"```(?:python)?\s*\n(.*?)```", re.DOTALL)


def extract_code(t):
    m = _CODE.search(t or ""); return (m.group(1) if m else (t or "")).strip()


def build_statement(scope):
    """Structured reconstruction → readable prose (vars inlined), samples verbatim."""
    out = []
    for el in scope.find_all(["h3", "p", "pre", "ul"]):
        if el.name == "h3":
            out.append("\n## " + el.get_text(strip=True))
        elif el.name == "pre":
            out.append("```\n" + el.get_text().rstrip() + "\n```")
        elif el.name == "ul":
            for li in el.find_all("li"):
                t = re.sub(r"\s+", " ", li.get_text(" ")).strip()
                if t: out.append("- " + t)
        else:  # p
            t = re.sub(r"\s+", " ", el.get_text(" ")).strip()
            if t: out.append(t)
    return "\n".join(out).strip()


def scrape(task, retries=3):
    contest = task.rsplit("_", 1)[0]
    url = f"https://atcoder.jp/contests/{contest}/tasks/{task}?lang=en"
    for i in range(retries):
        try:
            html = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA})).read().decode("utf-8", "replace")
            break
        except Exception:
            if i == retries - 1: raise
            time.sleep(2 * (i + 1))
    soup = BeautifulSoup(html, "lxml")
    ts = soup.find(id="task-statement"); scope = ts.find("span", class_="lang-en") or ts
    statement = build_statement(scope)
    samples, cur, cin = [], None, None
    for el in scope.find_all(["h3", "pre"]):
        if el.name == "h3":
            lb = el.get_text(strip=True).lower()
            cur = "in" if "sample input" in lb else "out" if "sample output" in lb else None
        else:
            if cur == "in": cin = el.get_text()
            elif cur == "out" and cin is not None: samples.append((cin, el.get_text())); cin = None
            cur = None
    return url, statement, samples


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--delay", type=float, default=0.6)
    ap.add_argument("--test-one", default=None)
    args = ap.parse_args()

    if args.test_one:
        _, st, sm = scrape(args.test_one)
        print(f"=== {args.test_one}: statement ({len(st)}c), {len(sm)} samples ===\n{st[:1200]}")
        return

    tasks = [t["task_id"] for t in json.loads((DATA / "window_manifest.json").read_text())["tasks"]]
    if args.limit: tasks = tasks[:args.limit]
    client = OpenAI()
    gen_f = (RESULTS / "window_generations.jsonl").open("a", encoding="utf-8")
    fail_f = (RESULTS / "window_failures.jsonl").open("a", encoding="utf-8")
    log = (RESULTS / "window_gen_log.txt").open("a", encoding="utf-8")
    stats = collections_counter()
    t0 = time.perf_counter()

    for k, task in enumerate(tasks, 1):
        d = DATA / task
        if (d / "ai" / "results.json").exists():     # resume: skip done
            stats["skipped"] += 1; continue
        try:
            url, statement, samples = scrape(task)
            if not statement or not samples:
                raise ValueError(f"empty stmt={not statement} samples={len(samples)}")
            (d / "problem.txt").write_text(statement, encoding="utf-8")
            for i, (inp, out) in enumerate(samples, 1):
                tc = d / "testcases" / f"{i:03d}"; tc.mkdir(parents=True, exist_ok=True)
                (tc / "in.txt").write_text(inp); (tc / "out.txt").write_text(out)
            tests = [TestCase(stdin=i, expected_stdout=o, name=f"{j:03d}") for j, (i, o) in enumerate(samples, 1)]
            resp = client.chat.completions.create(
                model=MODEL, temperature=TEMP, n=N, max_tokens=MAXTOK,
                messages=[{"role": "system", "content": SYSTEM},
                          {"role": "user", "content": statement}])
            (d / "ai").mkdir(exist_ok=True)
            per = []
            for idx, ch in enumerate(resp.choices, 1):
                code = extract_code(ch.message.content or "")
                (d / "ai" / f"gen_{idx}.py").write_text(code, encoding="utf-8")
                results = [run_python_code(code, t, timeout_sec=5.0) for t in tests]
                status = classify_failure(results)
                stats[status] += 1; stats["generations"] += 1
                rec = {"task_id": task, "sample_idx": idx, "origin": "ai", "model": MODEL,
                       "snapshot": resp.model, "status": status,
                       "code": code,
                       "test_results": [{"name": r.test_name, "type": r.failure_type,
                                         "stdout": r.stdout[:300], "stderr": r.stderr[:300]} for r in results]}
                per.append({"idx": idx, "status": status})
                gen_f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                if status != "pass":
                    fail_f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            (d / "ai" / "results.json").write_text(json.dumps(
                {"task_id": task, "snapshot": resp.model, "gens": per}, ensure_ascii=False, indent=2))
            gen_f.flush(); fail_f.flush()
            stats["tasks"] += 1
            nfail = sum(1 for p in per if p["status"] != "pass")
            msg = f"[{k}/{len(tasks)}] OK {task} fail={nfail}/{N}"
        except Exception as e:
            stats["task_error"] += 1
            msg = f"[{k}/{len(tasks)}] FAIL {task}: {type(e).__name__}: {e}"
        log.write(msg + "\n"); log.flush()
        print(msg)
        time.sleep(args.delay)

    stats["elapsed_sec"] = round(time.perf_counter() - t0, 1)
    (RESULTS / "window_summary.json").write_text(json.dumps(dict(stats), ensure_ascii=False, indent=2))
    gen_f.close(); fail_f.close(); log.close()
    print("\n=== window summary ===\n" + json.dumps(dict(stats), ensure_ascii=False, indent=2))


def collections_counter():
    import collections
    return collections.Counter()


if __name__ == "__main__":
    main()
