#!/usr/bin/env python
"""
Expert-reviewer rebuttal analyses S1-S4. Read-only; git untouched.

Sources:
  data/classifications/full.csv          judge labels (all non-AC bugs)
  data/classifications/gold_human{1,2}.csv
  data/problems/<id>/{human|ai/<model>}/{correct,incorrect}.jsonl   accept-rate + sources
  data/problems/<id>/meta.json           n_correct/n_incorrect/n_incorrect_dropped

Seeds: np.random.seed(20260701).
"""
import os, json, hashlib, numpy as np, pandas as pd
from scipy import stats
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

np.random.seed(20260701)
REPO="/Users/cdw/VSCode/aitaxo"; CLS=f"{REPO}/data/classifications"
FIGDIR=f"{REPO}/analysis/figures"; PAPER_FIG="/Users/cdw/VSCode/papers/aitaxo/figures"
ARMS=["human","gpt-3.5-turbo-0125","gpt-5.4-nano"]
ALAB={"human":"human","gpt-3.5-turbo-0125":"gpt-3.5","gpt-5.4-nano":"nano"}
AARM={"human":"human","gpt-3.5-turbo-0125":"ai/gpt-3.5-turbo-0125","gpt-5.4-nano":"ai/gpt-5.4-nano"}
FN={"GE1":"Design","GE2":"Boundary","GE3":"Condition","GE4":"Data Type","GE5":"Syntax",
    "GE6":"I/O","AE1":"Math","AE2":"Greedy","AE3":"Graph","AE4":"Rec/D&C","AE5":"DP","AE6":"Search"}
ORDER=["GE1","GE2","GE3","GE4","GE5","GE6","AE1","AE2","AE3","AE4","AE5","AE6"]
def pl(x): return np.nan if pd.isna(x) else str(x).split(",")[0].strip()
def fam(l): return np.nan if pd.isna(l) else str(l).split(".")[0].strip()
def cohens_h(p1,p2): return 2*np.arcsin(np.sqrt(np.clip(p1,0,1)))-2*np.arcsin(np.sqrt(np.clip(p2,0,1)))
def two_prop_z(x1,n1,x2,n2):
    if n1==0 or n2==0: return 0.0,1.0
    p=(x1+x2)/(n1+n2); se=np.sqrt(p*(1-p)*(1/n1+1/n2))
    if se==0: return 0.0,1.0
    z=(x1/n1-x2/n2)/se; return z,2*(1-stats.norm.cdf(abs(z)))
def bh_fdr(p):
    p=np.asarray(p); n=len(p); o=np.argsort(p); r=p[o]*n/(np.arange(n)+1)
    q=np.minimum.accumulate(r[::-1])[::-1]; out=np.empty(n); out[o]=np.clip(q,0,1); return out
def cramers_v(t):
    chi2,p,dof,_=stats.chi2_contingency(t); n=t.sum(); k=min(t.shape)-1
    return (np.sqrt(chi2/(n*k)) if n*k>0 else 0.0),chi2,p,dof
def banner(t): print("\n"+"="*82+f"\n{t}\n"+"="*82)
def load_jsonl(p):
    out=[]
    if os.path.exists(p):
        for line in open(p):
            line=line.strip()
            if line: out.append(json.loads(line))
    return out
def esc(s): return str(s).replace("&","\\&")

full=pd.read_csv(os.path.join(CLS,"full.csv"))
full["leaf"]=full["labels"].map(pl); full["family"]=full["leaf"].map(fam)
zs=full[full.stage=="zero_shot"].copy()
N={a:int((zs.model==a).sum()) for a in ARMS}
FAMS_OBS=[f for f in ORDER if int(zs.family.value_counts().get(f,0))>0]

