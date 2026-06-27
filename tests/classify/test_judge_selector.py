from src.common.config import Config
from src.classify.judge_selector import JudgeSelector


def test_agreement_metrics():
    js = JudgeSelector(Config())
    preds = [{"predicted": ["GE4.2"], "gold": ["GE4.2"]},          # exact
             {"predicted": ["AE3.2", "GE6.1"], "gold": ["AE3.2"]},  # one extra (FP)
             {"predicted": [], "gold": ["GE1.1"]}]                   # miss (FN)
    a = js._agreement(preds, None)
    assert a["exact_set_agreement"] == round(1 / 3, 4)
    assert 0 < a["micro_f1"] < 1
    # tp=2, fp=1, fn=1 -> precision 2/3, recall 2/3, f1 2/3
    assert a["precision"] == round(2 / 3, 4) and a["recall"] == round(2 / 3, 4)
