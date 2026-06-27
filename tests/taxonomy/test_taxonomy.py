from src.taxonomy.taxonomy import (FAMILIES, LANGUAGE_DEPENDENT_LEAVES, TAXONOMY,
                                   VERDICT_CANDIDATES, families_for_tags)


def test_taxonomy_shape():
    assert len(TAXONOMY) == 31           # 13 GE leaves + 18 AE leaves
    assert all(leaf.split(".")[0] in FAMILIES for leaf in TAXONOMY)
    assert all(len(v) == 4 for v in TAXONOMY.values())


def test_language_dependent_leaves_are_pinned():
    assert set(LANGUAGE_DEPENDENT_LEAVES) == {"GE2.1", "GE2.2", "GE6.1", "GE6.2"}


def test_verdict_candidates_subset_of_taxonomy():
    for cands in VERDICT_CANDIDATES.values():
        assert all(c in TAXONOMY for c in cands)
    assert "GE2.1" in VERDICT_CANDIDATES["CE"]


def test_families_for_tags_aligned_to_pinned_codes():
    assert families_for_tags(["dp"]) == ["AE3"]          # DP, not graphs
    assert families_for_tags(["graphs", "trees"]) == ["AE6"]
    assert families_for_tags(["greedy", "math"]) == ["AE1", "AE2"]
