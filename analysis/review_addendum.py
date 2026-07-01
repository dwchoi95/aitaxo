#!/usr/bin/env python
"""
Review-addendum analyses (A-I) for the aitaxo paper.

Inputs (read-only):
  data/classifications/full.csv         judge labels, all non-AC bugs, all arms/stages
  data/classifications/gold_human1.csv  annotator 1 (375 items, 125/arm, zero_shot)
  data/classifications/gold_human2.csv  annotator 2 (same 375 items)
  data/manifest.csv                     problem metadata (cf_rating, cf_tags)

Conventions (identical to expr2.ipynb):
  primary label = first comma-separated label; family = prefix before '.'
  arms = human, gpt-3.5-turbo-0125, gpt-5.4-nano ; zero_shot stage is the headline.
  gold "consensus/adjudicated" primary family = subset where the two annotators'
  primary family agrees (same definition the notebook uses for judge scoring).

Seeds: np.random.seed(20260701) for all bootstraps (B=5000 unless noted).
Outputs: prints tables to stdout; (F) writes analysis/figures/fig_family_by_difficulty.png
and copies to papers; (I) appends an h-CI column to the RQ1 table in analysis/tables.tex.
"""
import os, numpy as np, pandas as pd
from scipy import stats
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter

np.random.seed(20260701)
B = 5000
REPO = "/Users/cdw/VSCode/aitaxo"
CLS  = os.path.join(REPO, "data", "classifications")
FIGDIR = os.path.join(REPO, "analysis", "figures")
PAPER_FIG = "/Users/cdw/VSCode/papers/aitaxo/figures"

FAMILY_NAMES = {"GE1":"Design","GE2":"Boundary","GE3":"Condition","GE4":"Data Type",
                "GE5":"Syntax","GE6":"I/O","AE1":"Math","AE2":"Greedy","AE3":"Graph",
                "AE4":"Rec/D&C","AE5":"DP","AE6":"Search"}
FAMILY_ORDER = ["GE1","GE2","GE3","GE4","GE5","GE6","AE1","AE2","AE3","AE4","AE5","AE6"]
ARMS = ["human","gpt-3.5-turbo-0125","gpt-5.4-nano"]
ALAB = {"human":"human","gpt-3.5-turbo-0125":"gpt-3.5","gpt-5.4-nano":"gpt-5.4-nano"}
EDGES=[-np.inf,1400,1900,2400,np.inf]; BINS=["easy","medium","hard","expert"]

def primary_leaf(x):
    return np.nan if pd.isna(x) else str(x).split(",")[0].strip()
def fam_of(l):
    return np.nan if pd.isna(l) else str(l).split(".")[0].strip()
def cohens_h(p1,p2):
    return 2*np.arcsin(np.sqrt(p1))-2*np.arcsin(np.sqrt(p2))
def two_prop_z(x1,n1,x2,n2):
    p1,p2=x1/n1,x2/n2; p=(x1+x2)/(n1+n2)
    se=np.sqrt(p*(1-p)*(1/n1+1/n2))
    if se==0: return 0.0,1.0
    z=(p1-p2)/se; return z,2*(1-stats.norm.cdf(abs(z)))
def h_ci(xA,nA,xH,nH):
    """Cohen's h (AI - human) with Wald 95% CI via the arcsin-variance.
    phi=2*arcsin(sqrt(p)) has Var ~ 1/n; h=phiA-phiH, Var(h)=1/nA+1/nH."""
    pA,pH=xA/nA,xH/nH
    h=cohens_h(pA,pH); se=np.sqrt(1.0/nA+1.0/nH)
    return h, h-1.96*se, h+1.96*se
def boot_h_ci(xA,nA,xH,nH,B=B):
    pA,pH=xA/nA,xH/nH
    sA=np.random.binomial(nA,pA,B)/nA; sH=np.random.binomial(nH,pH,B)/nH
    hs=cohens_h(sA,sH)
    return np.percentile(hs,2.5),np.percentile(hs,97.5)
def cramers_v(table):
    chi2,p,dof,_=stats.chi2_contingency(table)
    n=table.sum(); k=min(table.shape)-1
    v=np.sqrt(chi2/(n*k)) if n*k>0 else 0.0
    return chi2,p,dof,v

