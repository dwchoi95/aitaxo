#!/usr/bin/env python
"""
Review v3 addendum: W1 (CE cause distribution), W4 (GE4/GE6 controlled exact test),
W3 (TOST equivalence). Inputs read-only; git untouched.

Sources:
  data/classifications/full.csv          judge labels (zero_shot CE == GE5.1)
  data/problems/<id>/{human|ai/<model>}/incorrect.jsonl   source by row idx
  config.yaml -> g++-16 -O2 -std=gnu++17 -include cassert   (exact harness flags)

Seeds: np.random.seed(20260701).
W1 recompiles the 424 zero_shot CE sources with the harness compiler and
categorizes the FIRST g++ diagnostic; also reports a purely-static
missing-include heuristic. Outputs a per-arm cause table + bar figure
analysis/figures/fig_ce_causes.png (copied to papers).
"""
import os, re, json, subprocess, tempfile, numpy as np, pandas as pd
from scipy import stats
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter

np.random.seed(20260701)
REPO="/Users/cdw/VSCode/aitaxo"; CLS=f"{REPO}/data/classifications"
FIGDIR=f"{REPO}/analysis/figures"; PAPER_FIG="/Users/cdw/VSCode/papers/aitaxo/figures"
GPP="/opt/homebrew/bin/g++-16"; STD="gnu++17"
ARMS=["human","gpt-3.5-turbo-0125","gpt-5.4-nano"]; ALAB={"human":"human","gpt-3.5-turbo-0125":"gpt-3.5","gpt-5.4-nano":"gpt-5.4-nano"}

def primary_leaf(x): return np.nan if pd.isna(x) else str(x).split(",")[0].strip()
def banner(t): print("\n"+"="*80+f"\n{t}\n"+"="*80)

full=pd.read_csv(os.path.join(CLS,"full.csv"))
full["leaf"]=full["labels"].map(primary_leaf)
full["family"]=full["leaf"].map(lambda l: np.nan if pd.isna(l) else str(l).split(".")[0].strip())

def load_jsonl(p):
    out=[]
    if os.path.exists(p):
        with open(p) as fh:
            for line in fh:
                line=line.strip()
                if line: out.append(json.loads(line))
    return out
def src_for(r):
    pid,m,stg,idx=r["problem_id"],r["model"],r["stage"],int(r["idx"])
    if m=="human": path=f"{REPO}/data/problems/{pid}/human/incorrect.jsonl"
    else: path=f"{REPO}/data/problems/{pid}/ai/{m}/{'reflect' if stg=='reflect' else 'incorrect'}.jsonl"
    arr=load_jsonl(path)
    return arr[idx].get("source") if idx<len(arr) else None

# ======================================================================
# W1 — compile-error cause distribution
# ======================================================================
banner("W1 — COMPILATION-ERROR CAUSE DISTRIBUTION (zero_shot CE = GE5.1)")
ce=full[(full.stage=="zero_shot")&(full.verdict=="CE")].copy()
print(f"zero_shot CE: {len(ce)} | by arm: {ce.model.value_counts().reindex(ARMS).to_dict()}")

# --- static missing-include heuristic ---
# symbol -> required header (competitive C++ common). If symbol used and header (or bits/stdc++) absent.
SYМ={  # noqa
}
SYM={
    "<cmath>": [r"\bpow\b",r"\bsqrt\b",r"\bceil\b",r"\bfloor\b",r"\babs\b\(",r"\bround\b",r"\blog\b",r"\bsin\b",r"\bcos\b"],
    "<vector>":[r"\bvector\s*<"],
    "<algorithm>":[r"\bsort\s*\(",r"\bmax_element",r"\bmin_element",r"\b__gcd",r"\bnext_permutation",r"\blower_bound",r"\bupper_bound"],
    "<map>":[r"\bmap\s*<",r"\bunordered_map\s*<"],
    "<set>":[r"\bset\s*<",r"\bunordered_set\s*<"],
    "<string>":[r"\bstring\b"],
    "<queue>":[r"\bqueue\s*<",r"\bpriority_queue\s*<"],
    "<stack>":[r"\bstack\s*<"],
    "<cstring>":[r"\bmemset\b",r"\bstrlen\b",r"\bmemcpy\b"],
    "<numeric>":[r"\baccumulate\b",r"\bgcd\s*\(",r"\blcm\s*\("],
    "<climits>":[r"\bINT_MAX\b",r"\bINT_MIN\b",r"\bLLONG_MAX\b"],
}
def static_missing_include(src):
    if "<bits/stdc++.h>" in src: return False, None
    body=src
    for hdr,pats in SYM.items():
        if hdr in body: continue
        for p in pats:
            if re.search(p,body):
                return True, hdr+" (uses "+p.strip('\\b()')+")"
    return False, None

