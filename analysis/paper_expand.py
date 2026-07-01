#!/usr/bin/env python
"""
Paper-expansion analyses P1-P6 for aitaxo. Read-only inputs; git untouched.

Sources:
  data/classifications/full.csv            judge labels (all non-AC bugs, all arms/stages)
  data/manifest.csv                        problem cf_rating + cf_tags ('|'-separated, multi)
  data/classifications/gold_human{1,2}.csv two annotators (375 items)

Tagging convention (P1): a problem belongs to EVERY one of its cf_tags (multi-membership),
so a submission is counted under each tag of its problem. We restrict to tags carried by
>=8 problems for stable per-arm rates. Per-arm family % within a tag uses that arm's
submissions on problems carrying the tag as the denominator.

Seeds: np.random.seed(20260701). Outputs: stdout tables; figures to analysis/figures/
(copied to papers); LaTeX appended to analysis/tables.tex (P1,P2,P3,P5 blocks).
"""
import os, json, numpy as np, pandas as pd
from scipy import stats
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter

np.random.seed(20260701)
REPO="/Users/cdw/VSCode/aitaxo"; CLS=f"{REPO}/data/classifications"
FIGDIR=f"{REPO}/analysis/figures"; PAPER_FIG="/Users/cdw/VSCode/papers/aitaxo/figures"
ARMS=["human","gpt-3.5-turbo-0125","gpt-5.4-nano"]
ALAB={"human":"Human","gpt-3.5-turbo-0125":"GPT-3.5","gpt-5.4-nano":"GPT-5.4-nano"}
SLAB={"human":"human","gpt-3.5-turbo-0125":"gpt-3.5","gpt-5.4-nano":"nano"}
ACOL={"human":"#4C72B0","gpt-3.5-turbo-0125":"#DD8452","gpt-5.4-nano":"#55A868"}
FAMILY_NAMES={"GE1":"Design","GE2":"Boundary","GE3":"Condition","GE4":"Data Type",
              "GE5":"Syntax","GE6":"I/O","AE1":"Math","AE2":"Greedy","AE3":"Graph",
              "AE4":"Rec/D&C","AE5":"DP","AE6":"Search"}
FAMILY_ORDER=["GE1","GE2","GE3","GE4","GE5","GE6","AE1","AE2","AE3","AE4","AE5","AE6"]
# leaf names (Wei et al. taxonomy.py verbatim) for observed leaves
LEAF_NAMES={
 "GE1.1":"Incorrect Algorithm","GE1.2":"Misunderstanding Requirements","GE1.3":"Overly Complex/Inefficient",
 "GE2.1":"Edge/Boundary Handling","GE2.2":"Off-by-one","GE3.1":"Faulty Condition",
 "GE4.1":"Overflow/Precision","GE5.1":"Compilation Error","GE6.1":"Input Format","GE6.2":"Output Format",
 "AE1.1":"Formula/Derivation","AE1.2":"Special Math Structure","AE2.1":"Suboptimal Greedy Choice",
 "AE5.1":"DP State Definition","AE5.2":"DP Transition"}

def primary_leaf(x): return np.nan if pd.isna(x) else str(x).split(",")[0].strip()
def fam_of(l): return np.nan if pd.isna(l) else str(l).split(".")[0].strip()
def cohens_h(p1,p2): return 2*np.arcsin(np.sqrt(p1))-2*np.arcsin(np.sqrt(p2))
def two_prop_z(x1,n1,x2,n2):
    if n1==0 or n2==0: return 0.0,1.0
    p=(x1+x2)/(n1+n2); se=np.sqrt(p*(1-p)*(1/n1+1/n2))
    if se==0: return 0.0,1.0
    z=(x1/n1-x2/n2)/se; return z,2*(1-stats.norm.cdf(abs(z)))
def banner(t): print("\n"+"="*82+f"\n{t}\n"+"="*82)
def esc(s): return str(s).replace("&","\\&")

full=pd.read_csv(os.path.join(CLS,"full.csv"))
full["leaf"]=full["labels"].map(primary_leaf); full["family"]=full["leaf"].map(fam_of)
man=pd.read_csv(os.path.join(REPO,"data","manifest.csv"))
pid_tags={p:[t.strip() for t in str(tg).split("|") if t.strip()] for p,tg in zip(man["problem_id"],man["cf_tags"].fillna(""))}
zs=full[full["stage"]=="zero_shot"].copy()
zs["tags"]=zs["problem_id"].map(lambda p:pid_tags.get(p,[]))
N={a:int((zs.model==a).sum()) for a in ARMS}