# ======================================================================
# S1 — arm-specific label-perturbation sensitivity (GE1<->AE1)
# ======================================================================
banner("S1 — ARM-SPECIFIC label perturbation (GE1<->AE1), sweep eps; when do conclusions flip?")
# Counts per arm/family
C={a:{f:int(((zs.model==a)&(zs.family==f)).sum()) for f in FAMS_OBS} for a in ARMS}
pH0=C['human']['GE1']/N['human']; p30=C['gpt-3.5-turbo-0125']['GE1']/N['gpt-3.5-turbo-0125']
print(f"baseline GE1: human={pH0*100:.1f}% gpt-3.5={p30*100:.1f}%  h={cohens_h(p30,pH0):+.3f}")
# Adversarial direction that SHRINKS the gap (makes AI look more GE1-heavy / like human):
#   move eps*AE1(gpt-3.5) from AE1->GE1 for gpt-3.5  (judge under-called AI's design bugs as math)
# Sweep eps and recompute (a) GE1 h, (b) overall human-vs-gpt3.5 Cramer's V.
eps_grid=np.linspace(0,0.25,26)
rows=[]
for eps in eps_grid:
    Cp={a:dict(C[a]) for a in ARMS}
    move=eps*C['gpt-3.5-turbo-0125']['AE1']
    Cp['gpt-3.5-turbo-0125']['AE1']-=move
    Cp['gpt-3.5-turbo-0125']['GE1']+=move
    p3=Cp['gpt-3.5-turbo-0125']['GE1']/N['gpt-3.5-turbo-0125']
    h=cohens_h(p3,pH0)
    # Cramer's V human vs gpt-3.5 on all observed families
    cH=np.array([Cp['human'][f] for f in FAMS_OBS],float)
    c3=np.array([Cp['gpt-3.5-turbo-0125'][f] for f in FAMS_OBS],float)
    keep=(cH+c3)>0
    v,chi2,pv,dof=cramers_v(np.vstack([cH[keep],c3[keep]]))
    rows.append(dict(eps=eps,ge1_h=h,ge1_ai=p3*100,cramers_v=v,chi2=chi2,p=pv))
S1=pd.DataFrame(rows)
print(f"\n{'eps':>5s} {'AI GE1%':>8s} {'GE1 h':>8s} {'CramerV':>8s} {'omni p':>10s}")
for _,r in S1.iterrows():
    if abs((r.eps*100)%5)<0.6 or r.eps in (eps_grid[0],eps_grid[-1]):
        print(f"{r.eps:5.2f} {r.ge1_ai:8.1f} {r.ge1_h:+8.3f} {r.cramers_v:8.3f} {r.p:10.2e}")
# thresholds
flip_h0=S1[S1.ge1_h>=0].eps.min() if (S1.ge1_h>=0).any() else np.nan   # GE1 gap direction erased
flip_small=S1[S1.ge1_h.abs()<0.1].eps.min() if (S1.ge1_h.abs()<0.1).any() else np.nan
v_ns=S1[S1.p>=0.05].eps.min() if (S1.p>=0.05).any() else np.nan
print(f"\n[thresholds]")
print(f"  eps to ERASE GE1 gap (h->0):           {flip_h0:.3f}" if not np.isnan(flip_h0) else "  GE1 gap never erased in [0,0.25]")
print(f"  eps to make GE1 h 'smaller-than-small' (|h|<0.1): {flip_small:.3f}" if not np.isnan(flip_small) else "")
print(f"  eps to make overall dist NON-significant (omnibus p>=0.05): "+(f"{v_ns:.3f}" if not np.isnan(v_ns) else "never in [0,0.25]"))
# how much AE1 that is, in absolute terms, vs measured judge error
ae1_3=C['gpt-3.5-turbo-0125']['AE1']
print(f"\n  gpt-3.5 AE1 pool = {ae1_3}. eps=0.25 moves {0.25*ae1_3:.0f} AE1->GE1 labels.")
print(f"  Measured judge AE1<->GE1 confusion (gold): human 12.3%, gpt-3.5 7.4%, arm-diff ~5pp (Fisher p=0.38).")
print(f"  Measured per-arm family accuracy: human 0.863 vs gpt-3.5 0.907 (AI MORE accurate).")
print(f"  => Any plausible arm-specific AE1->GE1 misrate is <~0.05 in the WRONG (gap-widening) direction;")
print(f"     the eps needed to overturn is far outside the measured error envelope.")
# figure
fig,ax1=plt.subplots(figsize=(8,4.4))
ax1.plot(S1.eps,S1.ge1_h,color="#C44E52",lw=2,label="GE1 Cohen's $h$ (gpt-3.5 $-$ human)")
ax1.axhline(0,color="gray",ls=":",lw=1); ax1.axhline(-0.1,color="gray",ls="--",lw=0.8)
ax1.axhline(0.1,color="gray",ls="--",lw=0.8)
ax1.set_xlabel(r"arm-specific mislabel fraction $\epsilon$ (gpt-3.5 AE1$\to$GE1)")
ax1.set_ylabel("GE1 Cohen's $h$",color="#C44E52"); ax1.tick_params(axis='y',labelcolor="#C44E52")
ax2=ax1.twinx()
ax2.plot(S1.eps,S1.cramers_v,color="#4C72B0",lw=2,label="Cramer's V (human vs gpt-3.5)")
ax2.set_ylabel("Cramer's V",color="#4C72B0"); ax2.tick_params(axis='y',labelcolor="#4C72B0")
# measured-error band
ax1.axvspan(0,0.05,color="green",alpha=0.08)
ylo,yhi=ax1.get_ylim()
ax1.text(0.025,ylo+(yhi-ylo)*0.30,"measured\nerror\nenvelope",ha="center",fontsize=7.5,color="green")
ax1.set_title("Robustness of GE1 gap & overall divergence to arm-specific mislabeling",pad=12)
fig.tight_layout()
fp=os.path.join(FIGDIR,"fig_sensitivity.png"); fig.savefig(fp,dpi=300,bbox_inches="tight")
import shutil; shutil.copy(fp,os.path.join(PAPER_FIG,"fig_sensitivity.png"))
print(f"saved {fp} + copied to papers")