# ---------- load ----------
full=pd.read_csv(os.path.join(CLS,"full.csv"))
full["leaf"]=full["labels"].map(primary_leaf); full["family"]=full["leaf"].map(fam_of)
manifest=pd.read_csv(os.path.join(REPO,"data","manifest.csv"))
manifest["maintag"]=manifest["cf_tags"].fillna("").map(lambda s:s.split("|")[0].strip() if s else "none")
pid2tags={p:(str(t) if pd.notna(t) else "") for p,t in zip(manifest["problem_id"],manifest["cf_tags"])}
full["difficulty"]=pd.cut(full["cf_rating"],bins=EDGES,labels=BINS)
zs=full[full["stage"]=="zero_shot"].copy()
N={a:int((zs.model==a).sum()) for a in ARMS}

g1=pd.read_csv(os.path.join(CLS,"gold_human1.csv")); g2=pd.read_csv(os.path.join(CLS,"gold_human2.csv"))
for g in (g1,g2):
    g["leaf"]=g["labels"].map(primary_leaf); g["fam"]=g["leaf"].map(fam_of)
g1i=g1.set_index("item_id"); g2i=g2.set_index("item_id")
common=[i for i in g1i.index if i in g2i.index]
jmap=full.set_index("item_id")[["model","problem_id","leaf","family","verdict"]]
# arm for each gold item
gold=pd.DataFrame({"item_id":common})
gold["arm"]=gold["item_id"].map(lambda i:jmap.loc[i,"model"])
gold["fam1"]=gold["item_id"].map(lambda i:g1i.loc[i,"fam"])
gold["fam2"]=gold["item_id"].map(lambda i:g2i.loc[i,"fam"])
gold["judge_fam"]=gold["item_id"].map(lambda i:jmap.loc[i,"family"])
gold["agree"]=gold["fam1"]==gold["fam2"]
# adjudicated/consensus primary family = agreed family (only on agreement subset)
gold["cons_fam"]=np.where(gold["agree"],gold["fam1"],np.nan)

def banner(t): print("\n"+"="*78+f"\n{t}\n"+"="*78)

# =========================================================================
# A) GOLD-ONLY HEADLINE (judge-independent)
# =========================================================================
banner("A) GOLD-ONLY HEADLINE — adjudicated (consensus) primary family, per arm")
gc=gold[gold["agree"]].copy()  # agreement subset = adjudicated gold
print(f"gold items total={len(gold)} | family-agreement (adjudicated) subset={len(gc)} "
      f"({len(gc)/len(gold)*100:.1f}%)")
print("per-arm adjudicated N:", {ALAB[a]:int((gc.arm==a).sum()) for a in ARMS})
print("\n[Gold adjudicated family % per arm]  (denominator = adjudicated items in that arm)")
rows=[]
golfam={}
for a in ARMS:
    sub=gc[gc.arm==a]; n=len(sub)
    cnt=sub["cons_fam"].value_counts()
    golfam[a]=(cnt,n)
hdr=f"{'fam':4s} {'name':10s} "+" ".join(f"{ALAB[a]:>13s}" for a in ARMS)
print(hdr)
for f in FAMILY_ORDER:
    line=f"{f:4s} {FAMILY_NAMES[f]:10s} "
    any_=False
    for a in ARMS:
        cnt,n=golfam[a]; c=int(cnt.get(f,0))
        if c>0: any_=True
        line+=f"  {c/n*100:5.1f}%({c:2d})"
    if any_: print(line)
# GE1 / GE5 headline + Cohen's h human vs gpt-3.5 with 95% CI
print("\n[Gold-only GE1 & GE5: human vs gpt-3.5, Cohen's h + 95% CI]")
for f in ["GE1","GE5"]:
    cH,nH=golfam["human"][0].get(f,0),golfam["human"][1]
    cA,nA=golfam["gpt-3.5-turbo-0125"][0].get(f,0),golfam["gpt-3.5-turbo-0125"][1]
    pH,pA=cH/nH,cA/nA
    h,lo,hi=h_ci(cA,nA,cH,nH)
    blo,bhi=boot_h_ci(cA,nA,cH,nH)
    z,pv=two_prop_z(cA,nA,cH,nH)
    print(f"  {f} {FAMILY_NAMES[f]:8s}: human={pH*100:5.1f}% ({cH}/{nH})  gpt-3.5={pA*100:5.1f}% ({cA}/{nA})  "
          f"h={h:+.3f} [Wald {lo:+.3f},{hi:+.3f}] [boot {blo:+.3f},{bhi:+.3f}]  2-prop p={pv:.2e}")
