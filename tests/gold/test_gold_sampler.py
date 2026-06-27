from src.common.config import Config
from src.gold.gold_sampler import GoldSampler


def _g():
    return GoldSampler(Config())


def test_cochran_size_with_fpc():
    g = _g()
    n, n0 = g._cochran(2800)
    assert round(n0) == 384            # z=1.96, p=0.5, e=0.05
    assert 330 <= n <= 345             # after finite-population correction on N=2800


def test_allocation_respects_floor_and_availability():
    g = _g()
    strata = {("human", "WA"): list(range(1000)), ("ai_zero_shot", "CE"): list(range(3))}
    alloc = g._allocate(339, strata, 1003)
    assert alloc[("human", "WA")] > alloc[("ai_zero_shot", "CE")]
    assert alloc[("ai_zero_shot", "CE")] == 3          # capped at availability (< floor of 5)
    assert alloc[("human", "WA")] <= 1000


def test_codebook_lists_all_leaves_and_lang_markers():
    cb = _g()._codebook()
    assert "GE6.1" in cb and "AE6.4" in cb
    assert "**[lang]**" in cb           # language-dependent leaves marked
