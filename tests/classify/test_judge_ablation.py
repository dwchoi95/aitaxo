from src.classify.judge_ablation import _prf


def test_prf_primary_vs_set_view():
    # single-leaf predictions never over-predict -> precision 1 when correct
    prim = [({"GE1.1"}, {"GE1.1"}), ({"AE3.2"}, {"AE3.2"}), ({"GE4.2"}, {"GE1.1"})]
    m = _prf(prim)
    assert m["precision"] == round(2/3, 3) and m["avg_pred_leaves"] == 1.0
    # set view with an extra leaf lowers precision
    s = _prf([({"GE1.1", "GE1.2"}, {"GE1.1"})])
    assert s["precision"] == 0.5 and s["recall"] == 1.0
