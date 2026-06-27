from src.common.config import Config
from src.data.human_corpus_builder import HumanCorpusBuilder


def _b():
    return HumanCorpusBuilder(Config())


def test_pick_is_deterministic_and_capped():
    b = _b()
    recs = [{"idx": i, "code": str(i)} for i in range(100)]
    a = b._pick(recs, "p1")
    assert a == b._pick(recs, "p1")            # same seed+pid -> same order
    assert len(a) == b.max_judge               # truncated to the judging cap
    assert b._pick(recs, "p1") != b._pick(recs, "p2")  # per-problem seeding differs


def test_pick_does_not_mutate_input():
    b = _b()
    recs = [{"idx": i, "code": str(i)} for i in range(5)]
    b._pick(recs, "p1")
    assert [r["idx"] for r in recs] == [0, 1, 2, 3, 4]
