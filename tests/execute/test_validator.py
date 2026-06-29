import json

from src.common.config import Config
from src.execute.validator import Validator

CORRECT = "#include <iostream>\nint main(){int a,b;std::cin>>a>>b;std::cout<<a+b<<\"\\n\";}"
WRONG = "#include <iostream>\nint main(){int a,b;std::cin>>a>>b;std::cout<<a-b<<\"\\n\";}"
NO_COMPILE = "int main(){ return"


def _problem(tmp_path):
    d = tmp_path / "0001A"
    d.mkdir()
    (d / "meta.json").write_text(json.dumps({"problem_id": "0001A", "time_limit_s": 2.0}))
    (d / "tests.jsonl").write_text(
        json.dumps({"input": "2 3\n", "output": "5\n", "kind": "public"}) + "\n" +
        json.dumps({"input": "10 1\n", "output": "11\n", "kind": "generated"}) + "\n")
    return d


def test_verdicts_signals_and_cache(tmp_path):
    v = Validator(Config("config.yaml"))
    v.cache = tmp_path / "cache"
    d = _problem(tmp_path)

    ac = v.judge(d, CORRECT)
    assert ac["verdict"] == "AC" and all(t["pass"] for t in ac["per_test"])

    wa = v.judge(d, WRONG)
    assert wa["verdict"] == "WA"
    assert wa["first_failing_test"]["expected"].strip() == "5" and wa["first_failing_test"]["actual"].strip() == "-1"

    ce = v.judge(d, NO_COMPILE)
    assert ce["verdict"] == "CE" and ce["compiler_stderr"]

    # the (problem, source) result is cached on disk for free deterministic re-runs
    assert (v.cache / f"{v._key('0001A', CORRECT, 'cpp')}.json").exists()