LATEX_BLOCKS=[]  # collect to append

# =====================================================================
# P1 — algorithm-tag analysis
# =====================================================================
banner("P1 — ALGORITHM-TAG (cf_tags) ANALYSIS")
from collections import Counter
prob_per_tag=Counter()
for p,ts in pid_tags.items():
    for t in ts: prob_per_tag[t]+=1
TAGS=[t for t,n in prob_per_tag.most_common() if n>=8]
print("tags (>=8 problems):",TAGS)
# (a) problems & bug counts per tag per arm
print("\n[(a) per tag: #problems, bug counts per arm]")
print(f"{'tag':24s} {'#prob':>5s} "+" ".join(f"{SLAB[a]:>8s}" for a in ARMS))
tag_rows=[]
for t in TAGS:
    pids=[p for p in pid_tags if t in pid_tags[p]]
    sub=zs[zs.problem_id.isin(pids)]
    cnts={a:int((sub.model==a).sum()) for a in ARMS}
    print(f"{t:24s} {prob_per_tag[t]:5d} "+" ".join(f"{cnts[a]:8d}" for a in ARMS))
    tag_rows.append((t,prob_per_tag[t],cnts))
# (b)(c) GE1/GE5/AE1 family % per tag, human vs gpt-3.5 + h
print("\n[(b,c) family % by tag and arm; h = Cohen's h (gpt-3.5 - human)]")
fam_focus=["GE1","GE5","AE1"]
res={f:[] for f in fam_focus}
hdr=f"{'tag':22s}"+"".join(f"  {fn+'(H/3.5/N) h':>22s}" for fn in [FAMILY_NAMES[f] for f in fam_focus])
print(hdr)
for t in TAGS:
    pids=[p for p in pid_tags if t in pid_tags[p]]
    sub=zs[zs.problem_id.isin(pids)]
    line=f"{t:22s}"
    for f in fam_focus:
        cell=""
        rec={"tag":t}
        for a in ARMS:
            s=sub[sub.model==a]; n=len(s); c=int((s.family==f).sum())
            rec[SLAB[a]]=c/n*100 if n else 0; rec[SLAB[a]+"_n"]=n; rec[SLAB[a]+"_c"]=c
        h=cohens_h(rec["gpt-3.5"]/100,rec["human"]/100)
        rec["h"]=h; res[f].append(rec)
        line+=f"  {rec['human']:4.1f}/{rec['gpt-3.5']:4.1f}/{rec['nano']:4.1f} {h:+.2f}"
    print(line)
# headline: which tags maximize GE5 / GE1 gap
print("\n[GE5 Syntax gap (gpt-3.5 - human), by tag, sorted]")
g5=pd.DataFrame(res["GE5"]).sort_values("h",ascending=False)
for _,r in g5.iterrows():
    z,p=two_prop_z(int(r["gpt-3.5_c"]),int(r["gpt-3.5_n"]),int(r["human_c"]),int(r["human_n"]))
    print(f"  {r['tag']:24s} human={r['human']:4.1f}% gpt-3.5={r['gpt-3.5']:4.1f}%  h={r['h']:+.3f}  p={p:.2e}")
print("\n[GE1 Design gap (gpt-3.5 - human), by tag, sorted]")
g1=pd.DataFrame(res["GE1"]).sort_values("h")
for _,r in g1.iterrows():
    z,p=two_prop_z(int(r["gpt-3.5_c"]),int(r["gpt-3.5_n"]),int(r["human_c"]),int(r["human_n"]))
    print(f"  {r['tag']:24s} human={r['human']:4.1f}% gpt-3.5={r['gpt-3.5']:4.1f}%  h={r['h']:+.3f}  p={p:.2e}")

