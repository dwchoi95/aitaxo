"""P3: LLM-based APR baseline on AIBugBench.

For a difficulty-stratified sample of WA bugs, give an LLM the problem, the buggy
code, and the first failing test (input/expected/actual), ask for a fixed program,
then re-judge against the FULL hidden tests. Two repairers are compared:
  - self  : gpt-3.5-turbo (same family as the generator) -> tests limitation L3
  - cross : gpt-4o-mini    (a different model)
Reports plausible repair rate overall, by difficulty, and by sub-type (if P2 labels exist).

Output: results/p3_apr.json
"""
from __future__ import annotations
import json, re, sys, random, collections
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from openai import OpenAI

sys.path.insert(0, "src")
from execution.runner import run_python_code
from problems.schema import TestCase

TEST = Path("/Users/cdw/VSCode/aria/data/ConDefects/Test")
DATA = Path("data"); RESULTS = Path("results"); TIMEOUT = 3.0
REPAIRERS = ["gpt-3.5-turbo", "gpt-4o-mini"]
PER_BAND = 70


def resolve(task):
    contest, letter = task.rsplit("_", 1)
    for L in (letter.upper(), "Ex"):
        if (TEST / contest / L / "in").is_dir():
            return TEST / contest / L
    return None


def names_of(tdir):
    return sorted(p.name for p in (tdir / "in").iterdir()
                  if p.suffix == ".txt" and (tdir / "out" / p.name).exists())


def first_fail(code, tdir, names):
    for nm in names:
        exp = (tdir / "out" / nm).read_text(errors="replace")
        tc = TestCase(stdin=(tdir / "in" / nm).read_text(errors="replace"), expected_stdout=exp, name=nm)
        r = run_python_code(code, tc, timeout_sec=TIMEOUT)
        if r.failure_type != "pass":
            return tc.stdin, exp, r.stdout, r.failure_type
    return None


def passes_all(code, tdir, names):
    for nm in names:
        tc = TestCase(stdin=(tdir / "in" / nm).read_text(errors="replace"),
                      expected_stdout=(tdir / "out" / nm).read_text(errors="replace"), name=nm)
        if run_python_code(code, tc, timeout_sec=TIMEOUT).failure_type != "pass":
            return False
    return True


def extract(text):
    m = re.search(r"```(?:python)?\s*(.*?)```", text, re.DOTALL)
    return (m.group(1) if m else text).strip()


def repair(client, model, problem, code, fail):
    stdin, exp, act, ft = fail
    prompt = (f"# Problem\n{problem[:1200]}\n\n# Buggy Python solution\n{code[:1200]}\n\n"
              f"# A failing test ({ft})\nInput:\n{stdin[:400]}\nExpected:\n{exp[:300]}\n"
              f"Actual:\n{act[:300]}\n\nFix the program. Output ONLY a complete Python 3 program.")
    try:
        r = client.chat.completions.create(
            model=model, temperature=0.0, max_tokens=900,
            messages=[{"role": "system", "content": "You are an expert competitive programmer fixing a buggy solution."},
                      {"role": "user", "content": prompt}])
        return extract(r.choices[0].message.content or "")
    except Exception:
        return ""


def band(d):
    return "easy" if d < 400 else "medium" if d < 1200 else "hard" if d < 2000 else "vhard"


def main():
    client = OpenAI()
    man = {t["task_id"]: t for t in json.loads((DATA / "window_manifest.json").read_text())["tasks"]}
    # collect WA bugs with code
    wa = {}
    for fn in ("results/fulltest_generations.jsonl", "results/gen2_generations.jsonl"):
        for l in open(fn):
            g = json.loads(l)
            if g["status"] == "wrong_answer" and g["task_id"] in man:
                wa[(g["task_id"], g["sample_idx"])] = g["code"]
    # sub-type labels (optional)
    sub = {}
    p2 = RESULTS / "p2_subtypes.jsonl"
    if p2.exists():
        for l in open(p2):
            d = json.loads(l); sub[(d["task_id"], d["idx"])] = d["subtype"]
    # stratified sample
    byband = collections.defaultdict(list)
    for (t, i), code in wa.items():
        d = man[t].get("difficulty")
        if d is not None:
            byband[band(d)].append((t, i, code, d))
    random.seed(7)
    sample = []
    for b, items in byband.items():
        random.shuffle(items)
        sample.extend(items[:PER_BAND])
    print(f"sampled {len(sample)} bugs across bands: " + ", ".join(f"{b}:{min(len(v),PER_BAND)}" for b, v in byband.items()))

    # cache tests + first-fail per bug
    def prep(item):
        t, i, code, d = item
        tdir = resolve(t)
        if not tdir:
            return None
        names = names_of(tdir)
        ff = first_fail(code, tdir, names)
        if not ff:
            return None
        prob = (DATA / t / "problem.txt")
        return {"t": t, "i": i, "code": code, "d": d, "tdir": str(tdir), "names": names,
                "fail": ff, "problem": prob.read_text(errors="replace") if prob.exists() else ""}
    with ThreadPoolExecutor(max_workers=8) as ex:
        prepped = [x for x in ex.map(prep, sample) if x]
    print(f"prepped {len(prepped)} repairable bugs")

    results = {}
    for model in REPAIRERS:
        def fix_and_check(b):
            patched = repair(client, model, b["problem"], b["code"], b["fail"])
            if not patched:
                return (b, False)
            return (b, passes_all(patched, Path(b["tdir"]), b["names"]))
        with ThreadPoolExecutor(max_workers=8) as ex:
            outs = list(ex.map(fix_and_check, prepped))
        ok = sum(1 for _, p in outs if p)
        byb = collections.Counter(); okb = collections.Counter()
        bys = collections.Counter(); oks = collections.Counter()
        for b, p in outs:
            bb = band(b["d"]); byb[bb] += 1; okb[bb] += p
            s = sub.get((b["t"], b["i"]))
            if s:
                bys[s] += 1; oks[s] += p
        results[model] = {
            "n": len(outs), "repaired": ok, "rate": round(ok / len(outs), 3),
            "by_difficulty": {k: f"{okb[k]}/{byb[k]}" for k in byb},
            "by_subtype": {k: f"{oks[k]}/{bys[k]}" for k in sorted(bys)},
        }
        print(f"{model}: {ok}/{len(outs)} = {results[model]['rate']}")

    (RESULTS / "p3_apr.json").write_text(json.dumps(results, ensure_ascii=False, indent=2))
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
