"""Open-coding aid: for WA bugs, juxtapose problem + AI buggy code + human correct.py
so the analyst can diagnose *what the model misread* and derive Spec-Misinterpretation sub-types.

Stratified sample (favoring easy/mid where the misread is diagnosable).
Output: results/wa_opencoding.txt
"""
from __future__ import annotations
import json, collections
from pathlib import Path

DATA = Path("data")
man = {t["task_id"]: t["difficulty"] for t in json.loads((DATA / "window_manifest.json").read_text())["tasks"]}
gens = [json.loads(l) for l in open("results/fulltest_generations.jsonl")]
wa = [g for g in gens if g["status"] == "wrong_answer"]

# stratify by difficulty band, favor easy/mid (diagnosable)
def band(d):
    d = d or man.get("", 0) or 0
    return "easy" if d < 400 else "mid" if d < 1200 else "hard" if d < 2000 else "vhard"

buckets = collections.defaultdict(list)
for g in wa:
    buckets[band(man.get(g["task_id"]))].append(g)
# quota: more easy/mid
quota = {"easy": 14, "mid": 12, "hard": 6, "vhard": 4}
sample = []
for b, q in quota.items():
    sample.extend(buckets[b][:q])

def correct_of(task):
    hd = DATA / task / "human"
    if hd.is_dir():
        for sub in sorted(hd.iterdir()):
            c = sub / "correct.py"
            if c.exists():
                return c.read_text(errors="replace")
    return "(no correct.py)"

out = open("results/wa_opencoding.txt", "w")
for i, g in enumerate(sample, 1):
    t = g["task_id"]
    prob = (DATA / t / "problem.txt").read_text(errors="replace")
    out.write(f"\n{'='*72}\n#{i} {t} diff={man.get(t)} passed={g.get('n_passed')}/{g.get('n_tests')}\n")
    out.write(f"--- PROBLEM ---\n{prob[:650]}\n")
    out.write(f"--- AI (WA) ---\n{g['code'][:600]}\n")
    out.write(f"--- HUMAN correct.py ---\n{correct_of(t)[:500]}\n")
out.close()
print(f"WA open-coding 덤프: {len(sample)}개 (easy {min(quota['easy'],len(buckets['easy']))}, "
      f"mid {min(quota['mid'],len(buckets['mid']))}, hard {min(quota['hard'],len(buckets['hard']))}, "
      f"vhard {min(quota['vhard'],len(buckets['vhard']))}) → results/wa_opencoding.txt")
print(f"전체 WA(gen1-5): {len(wa)}")