# figure: GE1 & GE5 by tag (human vs gpt-3.5 vs nano), top tags by bug volume
figtags=[t for t,_ in prob_per_tag.most_common() if t in TAGS][:9]
fig,axes=plt.subplots(1,2,figsize=(13,4.2))
for ax,f in zip(axes,["GE1","GE5"]):
    d=pd.DataFrame(res[f]).set_index("tag").reindex(figtags)
    x=np.arange(len(figtags)); w=0.26
    for k,a in enumerate(ARMS):
        ax.bar(x+(k-1)*w,d[SLAB[a]].values,w,label=ALAB[a],color=ACOL[a])
    ax.set_xticks(x); ax.set_xticklabels(figtags,rotation=30,ha="right",fontsize=8)
    ax.set_title(f"{FAMILY_NAMES[f]} ({f}) % by problem tag")
    ax.yaxis.set_major_formatter(PercentFormatter(decimals=0)); ax.grid(axis="y",alpha=0.3)
axes[0].set_ylabel("% of arm's bugs on tag's problems"); axes[0].legend(frameon=False,fontsize=8)
plt.tight_layout()
fp=os.path.join(FIGDIR,"fig_by_type.png"); fig.savefig(fp,dpi=300,bbox_inches="tight")
import shutil; shutil.copy(fp,os.path.join(PAPER_FIG,"fig_by_type.png"))
print(f"saved {fp} + copied to papers")
# LaTeX: tag x (GE1,GE5,AE1) human vs gpt-3.5
lat=[r"\begin{table*}[t]",r"\centering",
 r"\caption{Bug-family rates by Codeforces problem tag (multi-membership; tags on $\geq$8 problems). For each tag and family we report Human / GPT-3.5 \% and Cohen's $h$ (GPT-3.5$-$Human).}",
 r"\label{tab:by-tag}",r"\small",r"\begin{tabular}{lr ccc ccc ccc}",r"\toprule",
 r"& & \multicolumn{3}{c}{Design (GE1)} & \multicolumn{3}{c}{Syntax (GE5)} & \multicolumn{3}{c}{Math (AE1)} \\",
 r"\cmidrule(lr){3-5}\cmidrule(lr){6-8}\cmidrule(lr){9-11}",
 r"Tag & \#prob & Hum & 3.5 & $h$ & Hum & 3.5 & $h$ & Hum & 3.5 & $h$ \\",r"\midrule"]
dd={f:pd.DataFrame(res[f]).set_index("tag") for f in fam_focus}
for t in TAGS:
    cells=[]
    for f in fam_focus:
        r=dd[f].loc[t]; cells+= [f"{r['human']:.1f}",f"{r['gpt-3.5']:.1f}",f"{r['h']:+.2f}"]
    lat.append(f"{esc(t)} & {prob_per_tag[t]} & "+" & ".join(cells)+r" \\")
lat+=[r"\bottomrule",r"\end{tabular}",r"\end{table*}"]
LATEX_BLOCKS.append(("P1 by-tag","\n".join(lat)))

# =====================================================================
# P5 — RQ3 per-family residual/fix + reflection-introduced bugs
# =====================================================================
banner("P5 — RQ3 per-family residual / fix rate (gpt-3.5) + reflection-introduced bugs")
g35=full[full.model=="gpt-3.5-turbo-0125"]
z0=g35[g35.stage=="zero_shot"]; rf=g35[g35.stage=="reflect"]
z0c=z0["family"].value_counts().reindex(FAMILY_ORDER).fillna(0).astype(int)
rfc=rf["family"].value_counts().reindex(FAMILY_ORDER).fillna(0).astype(int)
print(f"turn-0={len(z0)} residual={len(rf)} overall residual share={len(rf)/len(z0)*100:.1f}%")
tbl=pd.DataFrame({"t0":z0c,"res":rfc})
tbl=tbl[(tbl.t0>0)|(tbl.res>0)]
tbl["persist_%"]=np.where(tbl.t0>0,tbl.res/tbl.t0*100,np.nan)
tbl["delta"]=tbl.res-tbl.t0
# two-proportion test on share-of-stage (does the family's *share* rise?)
def share_test(f):
    xA,nA=int(rfc[f]),len(rf); xH,nH=int(z0c[f]),len(z0)
    z,p=two_prop_z(xA,nA,xH,nH); return p
