import json

from src.common.config import Config
from src.data.benchmark_builder import BenchmarkBuilder


def _problem(cid, idx, source, cpp_correct, cpp_incorrect, py3_incorrect):
    def tests(n):
        return {"input": [f"in{i}" for i in range(n)], "output": [f"out{i}" for i in range(n)]}
    sol_lang = [2] * cpp_correct + [3] * 1                 # C++ correct + one python3
    sol_src = [f"//cpp correct {i}" for i in range(cpp_correct)] + ["#py3"]
    inc_lang = [2] * cpp_incorrect + [3] * py3_incorrect
    inc_src = [f"//cpp wrong {i}" for i in range(cpp_incorrect)] + ["#py3 wrong"] * py3_incorrect
    return {"name": f"{cid}_{idx}. Demo", "description": f"desc {cid}{idx}", "source": source,
            "difficulty": 7, "cf_contest_id": cid, "cf_index": idx, "cf_rating": 1100,
            "cf_tags": ["math", "greedy"], "memory_limit_bytes": 256000000,
            "time_limit": {"seconds": 2, "nanos": 0},
            "public_tests": tests(1), "private_tests": tests(2), "generated_tests": tests(3),
            "solutions": {"language": sol_lang, "solution": sol_src},
            "incorrect_solutions": {"language": inc_lang, "solution": inc_src}}


def test_benchmark_build(tmp_path, monkeypatch):
    rows = [_problem(1575, "A", source=2, cpp_correct=3, cpp_incorrect=2, py3_incorrect=4),
            _problem(9999, "B", source=4, cpp_correct=1, cpp_incorrect=1, py3_incorrect=0)]  # AtCoder -> dropped
    b = BenchmarkBuilder(Config("config.yaml"))
    b.out = tmp_path
    monkeypatch.setattr(b, "_load", lambda: rows)

    r = b.run()
    assert r["test_problems"] == 2 and r["kept_codeforces"] == 1

    # only the Codeforces problem is materialized
    assert (tmp_path / "1575A").is_dir()
    assert not (tmp_path / "9999B").exists()

    # C++-only extraction: correct/incorrect hold exactly the C++ submissions
    correct = [json.loads(l) for l in (tmp_path / "1575A" / "correct.jsonl").read_text().splitlines()]
    incorrect = [json.loads(l) for l in (tmp_path / "1575A" / "incorrect.jsonl").read_text().splitlines()]
    assert len(correct) == 3 and len(incorrect) == 2
    assert all("py3" not in c["source"] for c in incorrect)

    # all tests merged with kind tags
    tests = [json.loads(l) for l in (tmp_path / "1575A" / "tests.jsonl").read_text().splitlines()]
    assert len(tests) == 6 and {t["kind"] for t in tests} == {"public", "private", "generated"}

    # meta keeps raw cf_rating / cf_tags and per-language counts
    meta = json.loads((tmp_path / "1575A" / "meta.json").read_text())
    assert meta["cf_rating"] == 1100 and meta["cf_tags"] == ["math", "greedy"]
    assert meta["n_incorrect"]["cpp"] == 2 and meta["n_incorrect"]["python3"] == 4

    # whole-split stats count every source and language (incl. non-stored ones)
    stats = json.loads((tmp_path / "dataset_stats.json").read_text())
    assert stats["total_problems"] == 2 and stats["codeforces_problems"] == 1
    assert stats["by_source"] == {"codeforces": 1, "atcoder": 1}
    assert stats["submissions_by_language"]["incorrect"]["python3"] == 4

    assert (tmp_path / "manifest.csv").exists()
