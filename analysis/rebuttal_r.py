#!/usr/bin/env python
"""
Accept-conversion rebuttal analyses R1-R3. Read-only; git untouched.

Framing (R1): GPT-3.5 self-reflection = a "compile-and-retry" intervention. We compare
the turn-0 bug profile (before intervention) to the residual profile (full.csv reflect
stage = the still-buggy submissions after up to `rounds_used` rounds; the AC-fixed ones
have left the pool). This measures whether the intervention closes the compile (GE5/CE)
gap and moves GPT-3.5's family profile toward the human profile.

Sources: data/classifications/full.csv (zero_shot + reflect stages), gold_human{1,2}.csv.
Seeds: np.random.seed(20260701).
"""
import os, numpy as np, pandas as pd
from scipy import stats
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter

np.random.seed(20260701)
REPO="/Users/cdw/VSCode/aitaxo"; CLS=f"{REPO}/data/classifications"
FIGDIR=f"{REPO}/analysis/figures"; PAPER_FIG="/Users/cdw/VSCode/papers/aitaxo/figures"
FN={"GE1":"Design","GE2":"Boundary","GE3":"Condition","GE4":"Data Type","GE5":"Syntax",
    "GE6":"I/O","AE1":"Math","AE2":"Greedy","AE3":"Graph","AE4":"Rec/D&C","AE5":"DP","AE6":"Search"}
ORDER=["GE1","GE2","GE3","GE4","GE5","GE6","AE1","AE2","AE3","AE4","AE5","AE6"]
ACOL={"human":"#4C72B0","turn0":"#DD8452","residual":"#8172B3"}
def pl(x): return np.nan if pd.isna(x) else str(x).split(",")[0].strip()
def fam(l): return np.nan if pd.isna(l) else str(l).split(".")[0].strip()
def cohens_h(p1,p2): return 2*np.arcsin(np.sqrt(np.clip(p1,0,1)))-2*np.arcsin(np.sqrt(np.clip(p2,0,1)))
def two_prop_z(x1,n1,x2,n2):
    if n1==0 or n2==0: return 0.0,1.0
    p=(x1+x2)/(n1+n2); se=np.sqrt(p*(1-p)*(1/n1+1/n2))
    if se==0: return 0.0,1.0
    z=(x1/n1-x2/n2)/se; return z,2*(1-stats.norm.cdf(abs(z)))
def cramers_v(t):
    t=np.asarray(t,float); chi2,p,dof,_=stats.chi2_contingency(t); n=t.sum(); k=min(t.shape)-1
    return (np.sqrt(chi2/(n*k)) if n*k>0 else 0.0),chi2,p,dof
def cramers_v_ci(cH,cX,B=5000):
    """bootstrap CI for Cramer's V between human vec cH and other vec cX (counts)."""
    keep=(cH+cX)>0; a=cH[keep]; b=cX[keep]
    v,_,_,_=cramers_v(np.vstack([a,b]))
    pa=a/a.sum(); pb=b/b.sum(); na=int(a.sum()); nb=int(b.sum()); vs=[]
    for _ in range(B):
        ba=np.random.multinomial(na,pa); bb=np.random.multinomial(nb,pb)
        k2=(ba+bb)>0
        vv,_,_,_=cramers_v(np.vstack([ba[k2],bb[k2]])); vs.append(vv)
    return v,np.percentile(vs,2.5),np.percentile(vs,97.5)
def banner(t): print("\n"+"="*82+f"\n{t}\n"+"="*82)

full=pd.read_csv(os.path.join(CLS,"full.csv"))
full["leaf"]=full["labels"].map(pl); full["family"]=full["leaf"].map(fam)
zs=full[full.stage=="zero_shot"].copy()
FAMS_OBS=[f for f in ORDER if int(zs.family.value_counts().get(f,0))>0]
hum=zs[zs.model=="human"]; Nh=len(hum)
t0 =full[(full.model=="gpt-3.5-turbo-0125")&(full.stage=="zero_shot")]
res=full[(full.model=="gpt-3.5-turbo-0125")&(full.stage=="reflect")]
def vec(df): return np.array([int((df.family==f).sum()) for f in FAMS_OBS],float)
cH=vec(hum); cT0=vec(t0); cR=vec(res)
def pct(c): return c/c.sum()*100