# also nano
print("\n[Gold-only, nano vs human for reference]")
for f in ["GE1","GE5"]:
    cH,nH=golfam["human"][0].get(f,0),golfam["human"][1]
    cV,nV=golfam["gpt-5.4-nano"][0].get(f,0),golfam["gpt-5.4-nano"][1]
    h,lo,hi=h_ci(cV,nV,cH,nH)
    print(f"  {f}: nano={cV/nV*100:5.1f}% ({cV}/{nV})  h(nano-human)={h:+.3f} [{lo:+.3f},{hi:+.3f}]")

# =========================================================================
# B) MEASUREMENT-ERROR CORRECTION (judge -> gold confusion, per arm)
# =========================================================================
banner("B) MEASUREMENT-ERROR CORRECTION — per-arm judge->gold confusion, deconvolved family rates")
# Build per-arm confusion C[g, j] = P(judge=j | gold=g) estimated on adjudicated gold.
# Then observed full-corpus judge vector o = C^T @ t  (t = true family dist) approx;
# we solve for t by constrained least squares (non-neg, sum=1).  Bootstrap over gold
# items (per arm) AND full-corpus multinomial to get CI on corrected h.
FAMS_OBS=[f for f in FAMILY_ORDER if int(zs["family"].value_counts().get(f,0))>0]
def confusion(arm, g1i, g2i, idxs):
    """rows=gold family (adjudicated), cols=judge family; counts."""
    M=pd.DataFrame(0.0,index=FAMS_OBS,columns=FAMS_OBS)
    for i in idxs:
        gf=g1i.loc[i,"fam"]  # adjudicated == agreed; g1==g2 here
        jf=jmap.loc[i,"family"]
        if gf in M.index and jf in M.columns:
            M.loc[gf,jf]+=1
    return M
def deconvolve(obs_vec, Crowstoch):
    """obs_vec (judge dist), Crowstoch rows=gold, cols=judge row-stochastic.
    solve obs = C^T t for t>=0, sum t=1 via NNLS then renormalize."""
    A=Crowstoch.values.T  # cols of A index gold; A @ t = obs
    from scipy.optimize import nnls
    t,_=nnls(A,obs_vec)
    s=t.sum()
    return t/s if s>0 else t
# observed judge family dist per arm (full corpus zero_shot)
obs={a: (zs[zs.model==a]["family"].value_counts().reindex(FAMS_OBS).fillna(0)/N[a]).values for a in ARMS}
corr_point={}
for a in ARMS:
    idxs=[i for i in common if jmap.loc[i,"model"]==a and g1i.loc[i,"fam"]==g2i.loc[i,"fam"]]
    M=confusion(a,g1i,g2i,idxs)
    Crow=M.div(M.sum(axis=1).replace(0,np.nan),axis=0)  # row-stochastic P(judge|gold)
    # gold families with 0 observations: assume identity (no info) -> set diagonal 1
    for f in FAMS_OBS:
        if M.loc[f].sum()==0: Crow.loc[f]=0; Crow.loc[f,f]=1.0
    Crow=Crow.fillna(0)
    t=deconvolve(obs[a],Crow)
    corr_point[a]=pd.Series(t,index=FAMS_OBS)
print("[Corrected (deconvolved) family % per arm]  vs observed judge %")
print(f"{'fam':4s} {'name':9s}"+"".join(f"  {ALAB[a]+'(obs/corr)':>22s}" for a in ARMS))
for f in ["GE1","GE5","GE2","AE1"]:
    line=f"{f:4s} {FAMILY_NAMES[f]:9s}"
    for a in ARMS:
        o=obs[a][FAMS_OBS.index(f)]*100; c=corr_point[a][f]*100
        line+=f"   {o:5.1f}/{c:5.1f}%        "
    print(line)
