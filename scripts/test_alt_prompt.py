"""Quick test of the ALTERNATIVE prompt (system + user) on 5 window tasks.

Checks: (1) does the system prompt stop C++ drift (→ Python)?  (2) does judging work?
Saves: results/test_alt_prompt.jsonl, results/test_alt_prompt_summary.json
"""
from __future__ import annotations
import json, re, socket, sys, urllib.request
from pathlib import Path
from openai import OpenAI

sys.path.insert(0, "src")
from aitaxo.execution.runner import run_python_code, classify_failure
from aitaxo.problems.schema import TestCase

socket.setdefaulttimeout(25)
MODEL, TEMP, N = "gpt-3.5-turbo", 1.0, 5
SYSTEM = ("You are a competitive programming assistant. Read from standard input and "
          "write to standard output. Output ONLY a complete Python 3 program inside a "
          "single ```python code block. No explanation.")
_CODE = re.compile(r"```(?:python)?\s*\n(.*?)```", re.DOTALL)


def extract_code(t):
    m = _CODE.search(t or ""); return (m.group(1) if m else (t or "")).strip()

def lang(c):
    if re.search(r'#include|std::|int main\s*\(|cout|cin>>', c): return 'cpp'
    if re.search(r'\b(def|print|input|import)\b', c) and '#include' not in c: return 'python'
    return 'other'

def scrape(task):
    contest = task.rsplit("_", 1)[0]
    url = f"https://atcoder.jp/contests/{contest}/tasks/{task}?lang=en"
    html = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (research aitaxo)"})).read().decode("utf-8", "replace")
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "lxml")
    ts = soup.find(id="task-statement"); scope = ts.find("span", class_="lang-en") or ts
    s = scope.get_text("\n"); statement = "\n".join(l.rstrip() for l in s.splitlines()).strip()
    samples, cur, cin = [], None, None
    for el in scope.find_all(["h3", "pre"]):
        if el.name == "h3":
            lb = el.get_text(strip=True).lower()
            cur = "in" if "sample input" in lb else "out" if "sample output" in lb else None
        else:
            if cur == "in": cin = el.get_text()
            elif cur == "out" and cin is not None: samples.append((cin, el.get_text())); cin = None
            cur = None
    return statement, samples


def main():
    man = json.loads(Path("data/window_manifest.json").read_text())["tasks"]
    man = [t for t in man if t.get("difficulty") is not None]
    man.sort(key=lambda t: t["difficulty"])
    # difficulty spread: 5 picks
    idxs = [int(i * (len(man) - 1) / 4) for i in range(5)]
    picks = [man[i] for i in idxs]
    print("선택(난이도 스프레드):", [(p["task_id"], p["difficulty"]) for p in picks])

    client = OpenAI()
    out = open("results/test_alt_prompt.jsonl", "w")
    summ = {"by_lang": {}, "by_status": {}, "per_task": []}
    for p in picks:
        task = p["task_id"]
        statement, samples = scrape(task)
        tests = [TestCase(stdin=i, expected_stdout=o, name=str(k)) for k, (i, o) in enumerate(samples, 1)]
        resp = client.chat.completions.create(
            model=MODEL, temperature=TEMP, n=N, max_tokens=1024,
            messages=[{"role": "system", "content": SYSTEM},
                      {"role": "user", "content": statement}])
        row = {"task": task, "diff": p["difficulty"], "gens": []}
        for ch in resp.choices:
            code = extract_code(ch.message.content or "")
            lg = lang(code)
            results = [run_python_code(code, t, timeout_sec=5.0) for t in tests]
            st = classify_failure(results)
            row["gens"].append({"lang": lg, "status": st})
            summ["by_lang"][lg] = summ["by_lang"].get(lg, 0) + 1
            summ["by_status"][st] = summ["by_status"].get(st, 0) + 1
            out.write(json.dumps({"task": task, "lang": lg, "status": st, "code": code}, ensure_ascii=False) + "\n")
        np = sum(g["lang"] == "python" for g in row["gens"])
        pa = sum(g["status"] == "pass" for g in row["gens"])
        row["python"] = np; row["pass"] = pa
        summ["per_task"].append(row)
        print(f"  {task} (diff {p['difficulty']}): python {np}/5, pass {pa}/5, "
              f"statuses={[g['status'] for g in row['gens']]}")
    out.close()
    Path("results/test_alt_prompt_summary.json").write_text(json.dumps(summ, ensure_ascii=False, indent=2))
    print("\n=== 합계 (25 생성) ===")
    print("언어:", summ["by_lang"])
    print("status:", summ["by_status"])
    print("저장: results/test_alt_prompt.jsonl, results/test_alt_prompt_summary.json")


if __name__ == "__main__":
    main()