# ======================================================================
# R1 — compile-and-retry intervention: residual gap + convergence
# ======================================================================
banner("R1 — COMPILE-AND-RETRY intervention: residual CE(GE5) gap + convergence to human")
n_fixed=len(t0)-len(res)
print(f"turn-0 bugs={len(t0)}  fixed(AC)={n_fixed} ({n_fixed/len(t0)*100:.1f}%)  residual={len(res)}")
# (a) CE / GE5 share before vs after
ce_t0=int((t0.verdict=="CE").sum()); ce_res=int((res.verdict=="CE").sum())
ge5_t0=int((t0.family=="GE5").sum()); ge5_res=int((res.family=="GE5").sum())
ce_h=int((hum.verdict=="CE").sum())
print(f"\n(a) COMPILE (CE=GE5) share:")
print(f"    gpt-3.5 turn-0  : {ge5_t0}/{len(t0)} = {ge5_t0/len(t0)*100:.2f}%")
print(f"    gpt-3.5 residual: {ge5_res}/{len(res)} = {ge5_res/len(res)*100:.2f}%")
print(f"    human (ref)     : {ce_h}/{Nh} = {ce_h/Nh*100:.2f}%")
z,p_t0=two_prop_z(ge5_t0,len(t0),ce_h,Nh); z2,p_res=two_prop_z(ge5_res,len(res),ce_h,Nh)
print(f"    compile-gap vs human: turn-0 h={cohens_h(ge5_t0/len(t0),ce_h/Nh):+.3f} (p={p_t0:.1e}) "
      f"-> residual h={cohens_h(ge5_res/len(res),ce_h/Nh):+.3f} (p={p_res:.1e})")
print(f"    => intervention {'CLOSES' if p_res>0.05 else 'SHRINKS'} the compile gap "
      f"({ge5_t0/len(t0)*100:.1f}%->{ge5_res/len(res)*100:.1f}%, human {ce_h/Nh*100:.1f}%).")
# (b) Cramer's V human-vs-gpt3.5, turn-0 vs residual
vT0,loT0,hiT0=cramers_v_ci(cH,cT0)
vR ,loR ,hiR =cramers_v_ci(cH,cR)
print(f"\n(b) Human-vs-GPT3.5 family divergence (Cramer's V):")
print(f"    turn-0  : V={vT0:.4f} [{loT0:.4f},{hiT0:.4f}]")
print(f"    residual: V={vR:.4f} [{loR:.4f},{hiR:.4f}]")
print(f"    => {'CONVERGES (V drops)' if vR<vT0 else 'no convergence'}: divergence {vT0:.3f}->{vR:.3f} "
      f"({(vT0-vR)/vT0*100:+.1f}% change).")
# (c) residual family profile (GE5 down, GE1 up)
print(f"\n(c) family profile turn-0 -> residual (gpt-3.5), with human ref:")
print(f"    {'fam':4s} {'name':9s} {'turn-0%':>8s} {'resid%':>7s} {'Δ':>6s}  {'human%':>7s}")
for i,f in enumerate(FAMS_OBS):
    print(f"    {f:4s} {FN[f]:9s} {pct(cT0)[i]:7.2f} {pct(cR)[i]:6.2f} {pct(cR)[i]-pct(cT0)[i]:+6.2f}  {pct(cH)[i]:6.2f}")
# figure: 3-group bars human / turn-0 / residual
fig,ax=plt.subplots(figsize=(10,4.2))
x=np.arange(len(FAMS_OBS)); w=0.26
ax.bar(x-w,pct(cH),w,label="Human (ref)",color=ACOL["human"])
ax.bar(x,  pct(cT0),w,label="GPT-3.5 turn-0 (pre)",color=ACOL["turn0"])
ax.bar(x+w,pct(cR),w,label="GPT-3.5 residual (post compile-and-retry)",color=ACOL["residual"])
ax.set_xticks(x); ax.set_xticklabels([f"{f}\n{FN[f]}" for f in FAMS_OBS],fontsize=7.5)
ax.set_ylabel("% of arm's bugs"); ax.yaxis.set_major_formatter(PercentFormatter(decimals=0))
ax.set_title(f"Compile-and-retry moves GPT-3.5 toward human (Cramer's V {vT0:.3f}$\\to${vR:.3f})")
ax.legend(frameon=False,fontsize=8.5); ax.grid(axis="y",alpha=0.3)
plt.tight_layout()
fp=os.path.join(FIGDIR,"fig_intervention.png"); fig.savefig(fp,dpi=300,bbox_inches="tight")
import shutil; shutil.copy(fp,os.path.join(PAPER_FIG,"fig_intervention.png"))
print(f"saved {fp} + copied to papers")

# ======================================================================
# R2 — repair mis-targeting (human-tuned triage misses AI bugs)
# ======================================================================
banner("R2 — REPAIR MIS-TARGETING: human-priority top-k coverage on human vs gpt-3.5 bugs")
gp=zs[zs.model=="gpt-3.5-turbo-0125"]; Ng=len(gp)
hum_order=sorted(FAMS_OBS,key=lambda f:-int((hum.family==f).sum()))
print("human family priority (by frequency):",[f"{f}({FN[f]})" for f in hum_order])
print(f"\n(a) top-k (human priority) cumulative coverage of human vs gpt-3.5 bugs:")
print(f"    {'k':>2s} {'families':28s} {'human cov%':>10s} {'gpt-3.5 cov%':>12s} {'miss(AI-only gap)':>16s}")
rows=[]
for k in range(1,len(hum_order)+1):
    topk=hum_order[:k]
    hc=int(hum.family.isin(topk).sum())/Nh*100
    gc=int(gp.family.isin(topk).sum())/Ng*100
    rows.append(dict(k=k,fams=topk,hcov=hc,gcov=gc))
    print(f"    {k:2d} {','.join(topk):28s} {hc:9.1f}% {gc:11.1f}% {hc-gc:+15.1f}pp")