# corrected Cohen's h (gpt-3.5 vs human) with bootstrap CI
def corrected_h(f, B=2000):
    out=[]
    arm_idx={a:[i for i in common if jmap.loc[i,"model"]==a and g1i.loc[i,"fam"]==g2i.loc[i,"fam"]] for a in ["human","gpt-3.5-turbo-0125"]}
    for b in range(B):
        ts={}
        for a in ["human","gpt-3.5-turbo-0125"]:
            # resample gold items (confusion) and full-corpus (obs)
            gi=np.random.choice(arm_idx[a],len(arm_idx[a]),replace=True)
            M=confusion(a,g1i,g2i,list(gi))
            Crow=M.div(M.sum(axis=1).replace(0,np.nan),axis=0)
            for ff in FAMS_OBS:
                if M.loc[ff].sum()==0: Crow.loc[ff]=0; Crow.loc[ff,ff]=1.0
            Crow=Crow.fillna(0)
            # resample observed counts
            cnts=(zs[zs.model==a]["family"].value_counts().reindex(FAMS_OBS).fillna(0)).values
            ob=np.random.multinomial(int(cnts.sum()),cnts/cnts.sum())/cnts.sum()
            ts[a]=deconvolve(ob,Crow)
        i=FAMS_OBS.index(f)
        out.append(cohens_h(ts["gpt-3.5-turbo-0125"][i],ts["human"][i]))
    out=np.array(out)
    # point estimate from corr_point
    pe=cohens_h(corr_point["gpt-3.5-turbo-0125"][f],corr_point["human"][f])
    return pe,np.percentile(out,2.5),np.percentile(out,97.5)
print("\n[Corrected Cohen's h (gpt-3.5 - human), bootstrap 95% CI, B=2000]")
for f in ["GE1","GE5"]:
    # raw (judge) h for comparison
    cH=int(zs[(zs.model=='human')&(zs.family==f)].shape[0]); cA=int(zs[(zs.model=='gpt-3.5-turbo-0125')&(zs.family==f)].shape[0])
    hraw,_,_=h_ci(cA,N['gpt-3.5-turbo-0125'],cH,N['human'])
    pe,lo,hi=corrected_h(f)
    print(f"  {f} {FAMILY_NAMES[f]:8s}: raw h={hraw:+.3f}   corrected h={pe:+.3f} [{lo:+.3f}, {hi:+.3f}]")

# =========================================================================
# C) MACRO vs MICRO rate
# =========================================================================
banner("C) MACRO (problem-averaged) vs MICRO (submission-pooled) family rate per arm")
def micro(f,a):
    s=zs[zs.model==a]; return (s.family==f).mean()
def macro(f,a):
    s=zs[zs.model==a].copy(); s["is_f"]=(s.family==f).astype(int)
    per=s.groupby("problem_id")["is_f"].mean()
    return per.mean(), per.std(), len(per)
for f in ["GE1","GE5","AE1","GE2"]:
    print(f"\n[{f} {FAMILY_NAMES[f]}]")
    for a in ARMS:
        mi=micro(f,a)*100; ma,sd,npr=macro(f,a);
        print(f"  {ALAB[a]:14s}: micro={mi:5.1f}%   macro={ma*100:5.1f}% (sd {sd*100:4.1f}, {npr} problems)")
    # macro h human vs gpt-3.5
    maH,_,_=macro(f,"human"); maA,_,_=macro(f,"gpt-3.5-turbo-0125")
    print(f"  -> macro Cohen's h (gpt-3.5 - human) = {cohens_h(maA,maH):+.3f}  (micro h = {cohens_h(micro(f,'gpt-3.5-turbo-0125'),micro(f,'human')):+.3f})")

