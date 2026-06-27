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

    def run(self, classifications_path, residual_path=None, turn0_path=None):
        df = self._load(classifications_path)
        rq1 = self.rq1(df)
        rq2 = self.rq2(df)
        self.figure_leaf_frequencies(rq1["per_leaf"])
        rq3 = self.rq3(residual_path, turn0_path) if residual_path and turn0_path else None
        summary = {"submissions": len(df), "arms": {a: int((df.arm == a).sum()) for a in self.arms},
                   "rq1_overall": rq1["overall"], "rq1_significant_leaves": rq1["n_significant"],
                   "rq2_models": rq2["n_models"], "rq3": rq3}
        self._summary_md(summary, rq1)
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

    def rq1(self, df, collapse=True):
        n_a = int((df.arm == "human").sum())
        n_b = int((df.arm == "ai_zero_shot").sum())
        leaves = sorted({l for ls in df.leaves for l in ls})
        per_leaf = {}
        for leaf in leaves:
            ca = int(df[df.arm == "human"].leaves.apply(lambda x: leaf in x).sum())
            cb = int(df[df.arm == "ai_zero_shot"].leaves.apply(lambda x: leaf in x).sum())
            per_leaf[leaf] = (ca, cb)
        tested = collapse_sparse(per_leaf, n_a, n_b) if collapse else per_leaf
        rows = two_proportion_tests(tested, n_a, n_b, self.alpha)
        table = [[c[0] for c in per_leaf.values()], [c[1] for c in per_leaf.values()]]
        overall = chi2_or_fisher(table) if len(per_leaf) > 1 else {"test": "n/a"}
        overall["cramers_v"] = cramers_v(table) if len(per_leaf) > 1 else 0.0
        pd.DataFrame(rows).to_csv(self._tables() / "rq1_leaf_frequencies.csv", index=False)
        return {"per_leaf": per_leaf, "rows": rows, "overall": overall,
                "n_significant": sum(1 for r in rows if r.get("significant"))}

    def rq2(self, df, min_positives=15):
        leaves = sorted({l for ls in df.leaves for l in ls})
        out = []
        for leaf in leaves:
            d = df.copy()
            d["y"] = d.leaves.apply(lambda x: int(leaf in x))
            if d.y.sum() < min_positives or d.y.sum() > len(d) - min_positives:
                continue
            res = self._clustered_logit(d)
            if res:
                out.append({"leaf": leaf, **res})
        pd.DataFrame(out).to_csv(self._tables() / "rq2_adjusted_associations.csv", index=False)
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

    def rq3(self, residual_path, turn0_path):
        res = self._leaf_freq(residual_path)
        t0 = self._leaf_freq(turn0_path)
        leaves = sorted(set(res) | set(t0))
        rows = [{"leaf": l, "turn0": t0.get(l, 0), "residual": res.get(l, 0),
                 "fixed": t0.get(l, 0) - res.get(l, 0)} for l in leaves]
        pd.DataFrame(rows).to_csv(self._tables() / "rq3_persistence.csv", index=False)
        return {"leaves": len(leaves), "turn0_total": sum(t0.values()), "residual_total": sum(res.values())}

    def _leaf_freq(self, path):
        recs = [json.loads(l) for l in Path(path).read_text(encoding="utf-8").split("\n") if l]
        out = {}
        for r in recs:
            for leaf in r.get("leaves", []):
                out[leaf] = out.get(leaf, 0) + 1
        return out

    def figure_leaf_frequencies(self, per_leaf):
        n_a = max(1, sum(c[0] for c in per_leaf.values()))
        n_b = max(1, sum(c[1] for c in per_leaf.values()))
        leaves = sorted(per_leaf)
        ha = [per_leaf[l][0] for l in leaves]
        ai = [per_leaf[l][1] for l in leaves]
        x = range(len(leaves))
        fig, ax = plt.subplots(figsize=(max(6, len(leaves) * 0.4), 4))
        ax.bar([i - 0.2 for i in x], ha, width=0.4, label="human")
        ax.bar([i + 0.2 for i in x], ai, width=0.4, label="AI")
        ax.set_xticks(list(x))
        ax.set_xticklabels(leaves, rotation=90, fontsize=6)
        ax.set_ylabel("submissions with leaf")
        ax.legend()
        fig.tight_layout()
        fig.savefig(self._figures() / "rq1_leaf_frequencies.pdf")
        plt.close(fig)

    def _summary_md(self, summary, rq1):
        lines = ["# Results summary (script-generated)", "",
                 f"Submissions: {summary['submissions']} (human {summary['arms'].get('human', 0)}, "
                 f"AI {summary['arms'].get('ai_zero_shot', 0)})", "",
                 f"RQ1 overall: {summary['rq1_overall']}", "",
                 f"RQ1 leaves significant after BH-FDR: {summary['rq1_significant_leaves']}", "",
                 f"RQ2 clustered models fit: {summary['rq2_models']}", ""]
        if summary.get("rq3"):
            lines += [f"RQ3: {summary['rq3']}", ""]
        self.results.mkdir(parents=True, exist_ok=True) or (self.results / "SUMMARY.md").write_text("\n".join(lines), encoding="utf-8")