# --- real compile with harness flags, categorize first diagnostic ---
def first_error_category(stderr):
    s=stderr
    m=re.search(r":\s*error:\s*(.*)", s)
    msg=m.group(1).strip() if m else ""
    low=msg.lower()
    # --- toolchain/standard drift: names that 2021-era code used but C++20/GCC16 now
    #     occupies (y1/index/gettimeofday/_strrev POSIX/GNU globals; std ranges 'views',
    #     C++20 'midpoint','concept'; ambiguous std symbols; 'long long long' GCC limit;
    #     x86 pragmas on arm64). These compiled on the original judge but not here. ---
    drift_markers=[
        "redeclared as different kind","conflicting declaration","is ambiguous",
        "has not been declared","is too long for gcc","'target(","is not valid",
        "does not name a type; did you mean 'const'","forbids declaration of",
        "with no type [-fpermissive]","-wtemplate-body","must return 'int'"]
    drift_syms=["y1","index","gettimeofday","_strrev","midpoint","views","concept"]
    if any(d in low for d in drift_markers):
        return "toolchain/std drift"
    if "was not declared in this scope" in low and any(f"'{sy}'" in low for sy in drift_syms):
        return "toolchain/std drift"
    # category rules (ordered)
    if "was not declared in this scope" in low or "not declared" in low:
        return "undeclared identifier/typo"
    if "no member named" in low or "has no member" in low or "is not a member of" in low:
        return "no such member/namespace"
    if low.startswith("expected") or ("expected" in low and ("';'" in low or "'}'" in low or "')'" in low or "'{'" in low or "primary-expression" in low or "identifier" in low)):
        return "syntax: missing/unexpected token"
    if "redeclaration" in low or "redefinition" in low:
        return "toolchain/std drift"
    if "no matching function" in low or "cannot convert" in low or "invalid operands" in low or "no match for" in low or "static assertion failed" in low:
        return "type/overload mismatch"
    if "is not captured" in low:
        return "lambda capture"
    if "use of deleted" in low or "no viable" in low:
        return "type/overload mismatch"
    if "ld returned" in low or msg=="" or "(no error" in low:
        return "other/uncategorized"
    return "other/uncategorized"

def compile_first_error(src):
    with tempfile.TemporaryDirectory() as wd:
        p=os.path.join(wd,"main.cpp"); open(p,"w").write(src)
        b=os.path.join(wd,"main.bin")
        try:
            r=subprocess.run([GPP,"-O2",f"-std={STD}","-include","cassert",p,"-o",b],
                             capture_output=True,text=True,timeout=30)
        except subprocess.TimeoutExpired:
            return "compile-timeout","",False
        if r.returncode==0:
            return "COMPILES-OK","",True
        return first_error_category(r.stderr), r.stderr, False

# run on all CE
rows=[]
print("compiling CE sources (this takes a bit)...")
for _,r in ce.iterrows():
    src=src_for(r)
    if src is None:
        rows.append(dict(arm=r.model,cat="<no-source>",static=False,static_hdr=None)); continue
    stat,hdr=static_missing_include(src)
    cat,stderr,ok=compile_first_error(src)
    # refine: if static says missing include AND real error is undeclared -> label as missing-include
    final=cat
    if cat=="undeclared identifier/typo" and stat:
        final="missing #include"
    rows.append(dict(arm=r.model,cat=final,static=stat,static_hdr=hdr,raw_cat=cat,compiles=ok))
W1=pd.DataFrame(rows)

# how many CE actually reproduce as compile-error under harness compiler?
repro=(W1["raw_cat"]!="COMPILES-OK").mean()
print(f"\nCE that re-fail to compile under g++-16 harness flags: {(W1['raw_cat']!='COMPILES-OK').sum()}/{len(W1)} ({repro*100:.1f}%)")
print("(CE that now COMPILE-OK = compiler-version drift; reported as 'compiles-now')")

# arm x category table (%)
W1["catshow"]=W1["cat"].map(lambda c:"compiles-now" if c=="COMPILES-OK" else c)
W1.loc[W1["raw_cat"]=="COMPILES-OK","catshow"]="compiles-now"
order2=["missing #include","undeclared identifier/typo","type/overload mismatch","no such member/namespace",
        "syntax: missing/unexpected token","lambda capture","toolchain/std drift","compiles-now","other/uncategorized"]
W1["catf"]=W1["catshow"].map(lambda c: c if c in order2 else "other/uncategorized")
tab=pd.crosstab(W1["catf"],W1["arm"]).reindex(columns=ARMS).fillna(0).astype(int)
tab=tab.reindex([c for c in order2 if c in tab.index]+[c for c in tab.index if c not in order2])
pct=tab.div(tab.sum(axis=0),axis=1)*100
print("\n[CE cause counts per arm]"); print(tab.to_string())
print("\n[CE cause % per arm]"); print(pct.round(1).to_string())