# =========================================================================
# E) VERDICT BREAKDOWN
# =========================================================================
banner("E) VERDICT-STRATIFIED family distribution; non-CE-only check for GE5 gap")
print("[verdict counts per arm (zero_shot)]")
print(pd.crosstab(zs["model"],zs["verdict"]).reindex(ARMS).to_string())
print("\n[GE5 share within each verdict, per arm]")
for v in ["CE","WA","RE","TLE"]:
    sub=zs[zs.verdict==v]
    row=f"  {v:4s}: "
    for a in ARMS:
        s=sub[sub.model==a]; row+=f"{ALAB[a]}={ (s.family=='GE5').mean()*100 if len(s) else 0:5.1f}%(n{len(s)})  "
    print(row)
print("\n[NON-CE submissions only — family % per arm (does GE5 gap survive?)]")
nonce=zs[zs.verdict!="CE"].copy()
Nn={a:int((nonce.model==a).sum()) for a in ARMS}
print("non-CE N per arm:",{ALAB[a]:Nn[a] for a in ARMS})
hdr=f"{'fam':4s} {'name':9s}"+"".join(f"{ALAB[a]:>11s}" for a in ARMS)
print(hdr)
for f in ["GE1","GE5","GE2","AE1","AE2","AE5","GE4","GE6"]:
    line=f"{f:4s} {FAMILY_NAMES[f]:9s}"
    for a in ARMS:
        c=int(((nonce.model==a)&(nonce.family==f)).sum()); line+=f"  {c/Nn[a]*100:6.2f}%"
    print(line)
cH=int(((nonce.model=='human')&(nonce.family=='GE5')).sum()); cA=int(((nonce.model=='gpt-3.5-turbo-0125')&(nonce.family=='GE5')).sum())
h,lo,hi=h_ci(cA,Nn['gpt-3.5-turbo-0125'],cH,Nn['human'])
z,pv=two_prop_z(cA,Nn['gpt-3.5-turbo-0125'],cH,Nn['human'])
print(f"  GE5 non-CE: human={cH/Nn['human']*100:.2f}% gpt-3.5={cA/Nn['gpt-3.5-turbo-0125']*100:.2f}%  h={h:+.3f} [{lo:+.3f},{hi:+.3f}]  p={pv:.2e}")

# =========================================================================
# G) GE4/GE6 upper CI + overflow-reachable subset
# =========================================================================
banner("G) GE4/GE6 one-sided 95% upper CI (model arms) + overflow-reachable subset")
def upper95(x,n):
    # one-sided 95% upper bound (Clopper-Pearson). For x=0 -> rule of three 3/n.
    if x==0: return 3.0/n
    return stats.beta.ppf(0.95, x+1, n-x)
for f in ["GE4","GE6"]:
    for a in ["gpt-3.5-turbo-0125","gpt-5.4-nano"]:
        x=int(((zs.model==a)&(zs.family==f)).sum()); n=N[a]
        print(f"  {f} {FAMILY_NAMES[f]:9s} {ALAB[a]:13s}: x={x}/{n}  rate={x/n*100:.3f}%  upper95={upper95(x,n)*100:.3f}%")
# overflow-reachable subset: problems where human produced >=1 GE4.1
ge4_probs=set(zs[(zs.model=='human')&(zs.leaf=='GE4.1')]["problem_id"])
print(f"\noverflow-reachable subset = problems with >=1 human GE4.1 bug: {len(ge4_probs)} problems")
for a in ARMS:
    sub=zs[(zs.model==a)&(zs.problem_id.isin(ge4_probs))]
    c=int((sub.family=="GE4").sum()); n=len(sub)
    print(f"  {ALAB[a]:14s}: GE4 in subset = {c}/{n} = {c/n*100 if n else 0:.3f}% (upper95={upper95(c,n)*100 if n else 0:.3f}%)")