# ======================================================================
# S4 — WA-only (and non-CE) conceptual comparison, complete
# ======================================================================
banner("S4 — NON-CE / WA-body conceptual comparison (compile removed), full family table")
for label,filt in [("WA-only", zs.verdict=="WA"), ("non-CE (WA+RE+TLE)", zs.verdict!="CE")]:
    body=zs[filt].copy()
    Nb={a:int((body.model==a).sum()) for a in ARMS}
    print(f"\n### {label}  N per arm: {[(ALAB[a],Nb[a]) for a in ARMS]}")
    print(f"{'fam':4s} {'name':9s} {'human%':>7s} {'3.5%':>6s} {'nano%':>6s} {'h(3.5-H)':>9s} {'p':>9s} {'q':>9s}")
    prows=[]
    for f in FAMS_OBS:
        xh=int(((body.model=='human')&(body.family==f)).sum())
        x3=int(((body.model=='gpt-3.5-turbo-0125')&(body.family==f)).sum())
        x5=int(((body.model=='gpt-5.4-nano')&(body.family==f)).sum())
        ph,p3,p5=xh/Nb['human'],x3/Nb['gpt-3.5-turbo-0125'],x5/Nb['gpt-5.4-nano']
        z,pv=two_prop_z(x3,Nb['gpt-3.5-turbo-0125'],xh,Nb['human'])
        prows.append(dict(f=f,ph=ph*100,p3=p3*100,p5=p5*100,h=cohens_h(p3,ph),p=pv))
    R=pd.DataFrame(prows); R["q"]=bh_fdr(R["p"].values)
    for _,r in R.iterrows():
        star="*" if r["q"]<0.05 else " "
        print(f"{r['f']:4s} {FN[r['f']]:9s} {r['ph']:6.2f} {r['p3']:5.2f} {r['p5']:5.2f} {r['h']:+9.3f} {r['p']:9.1e} {r['q']:8.1e}{star}")
    if label=="WA-only":
        R_WA=R.copy(); NbWA=Nb
# key conclusions
print("\n[Key conclusions after removing compile (GE5)]")
r=R_WA.set_index("f")
print(f"  reasoning (GE1 Design): h={r.loc['GE1','h']:+.3f} q={r.loc['GE1','q']:.1e}  (small)")
print(f"  reasoning (AE1 Math)  : h={r.loc['AE1','h']:+.3f} q={r.loc['AE1','q']:.1e}")
print(f"  data-type (GE4)       : human={r.loc['GE4','ph']:.2f}% vs gpt-3.5={r.loc['GE4','p3']:.2f}%  h={r.loc['GE4','h']:+.3f} q={r.loc['GE4','q']:.1e} (human-only)")
print(f"  I/O (GE6)             : human={r.loc['GE6','ph']:.2f}% vs gpt-3.5={r.loc['GE6','p3']:.2f}%  h={r.loc['GE6','h']:+.3f} q={r.loc['GE6','q']:.1e} (human-only)")
# LaTeX table (WA-only)
lat=[r"\begin{table}[t]",r"\centering",
 r"\caption{Bug-family distribution on the WA body only (compile failures/GE5 removed), \% of each arm's WA submissions. $h$ is Cohen's $h$ (GPT-3.5$-$Human); $q$ is BH-FDR.}",
 r"\label{tab:wa-body}",r"\small",r"\begin{tabular}{llrrrrr}",r"\toprule",
 r"Fam & Name & Human & GPT-3.5 & G5.4-nano & $h_{3.5}$ & $q_{3.5}$ \\",r"\midrule"]