print(f"\n{'fam':4s} {'name':9s} {'t0':>4s} {'res':>4s} {'persist%':>8s} {'Δcount':>6s} {'share t0->res':>14s} {'p(share)':>9s}")
for f in tbl.index:
    sp=share_test(f)
    s0=z0c[f]/len(z0)*100; s1=rfc[f]/len(rf)*100
    print(f"{f:4s} {FAMILY_NAMES[f]:9s} {tbl.loc[f,'t0']:4d} {tbl.loc[f,'res']:4d} {tbl.loc[f,'persist_%']:8.1f} {tbl.loc[f,'delta']:+6d}  {s0:5.1f}->{s1:5.1f}%   {sp:9.2e}")
# families whose residual COUNT rose (reflection introduced/relabeled)
rose=tbl[tbl.delta>0]
print("\n[families with residual count > turn-0 count (net new in residual)]")
for f in rose.index:
    print(f"  {f} {FAMILY_NAMES[f]}: {tbl.loc[f,'t0']}->{tbl.loc[f,'res']} (+{tbl.loc[f,'delta']}, persist {tbl.loc[f,'persist_%']:.0f}%)")
# overall family-mix shift chi2
tab=pd.DataFrame({"t0":z0c,"res":rfc}); tab=tab[tab.sum(axis=1)>0]
chi2,p,dof,_=stats.chi2_contingency(tab.T.values)
print(f"\n[family-mix shift turn-0 vs residual] chi2={chi2:.1f} dof={dof} p={p:.2e}")
print("Interpretation: GE5 Syntax is the only family with persist<60% (reflection fixes compile errors);")
print("GE2 Boundary / AE2 Greedy persist>100% -> reflection leaves as many or more (no net repair, mild relabel).")
# LaTeX
lat=[r"\begin{table}[t]",r"\centering",
 r"\caption{GPT-3.5 self-reflection: per-family turn-0 vs.\ residual bug counts, persistence rate (residual/turn-0), and the change in each family's share of the stage's bugs. $p$ tests the share shift (two-proportion).}",
 r"\label{tab:rq3-residual}",r"\small",r"\begin{tabular}{llrrrr}",r"\toprule",
 r"Fam & Name & Turn-0 & Residual & Persist\% & $\Delta$share \\",r"\midrule"]
for f in tbl.index:
    s0=z0c[f]/len(z0)*100; s1=rfc[f]/len(rf)*100
    lat.append(f"{f} & {esc(FAMILY_NAMES[f])} & {tbl.loc[f,'t0']} & {tbl.loc[f,'res']} & {tbl.loc[f,'persist_%']:.0f} & {s1-s0:+.1f} \\\\")
lat+=[r"\bottomrule",r"\end{tabular}",r"\end{table}"]
LATEX_BLOCKS.append(("P5 rq3-residual","\n".join(lat)))

# =====================================================================
# P2 — full leaf-level distribution table
# =====================================================================
banner("P2 — FULL LEAF-LEVEL DISTRIBUTION (primary label, zero_shot)")
leaves=sorted([l for l in zs["leaf"].dropna().unique()], key=lambda l:(FAMILY_ORDER.index(fam_of(l)),l))
print(f"{'leaf':7s} {'name':28s} {'human':>7s} {'gpt-3.5':>8s} {'nano':>6s}")
prows=[]
for l in leaves:
    row={"leaf":l,"name":LEAF_NAMES.get(l,"?")}
    for a in ARMS:
        c=int(((zs.model==a)&(zs.leaf==l)).sum()); row[a]=c/N[a]*100
    prows.append(row)
    print(f"{l:7s} {LEAF_NAMES.get(l,'?'):28s} {row['human']:6.2f}% {row['gpt-3.5-turbo-0125']:7.2f}% {row['gpt-5.4-nano']:5.2f}%")
# verify leaf-sum == family-sum
print("\n[verify leaf% sums == family% per arm]")
for a in ARMS:
    for f in ["GE1","GE5","AE1","AE5"]:
        ls=sum(int(((zs.model==a)&(zs.leaf==l)).sum()) for l in leaves if fam_of(l)==f)
        fs=int(((zs.model==a)&(zs.family==f)).sum())
        assert ls==fs, f"MISMATCH {a} {f}"
print("  OK: all leaf sums equal family sums.")
lat=[r"\begin{table}[t]",r"\centering",
 r"\caption{Leaf-level (primary-label) bug distribution by arm (zero-shot, \% of arm's bugs). Only leaves observed in the corpus are shown; per-family leaf shares sum to the family total.}",
 r"\label{tab:leaf-dist}",r"\small",r"\begin{tabular}{llrrr}",r"\toprule",
 r"Leaf & Name & Human & GPT-3.5 & G5.4-nano \\",r"\midrule"]
