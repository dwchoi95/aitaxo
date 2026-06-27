import argparse
import json
import subprocess
import sys
from pathlib import Path

from src.common.config import Config
from src.data.problem_set_builder import ProblemSetBuilder
from src.judge.submission_judge import SubmissionJudge


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("test")
    sub.add_parser("build-problems")
    cj = sub.add_parser("check-judge")
    cj.add_argument("--limit", type=int, default=None)
    # one add_parser(...) per step is added as each phase's step class is implemented
    args = parser.parse_args()
    config = Config("config.yaml")
    if args.cmd == "test":
        sys.exit(subprocess.call([sys.executable, "-m", "pytest", "-q"]))
    elif args.cmd == "build-problems":
        ProblemSetBuilder(config).run()
    elif args.cmd == "check-judge":
        root = Path(config["paths"]["data"]) / "problems"
        r = SubmissionJudge(config).oracle_ac_selftest(root, config["languages"]["primary"], limit=args.limit)
        out = Path(config["paths"]["artifacts"]) / "judgeable_problems.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8")
        from collections import Counter
        by_reason = Counter(e["reason"] for e in r["excluded"])
        print(json.dumps({k: r[k] for k in ("problems", "judgeable_count", "excluded_count",
                                            "ac_rate_on_judgeable")}, indent=2))
        print("excluded by reason:", dict(by_reason))
        print("wrote", out)


if __name__ == "__main__":
    main()