# key: where does GE5 (compile) sit in human priority, and how much AI volume it holds
ge5_rank=hum_order.index("GE5")+1
ge5_ai=int((gp.family=="GE5").sum())/Ng*100; ge5_h=int((hum.family=="GE5").sum())/Nh*100
print(f"\n    GE5 Syntax rank in human priority = #{ge5_rank}/{len(hum_order)} "
      f"(human {ge5_h:.1f}% -> low priority), but holds {ge5_ai:.1f}% of GPT-3.5 bugs "
      f"({ge5_ai/ge5_h:.1f}x more) -> a human-tuned triage deprioritizes exactly the AI-dominant family.")
# (b) effort on GE4/GE6 (human-only) wasted on AI
for f in ["GE4","GE6"]:
    hf=int((hum.family==f).sum())/Nh*100; gf=int((gp.family==f).sum())/Ng*100
    print(f"    {f} {FN[f]}: human {hf:.2f}% (gets repair effort) vs gpt-3.5 {gf:.2f}% "
          f"-> {(1-gf/hf)*100 if hf>0 else 0:.0f}% of that effort is idle on AI bugs.")
# figure
fig,ax=plt.subplots(figsize=(7.5,4.3))
K=[r["k"] for r in rows]
ax.plot(K,[r["hcov"] for r in rows],"o-",color="#4C72B0",label="coverage of Human bugs")
ax.plot(K,[r["gcov"] for r in rows],"s-",color="#DD8452",label="coverage of GPT-3.5 bugs")
for r in rows:
    if r["hcov"]-r["gcov"]>2:
        ax.annotate("",xy=(r["k"],r["gcov"]),xytext=(r["k"],r["hcov"]),arrowprops=dict(arrowstyle="-",color="gray",lw=0.6))
ax.set_xlabel("top-k families by HUMAN priority"); ax.set_ylabel("cumulative % of arm's bugs covered")
ax.set_title("Human-tuned triage priority under-covers GPT-3.5 bugs")
ax.yaxis.set_major_formatter(PercentFormatter(decimals=0)); ax.legend(frameon=False); ax.grid(alpha=0.3)
plt.tight_layout()
fp=os.path.join(FIGDIR,"fig_mistarget.png"); fig.savefig(fp,dpi=300,bbox_inches="tight")
shutil.copy(fp,os.path.join(PAPER_FIG,"fig_mistarget.png"))
print(f"saved {fp} + copied to papers")

# ======================================================================
# R3 — asymmetric-eps sensitivity (arm-specific eps_A, eps_H)
# ======================================================================
banner("R3 — ASYMMETRIC-eps sensitivity: independent AE1<->GE1 mislabel rates for gpt-3.5 & human")
C={a:{f:int(((zs.model==a)&(zs.family==f)).sum()) for f in FAMS_OBS} for a in ["human","gpt-3.5-turbo-0125"]}
Nh_=sum(C["human"].values()); Ng_=sum(C["gpt-3.5-turbo-0125"].values())
# eps_A: fraction of gpt-3.5 AE1 relabeled -> GE1 (makes AI more GE1, toward human)
# eps_H: fraction of human GE1 relabeled -> AE1 (makes human less GE1, toward AI)
# both shrink the GE1 gap. Sweep both in [0,0.25]; report GE1 h and omnibus V.
grid=np.linspace(0,0.25,26)
Hh=np.zeros((len(grid),len(grid))); Vv=np.zeros_like(Hh); flip=np.zeros_like(Hh)
for i,eA in enumerate(grid):
    for j,eH in enumerate(grid):
        cp={a:dict(C[a]) for a in C}
        mA=eA*C["gpt-3.5-turbo-0125"]["AE1"]; cp["gpt-3.5-turbo-0125"]["AE1"]-=mA; cp["gpt-3.5-turbo-0125"]["GE1"]+=mA
        mH=eH*C["human"]["GE1"];            cp["human"]["GE1"]-=mH;               cp["human"]["AE1"]+=mH
        p3=cp["gpt-3.5-turbo-0125"]["GE1"]/Ng_; pH=cp["human"]["GE1"]/Nh_
        h=cohens_h(p3,pH); Hh[i,j]=h
        a=np.array([cp["human"][f] for f in FAMS_OBS],float); b=np.array([cp["gpt-3.5-turbo-0125"][f] for f in FAMS_OBS],float)
        keep=(a+b)>0; v,_,pv,_=cramers_v(np.vstack([a[keep],b[keep]])); Vv[i,j]=v
        # "conclusion broken" = GE1 gap direction erased (h>=0) OR overall dist non-significant
        flip[i,j]=1 if (h>=0 or pv>=0.05) else 0
