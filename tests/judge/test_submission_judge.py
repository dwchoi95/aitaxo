from src.common.config import Config
from src.judge.submission_judge import SubmissionJudge


def _j():
    return SubmissionJudge(Config())


def test_match_is_whitespace_token_equality():
    j = _j()
    assert j._match("1 2 3\n", "1 2 3")
    assert j._match("1\n2\n3\n", "1 2 3")
    assert not j._match("1 2 4", "1 2 3")


def test_match_float_tolerance():
    j = _j()
    assert j._match("3.16227670", "3.162277660")
    assert not j._match("3.20", "3.162277660")
    assert not j._match("1 2", "1 2 3")


def test_match_case_insensitive():
    j = _j()
    assert j._match("No\nYes\n", "NO\nYES")
    assert not j._match("YES", "NO")


def test_classify_verdicts():
    j = _j()
    assert j._classify({"timed_out": True, "returncode": None, "stdout": ""}, "x") == "TLE"
    assert j._classify({"timed_out": False, "returncode": 1, "stdout": ""}, "x") == "RE"
    assert j._classify({"timed_out": False, "returncode": 0, "stdout": "5\n"}, "5") == "AC"
    assert j._classify({"timed_out": False, "returncode": 0, "stdout": "6"}, "5") == "WA"


def test_python_compile_error_detects_syntax():
    j = _j()
    assert j._python_compile_error("def f(:\n  pass") is not None
    assert j._python_compile_error("print(1)") is None
