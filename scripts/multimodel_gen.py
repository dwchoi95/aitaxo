"""Multi-model generation + full-test judging for the capability spectrum (RQ).

Generates N solutions per problem with an additional model and judges each against
the full hidden tests, recording the same fields as the main pipeline. Resumable:
skips problems already present in the output file.

Usage: multimodel_gen.py <model> <n> <out.jsonl>
  gpt-4-0613 : leakage-free strong model (classic chat: temperature, n, max_tokens)
  gpt-5.5    : modern recall-regime model (reasoning: max_completion_tokens)
"""
from __future__ import annotations
import json, re, sys, collections
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from openai import OpenAI

sys.path.insert(0, "src")
from execution.runner import run_python_code
from problems.schema import TestCase

TEST = Path("/Users/cdw/VSCode/aria/data/ConDefects/Test")
DATA = Path("data"); TIMEOUT = 3.0
SYS = "Output ONLY a complete Python 3 program that reads from standard input and writes to standard output. No explanation."

MODEL = sys.argv[1]; N = int(sys.argv[2]); OUT = Path(sys.argv[3])
REASONING = MODEL.startswith("gpt-5") or MODEL.startswith("o1") or MODEL.startswith("o3")
client = OpenAI()


def resolve(task):
    contest, letter = task.rsplit("_", 1)
    for L in (letter.upper(), "Ex"):
        if (TEST / contest / L / "in").is_dir():
            return TEST / contest / L
    return None


def names_of(tdir):
    return sorted(p.name for p in (tdir / "in").iterdir()
                  if p.suffix == ".txt" and (tdir / "out" / p.name).exists())


def judge(code, tdir, names):
    npass = 0
    for nm in names:
        tc = TestCase(stdin=(tdir / "in" / nm).read_text(errors="replace"),
                      expected_stdout=(tdir / "out" / nm).read_text(errors="replace"), name=nm)
        r = run_python_code(code, tc, timeout_sec=TIMEOUT)
        if r.failure_type != "pass":
            return r.failure_type, npass, len(names)
        npass += 1
    return "pass", npass, len(names)


def extract(text):
    m = re.search(r"```(?:python)?\s*(.*?)```", text or "", re.DOTALL)
    return (m.group(1) if m else (text or "")).strip()


def generate(prompt):
    if REASONING:
        kwargs = dict(model=MODEL, n=N, max_completion_tokens=4000,
                      messages=[{"role": "system", "content": SYS}, {"role": "user", "content": prompt}])
        try:
            kwargs["reasoning_effort"] = "none"
            r = client.chat.completions.create(**kwargs)
        except Exception:
            kwargs.pop("reasoning_effort", None)
            r = client.chat.completions.create(**kwargs)
    else:
        r = client.chat.completions.create(model=MODEL, temperature=1.0, n=N, max_tokens=900,
                                           messages=[{"role": "system", "content": SYS}, {"role": "user", "content": prompt}])
    return [extract(ch.message.content) for ch in r.choices]


def main():
    man = {t["task_id"]: t for t in json.loads((DATA / "window_manifest.json").read_text())["tasks"]}
    done = set()
    if OUT.exists():
        for l in OUT.open():
            try: done.add(json.loads(l)["task_id"])
            except Exception: pass
    todo = [t for t in man if t not in done and resolve(t) is not None
            and (DATA / t / "problem.txt").exists()]
    print(f"{MODEL}: {len(done)} done, {len(todo)} to do (N={N})", flush=True)
    out = OUT.open("a")
    counter = {"n": 0}

    def work(task):
        tdir = resolve(task); names = names_of(tdir)
        prompt = (DATA / task / "problem.txt").read_text(errors="replace")[:4000]
        try:
            codes = generate(prompt)
        except Exception as e:
            print(f"  gen fail {task}: {str(e)[:120]}", flush=True); return []
        rows = []
        for i, code in enumerate(codes, 1):
            status, npass, ntests = judge(code, tdir, names) if code else ("compile_error", 0, len(names))
            rows.append({"task_id": task, "sample_idx": i, "code": code, "status": status,
                         "n_passed": npass, "n_tests": ntests, "difficulty": man[task].get("difficulty")})
        return rows

    with ThreadPoolExecutor(max_workers=16 if REASONING else 8) as ex:
        for rows in ex.map(work, todo):
            for r in rows:
                out.write(json.dumps(r, ensure_ascii=False) + "\n")
            out.flush()
            counter["n"] += 1
            if counter["n"] % 25 == 0:
                print(f"  {counter['n']}/{len(todo)} problems", flush=True)
    out.close()
    # quick summary
    st = collections.Counter()
    for l in OUT.open():
        st[json.loads(l)["status"]] += 1
    tot = sum(st.values()); pas = st.get("pass", 0)
    print(f"DONE {MODEL}: {tot} gens, pass {pas} ({100*pas/tot:.1f}%), "
          f"WA {st['wrong_answer']} TLE {st['timeout']} RE {st['runtime_error']} CE {st['compile_error']}", flush=True)


if __name__ == "__main__":
    main()