# static missing-include rate per arm (independent of compiler drift)
print("\n[static missing-#include heuristic — % of CE flagged, per arm]")
for a in ARMS:
    sub=W1[W1.arm==a]; print(f"  {ALAB[a]:14s}: {sub['static'].mean()*100:5.1f}%  (n={len(sub)})  top hdrs: "
          + ", ".join(pd.Series([h for h in sub['static_hdr'].dropna()]).str.replace(r' \(.*','',regex=True).value_counts().head(3).index.tolist()))

# headline: gpt-3.5 vs human missing-include share
mi_h=W1[(W1.arm=='human')&(W1.cat=='missing #include')].shape[0]
mi_3=W1[(W1.arm=='gpt-3.5-turbo-0125')&(W1.cat=='missing #include')].shape[0]
print(f"\n[Missing-#include as a share of CE]  human={mi_h}/{(W1.arm=='human').sum()} "
      f"gpt-3.5={mi_3}/{(W1.arm=='gpt-3.5-turbo-0125').sum()}")

# figure
ARM_COLOR={"human":"#4C72B0","gpt-3.5-turbo-0125":"#DD8452","gpt-5.4-nano":"#55A868"}
present=[c for c in order2 if c in pct.index]
fig,ax=plt.subplots(figsize=(11,4.3))
x=np.arange(len(present)); w=0.26
for k,a in enumerate(ARMS):
    ax.bar(x+(k-1)*w,pct.reindex(present)[a].values,w,label=ALAB[a],color=ARM_COLOR[a])
ax.set_xticks(x); ax.set_xticklabels(present,rotation=25,ha="right",fontsize=8.5)
ax.set_ylabel("% of arm's CE submissions"); ax.set_title("Compilation-error cause (first g++ diagnostic), by arm")
ax.legend(frameon=False); ax.yaxis.set_major_formatter(PercentFormatter(decimals=0)); ax.grid(axis="y",alpha=0.3)
plt.tight_layout()
fp=os.path.join(FIGDIR,"fig_ce_causes.png"); fig.savefig(fp,dpi=300,bbox_inches="tight")
import shutil; shutil.copy(fp,os.path.join(PAPER_FIG,"fig_ce_causes.png"))
print(f"saved {fp} + copied to papers")

# ======================================================================
# W4 — GE4/GE6 controlled estimate on overflow-reachable subset (Firth + exact)
# ======================================================================
banner("W4 — GE4/GE6 controlled: overflow-reachable subset, Firth logistic + Fisher exact")
zs=full[full.stage=="zero_shot"].copy()
ge4_probs=set(zs[(zs.model=='human')&(zs.leaf=='GE4.1')]["problem_id"])
print(f"overflow-reachable subset = {len(ge4_probs)} problems (>=1 human GE4.1)")

def fisher_and_rr(fam):
    sub=zs[zs.problem_id.isin(ge4_probs)].copy()
    sub["isf"]=(sub.family==fam).astype(int)
    H=sub[sub.model=="human"]; A=sub[sub.model=="gpt-3.5-turbo-0125"]
    xH,nH=int(H.isf.sum()),len(H); xA,nA=int(A.isf.sum()),len(A)
    # 2x2: rows=arm(human,gpt35), cols=(fam, notfam)
    table=[[xH,nH-xH],[xA,nA-xA]]
    OR,p=stats.fisher_exact(table)  # OR = human-odds / gpt35-odds by scipy convention (a*d/b*c)
    # exact CI for OR via the conditional (use statsmodels Table2x2 if available)
    try:
        import statsmodels.stats.contingency_tables as ct
        t=ct.Table2x2(np.array(table))
        orr=t.oddsratio; lo,hi=t.oddsratio_confint()
    except Exception:
        orr,lo,hi=OR,np.nan,np.nan
    # rate ratio human/gpt35 with log CI (add 0.5 if zero)
    pH=xH/nH; pA=xA/nA
    rr=pH/pA if pA>0 else np.inf
    # Katz log-RR CI
    a,b,c,dd=xH,nH-xH,xA,nA-xA
    if xH>0 and xA>0:
        se=np.sqrt(1/a-1/nH+1/c-1/nA); rrlo=np.exp(np.log(rr)-1.96*se); rrhi=np.exp(np.log(rr)+1.96*se)
    else:
        rrlo=rrhi=np.nan
    return dict(fam=fam,xH=xH,nH=nH,pH=pH*100,xA=xA,nA=nA,pA=pA*100,
                OR_HvsA=orr,OR_lo=lo,OR_hi=hi,p_fisher=p,RR_HvsA=rr,RR_lo=rrlo,RR_hi=rrhi)

