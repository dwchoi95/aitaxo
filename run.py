import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


def _load_env():
    f = Path(".env")
    if not f.exists():
        return
    for line in f.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

from src.common.config import Config
from src.data.dataset_finalizer import DatasetFinalizer
from src.data.human_corpus_builder import HumanCorpusBuilder
from src.data.problem_set_builder import ProblemSetBuilder
from src.analysis.rq_analysis import RqAnalysis
from src.classify.classifier import Classifier
from src.generation.ai_generator import AiGenerator
from src.gold.gold_sampler import GoldSampler
from src.judge.submission_judge import SubmissionJudge


def main():
    _load_env()
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("test")
    sub.add_parser("build-problems")
    cj = sub.add_parser("check-judge")
    cj.add_argument("--limit", type=int, default=None)
    bh = sub.add_parser("build-human")
    bh.add_argument("--limit", type=int, default=None)
    ba = sub.add_parser("build-ai")
    ba.add_argument("--limit", type=int, default=None)
    ba.add_argument("--dry-run", action="store_true")
    sub.add_parser("finalize-dataset")
    sub.add_parser("prepare-gold")
    cl = sub.add_parser("classify")
    cl.add_argument("--dataset", default="final", choices=["final", "gold"])
    cl.add_argument("--model", default=None)
    cl.add_argument("--limit", type=int, default=None)
    cl.add_argument("--dry-run", action="store_true")
    an = sub.add_parser("analyze")
    an.add_argument("--classifications", required=True)
    an.add_argument("--residual", default=None)
    an.add_argument("--turn0", default=None)
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
    elif args.cmd == "build-human":
        r = HumanCorpusBuilder(config).run(limit=args.limit)
        print(json.dumps({k: r[k] for k in ("problems", "kept_submissions",
                          "unexpected_ac_dropped", "problems_with_ge1_non_ac")}, indent=2))
    elif args.cmd == "build-ai":
        r = AiGenerator(config).run(limit=args.limit, dry_run=args.dry_run)
        print(json.dumps({k: r[k] for k in ("problems", "zero_shot_samples", "zero_shot_ac",
                          "zero_shot_no_code", "kept_non_ac_total", "problems_with_ge1_non_ac",
                          "self_reflection_solved")}, indent=2))
    elif args.cmd == "finalize-dataset":
        r = DatasetFinalizer(config).run()
        print(json.dumps({k: v for k, v in r.items() if k != "intersection_pids"}, indent=2))
    elif args.cmd == "prepare-gold":
        r = GoldSampler(config).run()
        print(json.dumps(r, indent=2))
    elif args.cmd == "classify":
        r = Classifier(config).run(dataset=args.dataset, model=args.model,
                                   limit=args.limit, dry_run=args.dry_run)
        print(json.dumps(r, indent=2, ensure_ascii=False))
    elif args.cmd == "analyze":
        r = RqAnalysis(config).run(args.classifications, args.residual, args.turn0)
        print(json.dumps(r, indent=2, default=str))


if __name__ == "__main__":
    main()
