from src.common.config import Config
from src.gold.gold_adjudicator import GoldAdjudicator


def _a():
    return GoldAdjudicator(Config())


def test_leaf_kappa_perfect_and_chance():
    a = _a()
    items = [str(i) for i in range(10)]
    a1 = {i: {"GE4.2"} for i in items[:5]} | {i: set() for i in items[5:]}
    a2 = dict(a1)
    assert a._leaf_kappa(a1, a2, items, "GE4.2") == 1.0          # identical -> kappa 1
    a3 = {i: ({"GE4.2"} if int(i) >= 5 else set()) for i in items}
    assert a._leaf_kappa(a1, a3, items, "GE4.2") < 0             # opposite -> negative


def test_jaccard():
    a = _a()
    assert a._jaccard({"GE1.1", "AE1.2"}, {"GE1.1"}) == 0.5
    assert a._jaccard(set(), set()) == 1.0
