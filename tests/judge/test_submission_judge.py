import json

from src.common.config import Config
from src.judge.submission_judge import SubmissionJudge

CORRECT = "#include <iostream>\nint main(){int a,b;std::cin>>a>>b;std::cout<<a+b<<\"\\n\";}"
WRONG = "#include <iostream>\nint main(){int a,b;std::cin>>a>>b;std::cout<<a-b<<\"\\n\";}"
NO_COMPILE = "int main(){ return"


def _problem(tmp_path):
    d = tmp_path / "0001A"
    d.mkdir()
    (d / "meta.json").write_text(json.dumps(
        {"problem_id": "0001A", "time_limit_s": 2.0, "memory_limit_bytes": 256000000}))
    (d / "tests.jsonl").write_text(
        json.dumps({"input": "2 3\n", "output": "5\n", "kind": "public"}) + "\n" +
        json.dumps({"input": "10 1\n", "output": "11\n", "kind": "generated"}) + "\n")
    (d / "correct.jsonl").write_text(json.dumps({"source": CORRECT}) + "\n")
    return d


def test_verdicts_and_signals(tmp_path):
    j = SubmissionJudge(Config("config.yaml"))
    j.cache = tmp_path / "cache"
    d = _problem(tmp_path)

    ac = j.judge(d, CORRECT)
    assert ac["verdict"] == "AC" and all(t["pass"] for t in ac["per_test"])

    wa = j.judge(d, WRONG)
    assert wa["verdict"] == "WA"
    assert wa["first_failing_test"]["expected"].strip() == "5" and wa["first_failing_test"]["actual"].strip() == "-1"

    ce = j.judge(d, NO_COMPILE)
    assert ce["verdict"] == "CE" and ce["compiler_stderr"]


def test_oracle_selftest_and_cache(tmp_path):
    j = SubmissionJudge(Config("config.yaml"))
    j.cache = tmp_path / "cache"
    _problem(tmp_path)

    r = j.oracle_ac_selftest(tmp_path, "cpp")
    assert r["judgeable"] == ["0001A"] and r["excluded_count"] == 0 and r["ac_rate_on_judgeable"] == 100.0

    # second judge of the same (problem, source) is served from cache (file exists)
    key = j._key("0001A", CORRECT, "cpp")
    assert (j.cache / f"{key}.json").exists()
