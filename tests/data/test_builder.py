import json

from src.common.config import Config
from src.data.builder import Builder


class _StubValidator:
    # verdict is AC iff the source is tagged GOOD; lets us test the keep/drop filter without compiling
    def judge(self, problem_dir, source, language="cpp"):
        return {"verdict": "AC" if "GOOD" in source else "WA"}


def _problem(cid, idx, source, correct, incorrect):
    def tests(n):
        return {"input": [f"in{i}" for i in range(n)], "output": [f"out{i}" for i in range(n)]}
    return {"name": f"{cid}_{idx}. Demo", "description": f"desc {cid}{idx}", "source": source,
            "difficulty": 7, "cf_contest_id": cid, "cf_index": idx, "cf_rating": 1100,
            "cf_tags": ["math"], "memory_limit_bytes": 256000000,
            "time_limit": {"seconds": 2, "nanos": 0},
            "public_tests": tests(1), "private_tests": tests(1), "generated_tests": tests(1),
            "solutions": {"language": [2] * len(correct), "solution": correct},
            "incorrect_solutions": {"language": [2] * len(incorrect), "solution": incorrect}}


def test_validation_filter(tmp_path, monkeypatch):
    keep = _problem(1, "A", 2, correct=["GOOD c0", "GOOD c1"],
                    incorrect=["GOOD u0"] + [f"bug {i}" for i in range(10)] + ["GOOD u1"])
    few = _problem(2, "B", 2, correct=["GOOD c0"], incorrect=[f"bug {i}" for i in range(5)])
    nonjudge = _problem(3, "C", 2, correct=["WA c0", "WA c1"], incorrect=[f"bug {i}" for i in range(10)])
    atcoder = _problem(9, "Z", 4, correct=["GOOD c0"], incorrect=[f"bug {i}" for i in range(10)])

    b = Builder(Config("config.yaml"))
    b.out = tmp_path
    b.validator = _StubValidator()
    monkeypatch.setattr(b, "_load", lambda: [keep, few, nonjudge, atcoder])

    r = b.run()
    assert r["test_problems"] == 4 and r["codeforces"] == 3
    assert r["kept_problems"] == 1
    assert r["dropped"] == {"too_few_bugs": 1, "not_judgeable": 1}

    # disagreement totals over every judged submission: the 2 WA "correct"s (3C) and the 2
    # unexpected-AC "incorrect"s (1A) are the label-vs-sandbox mismatches
    dis = r["disagreement"]
    assert dis["correct_judged"] == 5 and dis["correct_disagree"] == 2
    assert dis["incorrect_judged"] == 17 and dis["incorrect_disagree_unexpected_ac"] == 2

    # only the qualifying Codeforces problem is materialized
    assert (tmp_path / "1A").is_dir()
    for gone in ("2B", "3C", "9Z"):
        assert not (tmp_path / gone).exists()

    # every agreeing submission is kept: both GOOD corrects (AC), all 10 bug incorrects (non-AC);
    # the 2 unexpected-AC incorrects (GOOD) disagree with the label and are dropped
    correct = [json.loads(l) for l in (tmp_path / "1A" / "correct.jsonl").read_text().splitlines()]
    incorrect = [json.loads(l) for l in (tmp_path / "1A" / "incorrect.jsonl").read_text().splitlines()]
    assert len(correct) == 2 and all("GOOD" in c["source"] for c in correct)
    assert len(incorrect) == 10 and all("bug" in c["source"] for c in incorrect)

    meta = json.loads((tmp_path / "1A" / "meta.json").read_text())
    assert meta["n_correct"] == 2 and meta["n_incorrect"] == 10
    assert meta["n_incorrect_dropped"] == 2                 # two "GOOD" incorrects judged AC -> dropped

    # whole-split stats still count every source/language before filtering
    stats = json.loads((tmp_path / "dataset_stats.json").read_text())
    assert stats["codeforces_problems"] == 3 and stats["kept_problems"] == 1