# Firth logistic (penalized) — implement via statsmodels GLM with Jeffreys penalty fallback to firthlogist if available
def firth_or(fam):
    sub=zs[zs.problem_id.isin(ge4_probs)].copy()
    sub=sub[sub.model.isin(["human","gpt-3.5-turbo-0125"])].copy()
    sub["y"]=(sub.family==fam).astype(int)
    sub["is_ai"]=(sub.model=="gpt-3.5-turbo-0125").astype(int)
    try:
        from firthlogist import FirthLogisticRegression
        X=sub[["is_ai"]].values; yv=sub["y"].values
        m=FirthLogisticRegression().fit(X,yv)
        beta=m.coef_[0]; ci=m.ci_  # may not exist
        return np.exp(beta), None, None, "firthlogist"
    except Exception:
        return None,None,None,"firth-unavailable"

for fam in ["GE4","GE6"]:
    d=fisher_and_rr(fam)
    print(f"\n[{fam}] subset: human={d['xH']}/{d['nH']}={d['pH']:.2f}%  gpt-3.5={d['xA']}/{d['nA']}={d['pA']:.2f}%")
    print(f"   Fisher exact OR(human vs gpt-3.5)={d['OR_HvsA']:.2f} [{d['OR_lo']:.2f}, {d['OR_hi']:.2f}]  p={d['p_fisher']:.2e}")
    rr=d['RR_HvsA']; print(f"   Rate ratio human/gpt-3.5 = {rr:.2f}" + (f" [{d['RR_lo']:.2f}, {d['RR_hi']:.2f}]" if not np.isnan(d['RR_lo']) else " (CI NA: zero cell)"))
    orr,_,_,note=firth_or(fam);
    if orr is not None: print(f"   Firth penalized OR(ai vs human)={orr:.3f}  ({note})")
    else: print(f"   Firth: {note} (Fisher exact is the primary controlled estimate)")

# ======================================================================
# W3 — TOST equivalence (Cohen's h, SESOI 0.2 and 0.1)
# ======================================================================
banner("W3 — TOST equivalence on Cohen's h (gpt-3.5 vs human, full corpus zero_shot)")
N={a:int((zs.model==a).sum()) for a in ARMS}
def cohens_h(p1,p2): return 2*np.arcsin(np.sqrt(p1))-2*np.arcsin(np.sqrt(p2))
FAMS=[f for f in ["GE1","GE2","GE3","GE4","GE5","GE6","AE1","AE2","AE5"]]
def tost(fam,sesoi):
    xA=int(((zs.model=='gpt-3.5-turbo-0125')&(zs.family==fam)).sum()); nA=N['gpt-3.5-turbo-0125']
    xH=int(((zs.model=='human')&(zs.family==fam)).sum()); nH=N['human']
    pA,pH=xA/nA,xH/nH
    h=cohens_h(pA,pH); se=np.sqrt(1/nA+1/nH)
    # two one-sided z-tests: H0a: h<=-sesoi ; H0b: h>=+sesoi. equivalence if both rejected.
    z_lo=(h-(-sesoi))/se; p_lo=1-stats.norm.cdf(z_lo)   # test h > -sesoi
    z_hi=((sesoi)-h)/se;  p_hi=1-stats.norm.cdf(z_hi)   # test h < +sesoi
    p_tost=max(p_lo,p_hi)
    # also conventional 2-sided test vs 0
    z0=h/se; p0=2*(1-stats.norm.cdf(abs(z0)))
    return h,se,p_tost,p0
for sesoi in [0.2,0.1]:
    print(f"\n--- SESOI = +/-{sesoi} (equivalence bound on |h|) ---")
    print(f"{'fam':4s} {'h':>7s} {'90%CI':>18s} {'TOST p':>9s} {'2sided p':>10s}  verdict")
    for f in FAMS:
        h,se,ptost,p0=tost(f,sesoi)
        lo90,hi90=h-1.645*se,h+1.645*se
        equiv = ptost<0.05
        diff  = p0<0.05
        if equiv and not diff: verdict="EQUIVALENT (smaller than SESOI, not distinct from 0)"
        elif equiv and diff:   verdict="real-but-tiny (sig != 0 AND |h|<SESOI)"
        elif (not equiv) and diff: verdict="DISTINCT, not bounded < SESOI"
        else: verdict="inconclusive"
        print(f"{f:4s} {h:+7.3f} [{lo90:+.3f},{hi90:+.3f}] {ptost:9.1e} {p0:10.1e}  {verdict}")
print("\nDONE.")
