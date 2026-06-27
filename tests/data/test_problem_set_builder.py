from src.common.config import Config
from src.data.problem_set_builder import ProblemSetBuilder


def _b():
    return ProblemSetBuilder(Config())


def test_difficulty_bin():
    b = _b()
    assert b._difficulty_bin(800) == "easy"
    assert b._difficulty_bin(1500) == "medium"
    assert b._difficulty_bin(2000) == "hard"
    assert b._difficulty_bin(2600) == "expert"


def test_algo_families_maps_cf_tags():
    b = _b()
    assert b._algo_families(["dp", "greedy", "implementation"]) == ["AE2", "AE3"]
    assert b._algo_families(["graphs", "dfs and similar"]) == ["AE6"]
    assert b._algo_families([]) == []
    assert b._algo_families(None) == []


def test_solutions_filtered_by_language():
    b = _b()
    sols = {"language": [2, 3, 2, 1], "solution": ["cpp1", "py1", "cpp2", "py2old"]}
    assert b._solutions(sols, 2) == ["cpp1", "cpp2"]
    assert b._solutions(sols, 3) == ["py1"]
    assert b._solutions(None, 3) == []


def test_tests_collected_in_canonical_order_with_kind():
    b = _b()
    row = {"public_tests": {"input": ["i1"], "output": ["o1"]},
           "private_tests": {"input": ["i2"], "output": ["o2"]},
           "generated_tests": {"input": ["i3"], "output": ["o3"]}}
    tests = b._tests(row)
    assert [t["input"] for t in tests] == ["i1", "i2", "i3"]
    assert [t["kind"] for t in tests] == ["public", "private", "generated"]
    assert tests[0]["output"] == "o1"