# =========================================================================
# H) EQUIVALENCE — Cramér's V 95% CI upper bound (human vs gpt-3.5)
# =========================================================================
banner("H) Cramer's V (human vs gpt-3.5 family dist) with bootstrap 95% CI -> divergence bound")
present=[f for f in FAMS_OBS]
cH=zs[zs.model=='human']["family"].value_counts().reindex(present).fillna(0)
cA=zs[zs.model=='gpt-3.5-turbo-0125']["family"].value_counts().reindex(present).fillna(0)
tab=pd.DataFrame({'human':cH,'gpt-3.5':cA})
tab=tab[tab.sum(axis=1)>0]
chi2,p,dof,v=cramers_v(tab.T.values)
print(f"point: chi2={chi2:.1f} dof={dof} p={p:.2e}  Cramer's V={v:.4f}")
# bootstrap: resample submissions within each arm
pH=tab['human'].values/tab['human'].sum(); pA=tab['gpt-3.5'].values/tab['gpt-3.5'].sum()
vs=[]
for b in range(B):
    bh=np.random.multinomial(int(tab['human'].sum()),pH)
    ba=np.random.multinomial(int(tab['gpt-3.5'].sum()),pA)
    t2=np.vstack([bh,ba])
    keep=t2.sum(axis=0)>0
    _,_,_,vv=cramers_v(t2[:,keep])
    vs.append(vv)
print(f"bootstrap Cramer's V 95% CI = [{np.percentile(vs,2.5):.4f}, {np.percentile(vs,97.5):.4f}]  (B={B})")
print(f"=> human/gpt-3.5 family divergence is bounded: Cramer's V <= {np.percentile(vs,97.5):.3f} (small effect).")

# =========================================================================
# D) submissions per problem per arm
# =========================================================================
banner("D) wrong-submissions-per-problem distribution per arm (zero_shot)")
for a in ARMS:
    s=zs[zs.model==a].groupby("problem_id").size()
    print(f"  {ALAB[a]:14s}: problems={len(s):4d}  mean={s.mean():5.2f}  median={s.median():4.1f}  "
          f"p90={np.percentile(s,90):5.1f}  max={s.max():4d}  total={s.sum()}")

# =========================================================================
# F) Difficulty x family multi-panel figure  (GE5, AE1, GE2)
# =========================================================================
banner("F) Difficulty x family (GE5, AE1, GE2) — table + multi-panel figure")
ARM_LABEL={"human":"Human","gpt-3.5-turbo-0125":"GPT-3.5","gpt-5.4-nano":"GPT-5.4-nano"}
ARM_COLOR={"human":"#4C72B0","gpt-3.5-turbo-0125":"#DD8452","gpt-5.4-nano":"#55A868"}
panel_fams=["GE5","AE1","GE2"]
data={}
for f in panel_fams:
    zs["isf"]=(zs.family==f).astype(int)
    pct=(zs.groupby(["difficulty","model"])["isf"].mean().unstack("model").reindex(columns=ARMS)*100).reindex(BINS)
    nmat=zs.groupby(["difficulty","model"]).size().unstack("model").reindex(columns=ARMS).reindex(BINS)
    data[f]=(pct,nmat)
    print(f"\n[{f} {FAMILY_NAMES[f]} % by difficulty x arm]")
    print(pct.round(1).to_string())
fig,axes=plt.subplots(1,3,figsize=(13,3.6),sharex=True)
for ax,f in zip(axes,panel_fams):
    pct,_=data[f]; x=np.arange(len(BINS)); w=0.26
    for k,a in enumerate(ARMS):
        ax.bar(x+(k-1)*w,pct.reindex(BINS)[a].values,w,label=ARM_LABEL[a],color=ARM_COLOR[a])
    ax.set_xticks(x); ax.set_xticklabels([b.capitalize() for b in BINS],fontsize=9)
    ax.set_title(f"{FAMILY_NAMES[f]} ({f})"); ax.yaxis.set_major_formatter(PercentFormatter(decimals=0))
    ax.grid(axis="y",alpha=0.3)
axes[0].set_ylabel("% of arm's bugs in bin")
axes[0].legend(frameon=False,fontsize=8.5)
fig.supxlabel("Problem difficulty (cf_rating bin)",fontsize=10)
plt.tight_layout()
fp=os.path.join(FIGDIR,"fig_family_by_difficulty.png")
fig.savefig(fp,dpi=300,bbox_inches="tight")
import shutil; shutil.copy(fp,os.path.join(PAPER_FIG,"fig_family_by_difficulty.png"))
print(f"\nsaved {fp} and copied to {PAPER_FIG}")

