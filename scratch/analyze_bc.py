import json
from collections import Counter
from scipy.stats import fisher_exact

gold = {g["submission_id"]: g for g in (json.loads(l) for l in open("human/gold_labels.jsonl") if l.strip())}

def load(path):
    return {json.loads(l)["submission_id"]: json.loads(l) for l in open(path) if l.strip()}

def prf(recs, view="primary"):
    tp=fp=fn=ex=ap=0
    for r in recs:
        G=set(r["gold"]); P={r["primary"]} if (view=="primary" and r["primary"]) else set(r["leaves"])
        tp+=len(P&G);fp+=len(P-G);fn+=len(G-P);ex+=int(P==G);ap+=len(P)
    n=len(recs); pr=tp/(tp+fp) if tp+fp else 0; rc=tp/(tp+fn) if tp+fn else 0
    f1=2*pr*rc/(pr+rc) if pr+rc else 0
    return f"P {pr:.3f}  R {rc:.3f}  F1 {f1:.3f}  exact {ex/n:.3f}  avgN {ap/n:.2f}  (n={n})"

base=list(load("artifacts/judge_ablation/gpt-5-5_low.jsonl").values())   # revised, pre-tune
tuned=load("artifacts/judge_ablation/g5_tuned_low.jsonl")
print("=== (b) tuned vs pre-tune (gpt-5.5 low, 346) ===")
print("  pre-tune  primary:", prf(base))
print("  TUNED     primary:", prf(list(tuned.values())))
def famrecs(recs):
    return [{"gold":[x.split('.')[0] for x in r["gold"]],"primary":r["primary"].split('.')[0] if r["primary"] else None,"leaves":[x.split('.')[0] for x in r["leaves"]]} for r in recs]
print("  TUNED     family :", prf(famrecs(list(tuned.values()))))

# bias before/after
def bias(recs_map, g, jl):
    n=hit=0
    for r in recs_map.values() if isinstance(recs_map,dict) else recs_map:
        G=gold[r["submission_id"]]["gold_leaves"] if "submission_id" in r else None
    return None
def rate(recs, gl, jl):
    sub=[r for r in recs if len(r["gold"])==1 and r["gold"][0]==gl and r["primary"]]
    h=sum(1 for r in sub if r["primary"]==jl)
    return h, len(sub)
print("\n  bias change (gold->judge):")
for gl,jl in [("GE1.1","AE1.1"),("GE1.1","GE1.2")]:
    hb,nb=rate(base,gl,jl); ht,nt=rate(list(tuned.values()),gl,jl)
    print(f"    {gl}->{jl}: pre {hb}/{nb}={hb/nb:.2f}  ->  tuned {ht}/{nt}={ht/nt if nt else 0:.2f}")

# (0) re-check on tuned: per-arm + 2 confusion matrices
print("\n=== arm-split on TUNED (the 2 confusion matrices) ===")
items=[(gold[r["submission_id"]]["arm"], r["gold"][0], r["primary"]) for r in tuned.values() if len(r["gold"])==1 and r["primary"]]
for arm in ["human","ai_zero_shot"]:
    sub=[(g,p) for a,g,p in items if a==arm]
    acc=sum(1 for g,p in sub if g==p)/len(sub)
    conf=Counter((g,p) for g,p in sub if g!=p).most_common(6)
    print(f"  [{arm}] acc {acc:.3f} n={len(sub)} | top conf: "+", ".join(f"{g}->{p}:{n}" for (g,p),n in conf))
for gl,jl in [("GE1.1","AE1.1"),("GE1.1","GE1.2")]:
    tab=[]
    for arm in ["ai_zero_shot","human"]:
        sub=[p for a,g,p in items if a==arm and g==gl]; h=sum(1 for p in sub if p==jl)
        tab.append((h,len(sub)-h))
    if all(sum(t) for t in tab):
        _,pv=fisher_exact(tab); print(f"  {gl}->{jl} arm-diff Fisher p={pv:.3f} {'DIFFERENTIAL' if pv<0.05 else 'ok'}")

# (c) medium on 100
import os
if os.path.exists("artifacts/judge_ablation/g5_tuned_med100.jsonl"):
    med=load("artifacts/judge_ablation/g5_tuned_med100.jsonl")
    ids=set(med); low100=[tuned[i] for i in ids if i in tuned]
    print("\n=== (c) medium vs low on same 100 (tuned prompt) ===")
    print("  low    :", prf(low100))
    print("  MEDIUM :", prf(list(med.values())))
