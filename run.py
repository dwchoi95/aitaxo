import argparse
import json
from pathlib import Path

from src.common.config import Config
from src.data.benchmark_builder import BenchmarkBuilder
from src.judge.submission_judge import SubmissionJudge


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    bm = sub.add_parser("benchmark")
    bm.add_argument("--limit", type=int, default=None)
    cj = sub.add_parser("check-judge")
    cj.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()
    config = Config("config.yaml")

    if args.cmd == "benchmark":
        r = BenchmarkBuilder(config).run(limit=args.limit)
        print(json.dumps(r, indent=2, ensure_ascii=False))
    elif args.cmd == "check-judge":
        root = config["paths"]["benchmark"]
        r = SubmissionJudge(config).oracle_ac_selftest(root, "cpp", limit=args.limit)
        out = Path(config["paths"]["artifacts"]) / "judgeable_problems.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8")
        from collections import Counter
        print(json.dumps({k: r[k] for k in ("problems", "judged", "judgeable_count",
                          "excluded_count", "no_oracle", "ac_rate_on_judgeable")}, indent=2))
        print("excluded by reason:", dict(Counter(e["reason"] for e in r["excluded"])))
        print("wrote", out)


if __name__ == "__main__":
    main()
