import pandas as pd
from src.analysis.rq_analysis import RqAnalysis
from src.common.config import Config


def _synthetic():
    rows = []
    for p in range(20):
        for i in range(8):
            rows.append({"submission_id": f"human:{p}:{i}", "problem_id": f"p{p}", "arm": "human",
                         "is_ai": 0, "verdict": "WA", "difficulty_bin": "easy" if p % 2 else "hard",
                         "family": "AE3" if p % 3 else "AE1", "leaves": ["GE4.2"] if i % 2 else ["AE3.2"]})
            rows.append({"submission_id": f"ai:{p}:{i}", "problem_id": f"p{p}", "arm": "ai_zero_shot",
                         "is_ai": 1, "verdict": "WA", "difficulty_bin": "easy" if p % 2 else "hard",
                         "family": "AE3" if p % 3 else "AE1", "leaves": ["GE2.1"] if i % 2 else ["AE3.2"]})
    return pd.DataFrame(rows)


def test_rq1_and_rq2_run_on_synthetic():
    a = RqAnalysis(Config())
    df = _synthetic()
    r1 = a.rq1(df, "leaf")
    assert r1["overall"]["p_value"] < 0.05            # human GE4.2 vs AI GE2.1 differ
    assert any(row["leaf"] in ("GE4.2", "GE2.1") for row in r1["rows"])
    rfam = a.rq1(a._family_df(df), "family")          # family collapses GE4.2/GE2.1 -> GE4/GE2
    assert any(row["leaf"] in ("GE4", "GE2", "AE3") for row in rfam["rows"])
    r2 = a.rq2(df, "leaf", min_positives=10)
    assert r2["n_models"] >= 1
    a.figure_frequencies(r1["per_cat"], "leaf")
    assert (a.results / "figures" / "rq1_leaf_frequencies.pdf").exists()
    assert a.saturation(df)["final_distinct"] >= 1
    assert a.distributions(df)["family"] >= 1
