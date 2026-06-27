import math

import numpy as np
from scipy import stats
from statsmodels.stats.multitest import multipletests

# Statistical primitives for RQ1/RQ2. Pure functions over counts/tables so they are unit-
# testable without any model output.


def cohen_h(p1, p2):
    # effect size for the difference between two proportions
    return abs(2 * math.asin(math.sqrt(p1)) - 2 * math.asin(math.sqrt(p2)))


def cramers_v(table):
    table = np.asarray(table, dtype=float)
    chi2 = stats.chi2_contingency(table, correction=False)[0]
    n = table.sum()
    r, k = table.shape
    denom = n * (min(r, k) - 1)
    return math.sqrt(chi2 / denom) if denom > 0 else 0.0


def chi2_or_fisher(table):
    # Fisher's exact for 2x2 (exact, robust to small cells); chi-square otherwise
    table = np.asarray(table, dtype=float)
    if table.shape == (2, 2):
        odds, p = stats.fisher_exact(table)
        return {"test": "fisher_exact", "statistic": float(odds), "p_value": float(p)}
    chi2, p, dof, _ = stats.chi2_contingency(table, correction=False)
    return {"test": "chi2", "statistic": float(chi2), "p_value": float(p), "dof": int(dof)}


def two_proportion_tests(per_leaf, n_a, n_b, alpha=0.05):
    # per_leaf: {leaf: (count_in_a, count_in_b)}; one 2x2 Fisher test per leaf, then BH-FDR
    rows, pvals = [], []
    for leaf, (ca, cb) in sorted(per_leaf.items()):
        table = [[ca, n_a - ca], [cb, n_b - cb]]
        res = chi2_or_fisher(table)
        pa, pb = ca / n_a if n_a else 0.0, cb / n_b if n_b else 0.0
        rows.append({"leaf": leaf, "count_a": ca, "count_b": cb, "prop_a": pa, "prop_b": pb,
                     "cohen_h": cohen_h(pa, pb), "p_value": res["p_value"]})
        pvals.append(res["p_value"])
    if pvals:
        reject, q, _, _ = multipletests(pvals, alpha=alpha, method="fdr_bh")
        for row, r, qv in zip(rows, reject, q):
            row["q_value"] = float(qv)
            row["significant"] = bool(r)
    return rows


def collapse_sparse(per_leaf, n_a, n_b, min_expected=5):
    # collapse a leaf to its family only when its *expected* leaf-present cell count is below
    # min_expected (total occurrences too few for a valid test). An arm-exclusive leaf with
    # many occurrences in one arm (e.g. 80 vs 0) is NOT sparse and is kept — it is the finding.
    total = n_a + n_b
    kept, collapsed = {}, {}
    for leaf, (ca, cb) in per_leaf.items():
        expected_present = (ca + cb) * min(n_a, n_b) / total if total else 0.0
        if expected_present < min_expected:
            fam = leaf.split(".")[0]
            c = collapsed.setdefault(fam, [0, 0])
            c[0] += ca
            c[1] += cb
        else:
            kept[leaf] = (ca, cb)
    kept.update({f: tuple(v) for f, v in collapsed.items()})
    return kept