# =========================================================================
# I) RQ1 table with Cohen's h 95% CI -> update tables.tex
# =========================================================================
banner("I) RQ1 family table with Cohen's h 95% CI (gpt-3.5 vs human) -> tables.tex")
def bh_fdr(p):
    p=np.asarray(p); n=len(p); order=np.argsort(p); ranked=p[order]*n/(np.arange(n)+1)
    q=np.minimum.accumulate(ranked[::-1])[::-1]; out=np.empty(n); out[order]=np.clip(q,0,1); return out
rows=[]
for f in FAMILY_ORDER:
    cH=int(((zs.model=='human')&(zs.family==f)).sum())
    c35=int(((zs.model=='gpt-3.5-turbo-0125')&(zs.family==f)).sum())
    c54=int(((zs.model=='gpt-5.4-nano')&(zs.family==f)).sum())
    if cH==0 and c35==0 and c54==0: continue
    h,lo,hi=h_ci(c35,N['gpt-3.5-turbo-0125'],cH,N['human'])
    z,pv=two_prop_z(c35,N['gpt-3.5-turbo-0125'],cH,N['human'])
    rows.append(dict(family=f,name=FAMILY_NAMES[f],
                     ph=cH/N['human']*100,p35=c35/N['gpt-3.5-turbo-0125']*100,p54=c54/N['gpt-5.4-nano']*100,
                     h=h,lo=lo,hi=hi,p=pv))
R=pd.DataFrame(rows); R["q"]=bh_fdr(R["p"].values)
print(R.assign(ph=R.ph.round(1),p35=R.p35.round(1),p54=R.p54.round(1),
               h=R.h.round(3),lo=R.lo.round(3),hi=R.hi.round(3),
               p=R.p.map(lambda x:f"{x:.1e}"),q=R.q.map(lambda x:f"{x:.1e}")).to_string(index=False))

def esc(s): return str(s).replace("&","\\&")
lat=[r"\begin{table}[t]",r"\centering",
 r"\caption{Bug-family distribution by arm (zero-shot, \% of each arm's bugs). $h$ is Cohen's $h$ vs.\ human (positive: AI more frequent) with 95\% CI; $q$ is BH-FDR.}",
 r"\label{tab:rq1-family}",r"\small",r"\begin{tabular}{llrrrr@{\,}lr}",r"\toprule",
 r"Fam & Name & Human & GPT-3.5 & G5.4-nano & \multicolumn{2}{c}{$h_{3.5}$ [95\% CI]} & $q_{3.5}$ \\",r"\midrule"]
for _,r in R.iterrows():
    star="$^{*}$" if r["q"]<0.05 else ""
    lat.append(f"{r['family']} & {esc(r['name'])} & {r['ph']:.1f} & {r['p35']:.1f} & {r['p54']:.1f} & "
               f"{r['h']:+.2f} & [{r['lo']:+.2f}, {r['hi']:+.2f}] & {r['q']:.1e}{star} \\\\")
lat+=[r"\bottomrule",r"\end{tabular}",r"\end{table}"]
RQ1_LATEX="\n".join(lat)

# rebuild tables.tex: keep RQ2 + judge from old file, replace RQ1 block
TBL=os.path.join(REPO,"analysis","tables.tex")
old=open(TBL).read()
# split out RQ2 and judge tables (everything after first \end{table})
parts=old.split(r"\end{table}")
# parts[0]=header+RQ1, parts[1]=RQ2, parts[2]=judge, parts[3]=trailing
rq2=("\\end{table}".join([""]+[parts[1]])).strip()+"\n"  # reconstruct RQ2 with its end
# safer: regenerate by locating the two later tables
import re
tables=re.findall(r"\\begin\{table\}.*?\\end\{table\}",old,flags=re.S)
rq2_tbl=tables[1] if len(tables)>1 else ""
judge_tbl=tables[2] if len(tables)>2 else ""
with open(TBL,"w") as fh:
    fh.write("% Auto-generated — RQ1 (with Cohen's h 95% CI), RQ2, judge tables\n\n")
    fh.write(RQ1_LATEX+"\n\n"+rq2_tbl+"\n\n"+judge_tbl+"\n")
print(f"\nupdated {TBL} (RQ1 table now has h 95% CI column)")
print("\nDONE.")