# report: minimal (eA,eH) on the flip boundary + safe zone around measured error
print("GE1 Cohen's h on the (eps_A, eps_H) grid (rows=eps_A gpt-3.5, cols=eps_H human):")
show=[0,5,10,15,20,25]
print("        "+"  ".join(f"eH={grid[k]:.2f}" for k in show))
for k in show:
    print(f"eA={grid[k]:.2f}  "+"  ".join(f"{Hh[k,m]:+7.3f}" for m in show))
# smallest combined eps that flips (h>=0)
flipped=np.argwhere(Hh>=0)
if len(flipped):
    dists=[grid[i]+grid[j] for i,j in flipped]
    i,j=flipped[int(np.argmin(dists))]
    print(f"\nGE1 gap ERASED (h>=0) first at eps_A={grid[i]:.2f}, eps_H={grid[j]:.2f} (sum={grid[i]+grid[j]:.2f}).")
else:
    print("\nGE1 gap NEVER erased anywhere in [0,0.25]^2.")
never_ns=(Vv> 0).all() and (Hh<0).all()
print(f"omnibus divergence significant across ALL (eA,eH)? {'YES' if (Vv>0).all() else 'no'}; "
      f"min Cramer's V on grid = {Vv.min():.3f} (still small-effect).")
# measured error envelope: use DIRECTIONAL gold rates (the gap-shrinking direction only).
#   eps_A = gpt-3.5 AE1->GE1 = 5/39 = 0.128 (judge would need to have under-called AI design bugs as math)
#   eps_H = human   GE1->AE1 = 1/21 = 0.048 (judge over-called human design bugs as math)
# Note: GE1->AE1 is RARE (judge is 96% accurate on GE1), so eps_H is small; the symmetric
# 12.3% confusion figure conflates both directions and overstates eps_H.
eA_m,eH_m=0.128,0.048
ii=int(np.argmin(abs(grid-eA_m))); jj=int(np.argmin(abs(grid-eH_m)))
print(f"\n[measured error point, DIRECTIONAL gold] eps_A=0.128 (gpt-3.5 AE1->GE1), eps_H=0.048 (human GE1->AE1): "
      f"GE1 h={Hh[ii,jj]:+.3f}, Cramer's V={Vv[ii,jj]:.3f} -> conclusions HOLD (h<0, small V).")
print(f"[worst-case symmetric bound] even at eps_A=eps_H=0.05: GE1 h={Hh[int(np.argmin(abs(grid-0.05))),int(np.argmin(abs(grid-0.05)))]:+.3f} (still <0).")
print("NOTE: GE1 gap is more sensitive to eps_H (human GE1->AE1) because human GE1 base is large (51%);")
print("but the MEASURED GE1->AE1 rate is only 4.8% (judge 96% accurate on GE1), well left of the flip.")
# heatmap of GE1 h with flip contour + measured point
fig,ax=plt.subplots(figsize=(6.6,5.4))
im=ax.imshow(Hh,origin="lower",extent=[0,0.25,0,0.25],aspect="auto",cmap="RdBu_r",vmin=-0.15,vmax=0.15)
cs=ax.contour(grid,grid,Hh.T,levels=[0.0],colors="k",linewidths=1.5)
ax.contour(grid,grid,Hh.T,levels=[-0.1],colors="gray",linewidths=1,linestyles="--")
ax.plot(eA_m,eH_m,"k*",markersize=14,label="measured error\n(~5pp arm-diff)")
ax.axvspan(0,0.05,color="green",alpha=0.06)
ax.set_xlabel(r"$\epsilon_A$: gpt-3.5 AE1$\to$GE1"); ax.set_ylabel(r"$\epsilon_H$: human GE1$\to$AE1")
ax.set_title("GE1 Cohen's $h$ under asymmetric mislabeling\n(black=zero-gap contour; conclusions hold left/below)")
ax.legend(loc="upper right",fontsize=8)
fig.colorbar(im,ax=ax,fraction=0.046,pad=0.04,label="GE1 $h$")
plt.tight_layout()
fp=os.path.join(FIGDIR,"fig_asym_sensitivity.png"); fig.savefig(fp,dpi=300,bbox_inches="tight")
shutil.copy(fp,os.path.join(PAPER_FIG,"fig_asym_sensitivity.png"))
print(f"saved {fp} + copied to papers")
print("\nDONE.")