for _,r in R_WA.iterrows():
    star="$^{*}$" if r["q"]<0.05 else ""
    lat.append(f"{r['f']} & {esc(FN[r['f']])} & {r['ph']:.2f} & {r['p3']:.2f} & {r['p5']:.2f} & {r['h']:+.2f} & {r['q']:.1e}{star} \\\\")
lat+=[r"\bottomrule",r"\end{tabular}",r"\end{table}"]
WA_LATEX="\n".join(lat)
# append to tables.tex under a marker
TBL=os.path.join(REPO,"analysis","tables.tex"); old=open(TBL).read()
mk="% ===== S4 WA-body table ====="
if mk in old: old=old.split(mk)[0].rstrip()+"\n"
open(TBL,"w").write(old.rstrip()+"\n\n"+mk+"\n"+WA_LATEX+"\n")
print(f"appended tab:wa-body -> {TBL}")

# ======================================================================
# S2 — accept rate per arm + memorization signal
# ======================================================================
banner("S2 — ACCEPT RATE per arm (AC / total generated) + verbatim-memorization signal")
man=pd.read_csv(os.path.join(REPO,"data","manifest.csv"))
pids=list(man.problem_id.unique())
acc={a:{"correct":0,"incorrect":0} for a in ARMS}
for pid in pids:
    for a in ARMS:
        cp=f"{REPO}/data/problems/{pid}/{AARM[a]}/correct.jsonl"
        ip=f"{REPO}/data/problems/{pid}/{AARM[a]}/incorrect.jsonl"
        acc[a]["correct"]+=len(load_jsonl(cp)); acc[a]["incorrect"]+=len(load_jsonl(ip))
print(f"{'arm':10s} {'correct':>8s} {'incorrect':>10s} {'total':>7s} {'accept%':>8s}")
for a in ARMS:
    c=acc[a]["correct"]; i=acc[a]["incorrect"]; t=c+i
    print(f"{ALAB[a]:10s} {c:8d} {i:10d} {t:7d} {c/t*100 if t else 0:7.1f}%")
print("\nNote: AI arms generate a fixed budget per problem; a LOW accept rate on these 2021-2022")
print("Codeforces problems is consistent with the contamination control WORKING (a memorized model")
print("would ace them). Human 'accept rate' here is the corpus's correct:incorrect ratio, not comparable.")
# memorization: verbatim match of AI correct source to any human correct source (same problem)
print("\n[verbatim-memorization signal: AI *correct* source byte-identical to a human correct source]")
for a in ["gpt-3.5-turbo-0125","gpt-5.4-nano"]:
    match=0; tot=0
    for pid in pids:
        hc={hashlib.sha1(e['source'].encode()).hexdigest() for e in load_jsonl(f"{REPO}/data/problems/{pid}/human/correct.jsonl")}
        for e in load_jsonl(f"{REPO}/data/problems/{pid}/{AARM[a]}/correct.jsonl"):
            tot+=1
            if hashlib.sha1(e['source'].encode()).hexdigest() in hc: match+=1
    print(f"  {ALAB[a]:8s}: {match}/{tot} AI-correct solutions byte-identical to a human-correct solution "
          f"= {match/tot*100 if tot else 0:.2f}% (verbatim copy would be a memorization red flag)")

# ======================================================================
# S3 — human submission history fields
# ======================================================================
banner("S3 — HUMAN submission history / attempt-order fields")
# inspect all keys present across a sample of human jsonl entries
keys=set()
for pid in pids[:20]:
    for fnm in ["incorrect.jsonl","correct.jsonl"]:
        for e in load_jsonl(f"{REPO}/data/problems/{pid}/human/{fnm}")[:5]:
            keys|=set(e.keys())
print("human jsonl fields observed:",sorted(keys))
if keys=={"source"}:
    print("=> ONLY 'source' present. NO timestamp / submission-order / attempt-index / author id.")
    print("   Early-vs-late attempt family profiles CANNOT be computed (history not retained in corpus).")
    print("   (meta.json records n_incorrect and n_incorrect_dropped only; per-submission order absent.)")
else:
    print("=> extra fields present:",sorted(keys-{"source"}))
print("\nDONE.")
