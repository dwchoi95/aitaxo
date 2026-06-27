from src.analysis.stats import (cohen_h, collapse_sparse, cramers_v,
                                two_proportion_tests)


def test_cohen_h_zero_when_equal():
    assert cohen_h(0.5, 0.5) == 0.0
    assert cohen_h(0.1, 0.9) > 1.5


def test_cramers_v_range():
    assert 0.0 <= cramers_v([[10, 0], [0, 10]]) <= 1.0
    assert cramers_v([[5, 5], [5, 5]]) < 1e-9


def test_two_proportion_tests_bh_and_effect():
    per_leaf = {"GE4.2": (90, 10), "AE3.2": (50, 50)}
    rows = two_proportion_tests(per_leaf, 100, 100)
    r = {x["leaf"]: x for x in rows}
    assert r["GE4.2"]["q_value"] <= 1.0 and "significant" in r["GE4.2"]
    assert r["GE4.2"]["cohen_h"] > r["AE3.2"]["cohen_h"]   # bigger gap -> bigger effect


def test_collapse_sparse_rolls_up_rare_leaves():
    per_leaf = {"GE4.1": (2, 1), "GE4.2": (50, 40)}
    out = collapse_sparse(per_leaf, 100, 100, min_expected=5)
    assert "GE4" in out and out["GE4"] == (2, 1)           # rare leaf rolled to family
    assert out["GE4.2"] == (50, 40)