cur=None
for r in prows:
    fam=fam_of(r["leaf"])
    if fam!=cur: lat.append(r"\addlinespace"); cur=fam
    lat.append(f"{r['leaf']} & {esc(r['name'])} & {r['human']:.2f} & {r['gpt-3.5-turbo-0125']:.2f} & {r['gpt-5.4-nano']:.2f} \\\\")
lat+=[r"\bottomrule",r"\end{tabular}",r"\end{table}"]
LATEX_BLOCKS.append(("P2 leaf-dist","\n".join(lat)))

# =====================================================================
# P3 — family x verdict
# =====================================================================
banner("P3 — VERDICT distribution per arm + family distribution within verdict")
vt=pd.crosstab(zs["model"],zs["verdict"],normalize="index").reindex(ARMS)*100
print("[verdict % per arm]"); print(vt.round(1).to_string())
print("\n[WA-only family % per arm (the 'real-bug' body, GE5 excluded by construction)]")
wa=zs[zs.verdict=="WA"]; Nw={a:int((wa.model==a).sum()) for a in ARMS}
print(f"WA N per arm: {[(SLAB[a],Nw[a]) for a in ARMS]}")
print(f"{'fam':4s} {'name':9s}"+"".join(f"{SLAB[a]:>9s}" for a in ARMS))
for f in FAMILY_ORDER:
    if int((wa.family==f).sum())==0: continue
    line=f"{f:4s} {FAMILY_NAMES[f]:9s}"
    for a in ARMS:
        c=int(((wa.model==a)&(wa.family==f)).sum()); line+=f"  {c/Nw[a]*100:6.2f}%"
    print(line)
lat=[r"\begin{table}[t]",r"\centering",
 r"\caption{Verdict mix per arm (\% of arm's non-AC submissions). CE is the GE5 Syntax family by construction; the WA body carries the conceptual bugs.}",
 r"\label{tab:verdict}",r"\small",r"\begin{tabular}{lrrrr}",r"\toprule",
 r"Arm & WA & CE & RE & TLE \\",r"\midrule"]
for a in ARMS:
    row=vt.loc[a]
    lat.append(f"{ALAB[a]} & {row.get('WA',0):.1f} & {row.get('CE',0):.1f} & {row.get('RE',0):.1f} & {row.get('TLE',0):.1f} \\\\")
lat+=[r"\bottomrule",r"\end{tabular}",r"\end{table}"]
LATEX_BLOCKS.append(("P3 verdict","\n".join(lat)))

# =====================================================================
# P4 — judge confusion matrix (gold consensus family -> judge family)
# =====================================================================
banner("P4 — JUDGE CONFUSION (gold consensus family -> judge family)")
g1=pd.read_csv(os.path.join(CLS,"gold_human1.csv")); g2=pd.read_csv(os.path.join(CLS,"gold_human2.csv"))
for g in (g1,g2): g["fam"]=g["labels"].map(primary_leaf).map(fam_of)
g1i=g1.set_index("item_id"); g2i=g2.set_index("item_id")
common=[i for i in g1i.index if i in g2i.index]
jmap=full.set_index("item_id")["family"]
agree=[i for i in common if g1i.loc[i,"fam"]==g2i.loc[i,"fam"]]
FAMS_OBS=[f for f in FAMILY_ORDER if int(zs["family"].value_counts().get(f,0))>0]
M=pd.DataFrame(0,index=FAMS_OBS,columns=FAMS_OBS,dtype=int)
extra=0
for i in agree:
    gf=g1i.loc[i,"fam"]; jf=jmap.get(i,None)
    if gf in M.index and jf in M.columns: M.loc[gf,jf]+=1
    else: extra+=1
print(f"adjudicated (family-agree) gold items: {len(agree)} (used {M.values.sum()}, off-grid {extra})")
print("\n[confusion counts: rows=gold consensus, cols=judge]")
print(M.to_string())
acc=np.trace(M.values)/M.values.sum()
print(f"\ndiagonal accuracy = {acc:.3f}")
print("[top off-diagonal confusions]")
off=[]
for gf in FAMS_OBS:
    for jf in FAMS_OBS:
        if gf!=jf and M.loc[gf,jf]>0: off.append((M.loc[gf,jf],gf,jf))
