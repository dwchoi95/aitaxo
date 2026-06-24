"""C-stage: per-problem systematicity + 10/task taxonomy.

Merge gen1-5 (fulltest_generations.jsonl) + gen6-10 (gen2_generations.jsonl) -> 10/task.
For each problem: do its failing generations converge on the same coarse failure mode?
  - modal-share = (count of bugs in the most common status) / n_bugs
  - normalized entropy of the bug-status distribution (0 = perfectly systematic)
Plus overall 10/task status distribution and difficulty gradient.

Output: results/consistency.json, results/tenpertask_taxonomy.json
"""
from __future__ import annotations
import json, collections, math
from pathlib import Path

DATA = Path("data")
man = {t["task_id"]: t["difficulty"] for t in json.loads((DATA / "window_manifest.json").read_text())["tasks"]}

recs = {}
for fn in ("results/fulltest_generations.jsonl", "results/gen2_generations.jsonl"):
    for l in open(fn):
        g = json.loads(l)
        recs[(g["task_id"], g["sample_idx"])] = g["status"]   # dedup by (task, idx)

by_task = collections.defaultdict(dict)
for (task, idx), st in recs.items():
    by_task[task][idx] = st

# overall
allst = collections.Counter(recs.values())
N = len(recs)

# per-problem systematicity (over BUG generations)
modal_shares, entropies, full_consistent = [], [], 0
per = []
for task, idxs in by_task.items():
    sts = list(idxs.values())
    bugs = [s for s in sts if s != "pass"]
    if len(bugs) < 2:
        continue
    c = collections.Counter(bugs)
    modal = c.most_common(1)[0][1]
    share = modal / len(bugs)
    H = -sum((n/len(bugs)) * math.log2(n/len(bugs)) for n in c.values())
    Hn = H / math.log2(len(c)) if len(c) > 1 else 0.0
    modal_shares.append(share); entropies.append(Hn)
    if len(c) == 1:
        full_consistent += 1
    per.append({"task": task, "n_gen": len(sts), "n_bugs": len(bugs),
                "modal_status": c.most_common(1)[0][0], "modal_share": round(share, 3),
                "n_distinct_status": len(c)})

def band(d):
    d = d or 0
    return "easy" if d < 400 else "mid" if d < 1200 else "hard" if d < 2000 else "vhard"
bd = collections.defaultdict(lambda: [0, 0])
for (task, idx), st in recs.items():
    b = band(man.get(task)); bd[b][0] += 1; bd[b][1] += (st == "pass")

out = {
    "n_generations": N, "n_tasks": len(by_task),
    "status": dict(allst), "pass_rate": round(allst["pass"] / N, 3),
    "systematicity": {
        "problems_scored": len(modal_shares),
        "avg_modal_share": round(sum(modal_shares) / len(modal_shares), 3),
        "avg_norm_entropy": round(sum(entropies) / len(entropies), 3),
        "pct_fully_consistent": round(100 * full_consistent / len(modal_shares), 1),
        "modal_share_hist": dict(collections.Counter(round(s, 1) for s in modal_shares)),
    },
    "difficulty_pass": {b: {"n": bd[b][0], "pass": bd[b][1], "rate": round(bd[b][1]/bd[b][0], 3)}
                        for b in ["easy", "mid", "hard", "vhard"] if bd[b][0]},
}
Path("results/consistency.json").write_text(json.dumps(out, ensure_ascii=False, indent=2))
print(json.dumps(out, ensure_ascii=False, indent=2))
print(f"\n버그 = {N - allst['pass']} | 저장: results/consistency.json")
