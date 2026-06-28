import json
import warnings
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import statsmodels.api as sm  # noqa: E402
import statsmodels.formula.api as smf  # noqa: E402

from src.analysis.stats import chi2_or_fisher, collapse_sparse, cramers_v, two_proportion_tests  # noqa: E402


class RqAnalysis:
    # Phase G: turn a classification jsonl into the RQ1-RQ3 tables and figures. Every number is
    # script-generated into results/. Built to run on real or synthetic labels identically.
    def __init__(self, config):
        self.config = config
        self.art = Path(config["paths"]["artifacts"])
        self.results = Path(config["paths"]["results"])
        self.problems = Path(config["paths"]["data"]) / "problems"
        self.alpha = config["stats"]["alpha"]
        self.arms = ("human", "ai_zero_shot")

    def run(self, classifications_path, rq3_path=None):
        df = self._load(classifications_path)
        fam = self._family_df(df)
        rq1_leaf = self.rq1(df, "leaf")
        rq1_fam = self.rq1(fam, "family")                  # FAMILY = primary granularity
        rq2_fam = self.rq2(fam, "family")
        rq2_leaf = self.rq2(df, "leaf")
        self.figure_frequencies(rq1_leaf["per_cat"], "leaf")
        self.figure_frequencies(rq1_fam["per_cat"], "family")
        sat = self.saturation(df)
        dist = self.distributions(df)
        rq3 = self.rq3(rq3_path) if rq3_path else None
        summary = {"submissions": len(df), "arms": {a: int((df.arm == a).sum()) for a in self.arms},
                   "rq1_family_overall": rq1_fam["overall"], "rq1_family_significant": rq1_fam["n_significant"],
                   "rq1_leaf_overall": rq1_leaf["overall"], "rq1_leaf_significant": rq1_leaf["n_significant"],
                   "rq2_family_models": rq2_fam["n_models"], "rq2_leaf_models": rq2_leaf["n_models"],
                   "saturation": sat, "distributions_categories": dist, "rq3": rq3}
        self._summary_md(summary, rq1_fam, rq1_leaf)
        return summary

    def _tables(self):
        d = self.results / "tables"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def _figures(self):
        d = self.results / "figures"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def _load(self, path):
        recs = [json.loads(l) for l in Path(path).read_text(encoding="utf-8").split("\n") if l]
        meta = {}
        for r in recs:
            pid = r["problem_id"]
            if pid not in meta:
                m = json.loads((self.problems / pid / "meta.json").read_text(encoding="utf-8"))
                fams = m.get("algo_families") or []
                meta[pid] = (m["difficulty_bin"], fams[0] if fams else "other")
        rows = []
        for r in recs:
            if r["arm"] not in self.arms:
                continue
            diff, fam = meta[r["problem_id"]]
            rows.append({"submission_id": r["submission_id"], "problem_id": r["problem_id"],
                         "arm": r["arm"], "is_ai": int(r["arm"] != "human"), "verdict": r["verdict"],
                         "difficulty_bin": diff, "family": fam, "leaves": list(r.get("leaves", []))})
        return pd.DataFrame(rows)

    def _family_df(self, df):
        d = df.copy()
        d["leaves"] = d.leaves.apply(lambda xs: sorted({x.split(".")[0] for x in xs}))
        return d

    def rq1(self, df, tag="leaf", collapse=True):
        n_a = int((df.arm == "human").sum())
        n_b = int((df.arm == "ai_zero_shot").sum())
        cats = sorted({l for ls in df.leaves for l in ls})
        per_cat = {}
        for c in cats:
            ca = int(df[df.arm == "human"].leaves.apply(lambda x: c in x).sum())
            cb = int(df[df.arm == "ai_zero_shot"].leaves.apply(lambda x: c in x).sum())
            per_cat[c] = (ca, cb)
        tested = collapse_sparse(per_cat, n_a, n_b) if collapse else per_cat
        rows = two_proportion_tests(tested, n_a, n_b, self.alpha)
        table = [[c[0] for c in per_cat.values()], [c[1] for c in per_cat.values()]]
        overall = chi2_or_fisher(table) if len(per_cat) > 1 else {"test": "n/a"}
        overall["cramers_v"] = cramers_v(table) if len(per_cat) > 1 else 0.0
        pd.DataFrame(rows).to_csv(self._tables() / f"rq1_{tag}_frequencies.csv", index=False)
        return {"per_cat": per_cat, "rows": rows, "overall": overall,
                "n_significant": sum(1 for r in rows if r.get("significant"))}

    def rq2(self, df, tag="leaf", min_positives=15):
        cats = sorted({l for ls in df.leaves for l in ls})
        out = []
        for c in cats:
            d = df.copy()
            d["y"] = d.leaves.apply(lambda x: int(c in x))
            if d.y.sum() < min_positives or d.y.sum() > len(d) - min_positives:
                continue
            res = self._clustered_logit(d)
            if res:
                out.append({"category": c, **res})
        pd.DataFrame(out).to_csv(self._tables() / f"rq2_{tag}_adjusted.csv", index=False)
        return {"rows": out, "n_models": len(out)}

    def _clustered_logit(self, d):
        # problem-clustered logistic via GEE (exchangeable working correlation, groups=problem)
        formula = "y ~ is_ai + C(difficulty_bin) + C(family)"
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                model = smf.gee(formula, "problem_id", data=d, family=sm.families.Binomial(),
                                cov_struct=sm.cov_struct.Exchangeable())
                res = model.fit()
            coef = float(res.params.get("is_ai", float("nan")))
            separated = abs(coef) > 15  # quasi-complete separation (e.g. arm-exclusive leaf)
            return {"ai_coef": coef,
                    "ai_odds_ratio": float("inf") if separated else float(np.exp(coef)),
                    "ai_p_value": float(res.pvalues.get("is_ai", float("nan"))),
                    "separated": separated, "n": int(len(d))}
        except Exception:
            return None

    def rq3(self, rq3_classifications_path):
        # one file, arm = ai_reflection_turn0 / ai_reflection_residual; compare distributions
        recs = [json.loads(l) for l in Path(rq3_classifications_path).read_text(encoding="utf-8").split("\n") if l]
        for level in ("leaf", "family"):
            t0 = self._freq([r for r in recs if r["arm"].endswith("turn0")], level)
            res = self._freq([r for r in recs if r["arm"].endswith("residual")], level)
            cats = sorted(set(t0) | set(res))
            rows = [{"category": c, "turn0": t0.get(c, 0), "residual": res.get(c, 0),
                     "fixed": t0.get(c, 0) - res.get(c, 0)} for c in cats]
            pd.DataFrame(rows).to_csv(self._tables() / f"rq3_persistence_{level}.csv", index=False)
        return {"turn0": sum(self._freq([r for r in recs if r["arm"].endswith("turn0")], "leaf").values()),
                "residual": sum(self._freq([r for r in recs if r["arm"].endswith("residual")], "leaf").values())}

    def _freq(self, recs, level):
        out = {}
        for r in recs:
            for leaf in r.get("leaves", []):
                c = leaf.split(".")[0] if level == "family" else leaf
                out[c] = out.get(c, 0) + 1
        return out

    def saturation(self, df):
        # RQ1 sample-size validity: cumulative distinct leaves vs number of AI zero-shot samples
        ai = df[df.arm == "ai_zero_shot"].reset_index(drop=True)
        seen, curve = set(), []
        for _, row in ai.iterrows():
            seen |= set(row["leaves"])
            curve.append(len(seen))
        pd.DataFrame({"n_samples": range(1, len(curve) + 1), "distinct_leaves": curve}).to_csv(
            self._tables() / "rq1_saturation.csv", index=False)
        fig, ax = plt.subplots(figsize=(5, 3.2))
        ax.plot(range(1, len(curve) + 1), curve)
        ax.set_xlabel("AI zero-shot samples")
        ax.set_ylabel("distinct leaves seen")
        fig.tight_layout()
        fig.savefig(self._figures() / "rq1_saturation.pdf")
        plt.close(fig)
        return {"final_distinct": curve[-1] if curve else 0, "still_rising": bool(curve and curve[-1] > (curve[-2] if len(curve) > 1 else 0))}

    def distributions(self, df):
        # per-arm leaf and family frequency tables
        out = {}
        for level in ("leaf", "family"):
            ld = df if level == "leaf" else self._family_df(df)
            cats = sorted({l for ls in ld.leaves for l in ls})
            rows = []
            for c in cats:
                row = {"category": c}
                for arm in self.arms:
                    sub = ld[ld.arm == arm]
                    row[arm] = int(sub.leaves.apply(lambda x: c in x).sum())
                    row[f"{arm}_pct"] = round(100 * row[arm] / max(1, len(sub)), 1)
                rows.append(row)
            pd.DataFrame(rows).to_csv(self._tables() / f"dist_{level}_by_arm.csv", index=False)
            out[level] = len(cats)
        return out

    def figure_frequencies(self, per_cat, tag):
        cats = sorted(per_cat)
        ha = [per_cat[c][0] for c in cats]
        ai = [per_cat[c][1] for c in cats]
        x = range(len(cats))
        fig, ax = plt.subplots(figsize=(max(6, len(cats) * 0.4), 4))
        ax.bar([i - 0.2 for i in x], ha, width=0.4, label="human")
        ax.bar([i + 0.2 for i in x], ai, width=0.4, label="AI")
        ax.set_xticks(list(x))
        ax.set_xticklabels(cats, rotation=90, fontsize=6)
        ax.set_ylabel("submissions with category")
        ax.legend()
        fig.tight_layout()
        fig.savefig(self._figures() / f"rq1_{tag}_frequencies.pdf")
        plt.close(fig)

    def _summary_md(self, summary, rq1_fam, rq1_leaf):
        def sig_rows(rq, k=12):
            sig = sorted([r for r in rq["rows"] if r.get("significant")],
                         key=lambda r: r.get("q_value", 1))[:k]
            return [f"  {r['leaf']}: human {r['prop_a']:.3f} vs AI {r['prop_b']:.3f}  "
                    f"(h={r['cohen_h']:.2f}, q={r.get('q_value', 1):.3g})" for r in sig]
        lines = ["# Results summary (script-generated; FAMILY is primary, leaf exploratory)", "",
                 f"Submissions: {summary['submissions']} "
                 f"(human {summary['arms'].get('human', 0)}, AI {summary['arms'].get('ai_zero_shot', 0)})",
                 "Between-arm differences are conservative lower bounds (non-differential judge error).", "",
                 "## RQ1 FAMILY (primary)",
                 f"overall: {summary['rq1_family_overall']}",
                 f"families significant after BH-FDR: {summary['rq1_family_significant']}",
                 *sig_rows(rq1_fam), "",
                 "## RQ1 leaf (exploratory)",
                 f"overall: {summary['rq1_leaf_overall']}",
                 f"leaves significant after BH-FDR: {summary['rq1_leaf_significant']}",
                 *sig_rows(rq1_leaf), "",
                 f"## RQ2 problem-clustered models: family {summary['rq2_family_models']}, "
                 f"leaf {summary['rq2_leaf_models']} (see rq2_*_adjusted.csv)",
                 f"## Saturation: {summary['saturation']}",
                 f"## Distributions: dist_leaf_by_arm.csv, dist_family_by_arm.csv",
                 f"## RQ3 persistence: {summary['rq3']} (see rq3_persistence_*.csv)", ""]
        self.results.mkdir(parents=True, exist_ok=True)
        (self.results / "SUMMARY.md").write_text("\n".join(lines), encoding="utf-8")