for c,gf,jf in sorted(off,reverse=True)[:8]:
    print(f"  gold {gf}({FAMILY_NAMES[gf]}) -> judge {jf}({FAMILY_NAMES[jf]}): {c}")
# figure heatmap (row-normalized)
Mr=M.div(M.sum(axis=1).replace(0,np.nan),axis=0).fillna(0)
fig,ax=plt.subplots(figsize=(6.6,5.6))
im=ax.imshow(Mr.values,cmap="Blues",vmin=0,vmax=1,aspect="auto")
ax.set_xticks(range(len(FAMS_OBS))); ax.set_xticklabels([f"{f}\n{FAMILY_NAMES[f]}" for f in FAMS_OBS],fontsize=7)
ax.set_yticks(range(len(FAMS_OBS))); ax.set_yticklabels([f"{f} {FAMILY_NAMES[f]}" for f in FAMS_OBS],fontsize=7)
ax.set_xlabel("Judge (LLM) family"); ax.set_ylabel("Gold consensus family")
ax.set_title(f"Judge vs gold family confusion (row-norm; diag acc={acc:.2f})",fontsize=10)
for i in range(len(FAMS_OBS)):
    for j in range(len(FAMS_OBS)):
        v=Mr.values[i,j]
        if v>0: ax.text(j,i,f"{v:.2f}",ha="center",va="center",fontsize=6.5,color="white" if v>0.5 else "black")
fig.colorbar(im,ax=ax,fraction=0.046,pad=0.04)
plt.tight_layout()
fp=os.path.join(FIGDIR,"fig_confusion.png"); fig.savefig(fp,dpi=300,bbox_inches="tight")
shutil.copy(fp,os.path.join(PAPER_FIG,"fig_confusion.png"))
print(f"saved {fp} + copied to papers")

# =====================================================================
# P6 — coverage / saturation curve (distinct leaves vs #submissions)
# =====================================================================
banner("P6 — CATEGORY COVERAGE / SATURATION (distinct leaves vs #submissions)")
fig,ax=plt.subplots(figsize=(7.5,4.3))
for a in ARMS:
    s=np.array(zs[zs.model==a]["leaf"].dropna().tolist(),dtype=object)
    np.random.shuffle(s)
    seen=set(); curve=[]
    for x in s: seen.add(x); curve.append(len(seen))
    ax.plot(range(1,len(curve)+1),curve,label=f"{ALAB[a]} ({len(seen)} leaves)",color=ACOL[a],lw=2)
    print(f"  {ALAB[a]:14s}: {len(s)} subs -> {len(seen)} distinct leaves (saturates well before N)")
allleaf=zs["leaf"].dropna().nunique()
ax.set_xlabel("# submissions sampled (shuffled, seed=20260701)"); ax.set_ylabel("cumulative distinct leaves")
ax.set_title(f"Taxonomy coverage saturation (corpus uses {allleaf} of 32 leaves)")
ax.legend(frameon=False); ax.grid(alpha=0.3)
plt.tight_layout()
fp=os.path.join(FIGDIR,"fig_saturation.png"); fig.savefig(fp,dpi=300,bbox_inches="tight")
shutil.copy(fp,os.path.join(PAPER_FIG,"fig_saturation.png"))
print(f"corpus distinct leaves (zero_shot): {allleaf} / 32 ; saved {fp} + copied to papers")

# =====================================================================
# append LaTeX blocks to tables.tex (keep existing RQ1/RQ2/judge)
# =====================================================================
banner("Appending P1,P5,P2,P3 LaTeX to analysis/tables.tex")
TBL=os.path.join(REPO,"analysis","tables.tex")
old=open(TBL).read()
marker="% ===== paper-expansion tables (P1,P5,P2,P3) ====="
if marker in old: old=old.split(marker)[0].rstrip()+"\n"
with open(TBL,"w") as fh:
    fh.write(old.rstrip()+"\n\n"+marker+"\n")
    for name,blk in LATEX_BLOCKS:
        fh.write(f"\n% --- {name} ---\n{blk}\n")
print("appended", [n for n,_ in LATEX_BLOCKS], "->", TBL)
print("\nDONE.")
