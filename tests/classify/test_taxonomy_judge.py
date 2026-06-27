from src.common.config import Config
from src.classify.taxonomy_judge import TaxonomyJudge


def _j():
    return TaxonomyJudge(Config())


def test_tier1_candidates_by_verdict():
    assert TaxonomyJudge.tier1_candidates("CE") == ["GE2.1", "GE2.2"]
    assert "GE2.1" not in TaxonomyJudge.tier1_candidates("WA")
    assert len(TaxonomyJudge.tier1_candidates("WA")) >= 20


def test_parse_primary_secondary_filters_unknown():
    j = _j()
    p = j._parse('noise {"primary":"GE4.2","secondary":["AE3.2","ZZ9.9"],"rationale":"x"} tail')
    assert p["primary"] == "GE4.2"
    assert p["secondary"] == ["AE3.2"]            # invalid ZZ9.9 dropped
    assert p["uncovered"] is False
    assert j._parse('{"primary":"UNCOVERED","secondary":[]}')["uncovered"] is True
    assert j._parse("not json")["primary"] is None


def test_aggregate_primary_mode_and_secondary_majority():
    j = _j()
    m = j.m
    maj = m // 2 + 1
    # primary GE1.1 in a majority of samples; GE1.2 appears only as a minority secondary
    samples = ([{"primary": "GE1.1", "secondary": [], "uncovered": False, "rationale": ""}] * maj +
               [{"primary": "GE1.2", "secondary": ["GE1.1"], "uncovered": False, "rationale": ""}] * (m - maj))
    agg = j._aggregate(samples)
    assert agg["primary"] == "GE1.1"             # mode of primaries
    assert "GE1.2" not in agg["secondary"]       # minority -> not promoted
    assert agg["leaves"][0] == "GE1.1"
