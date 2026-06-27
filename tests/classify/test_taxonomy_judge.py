from src.common.config import Config
from src.classify.taxonomy_judge import TaxonomyJudge


def _j():
    return TaxonomyJudge(Config())


def test_tier1_candidates_by_verdict():
    assert TaxonomyJudge.tier1_candidates("CE") == ["GE2.1", "GE2.2"]
    assert "GE2.1" not in TaxonomyJudge.tier1_candidates("WA")
    assert len(TaxonomyJudge.tier1_candidates("WA")) >= 20


def test_parse_filters_to_known_leaves():
    j = _j()
    p = j._parse('noise {"leaves":["GE4.2","ZZ9.9"],"rationale":"x","uncovered":false} tail')
    assert p["leaves"] == ["GE4.2"]          # invalid ZZ9.9 dropped
    assert p["uncovered"] is False
    assert j._parse("not json at all")["leaves"] == []


def test_aggregate_majority_vote():
    j = _j()
    m = j.m
    maj = m // 2 + 1                          # strict-majority count for any m
    samples = ([{"leaves": ["GE4.2"], "uncovered": False, "rationale": ""}] * maj +
               [{"leaves": ["AE3.2"], "uncovered": False, "rationale": ""}] * (m - maj))
    agg = j._aggregate(samples)
    assert agg["leaves"] == ["GE4.2"]        # majority on GE4.2; AE3.2 below threshold
    assert agg["uncovered"] is False
    assert agg["needs_review"] is False
