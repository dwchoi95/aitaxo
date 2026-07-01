import argparse
import json
import os
from pathlib import Path

from src.common.config import Config
from src.data.builder import Builder
from src.core.ai_submission import AiSubmission
from src.core.self_reflection import SelfReflection
from src.core.gold_sampler import GoldSampler
from src.core.gold_consolidator import GoldConsolidator
from src.core.classifier import Classifier


def _load_env():
    f = Path(".env")
    if not f.exists():
        return
    for line in f.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())


def main():
    _load_env()
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("build")
    g = sub.add_parser("generate")
    g.add_argument("--limit", type=int, default=None)
    g.add_argument("--models", default=None, help="comma-separated subset of ai_submission.models")
    rf = sub.add_parser("reflect")
    rf.add_argument("--limit", type=int, default=None)
    rf.add_argument("--models", default=None, help="comma-separated subset of reflect.models")
    rf.add_argument("--problem", default=None, help="restrict to a single problem id")
    sub.add_parser("sample-gold")
    cg = sub.add_parser("consolidate-gold")
    cg.add_argument("--input", default=None, help="annotation CSV (default analysis/label/annotator.csv)")
    c = sub.add_parser("classify")
    c.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()
    config = Config("config.yaml")
    if args.cmd == "build":
        r = Builder(config).run()
        print(json.dumps(r, indent=2, ensure_ascii=False))
    elif args.cmd == "generate":
        models = args.models.split(",") if args.models else None
        r = AiSubmission(config).run(limit=args.limit, models=models)
        print(json.dumps(r, indent=2, ensure_ascii=False))
    elif args.cmd == "reflect":
        models = args.models.split(",") if args.models else None
        r = SelfReflection(config).run(limit=args.limit, models=models, problem=args.problem)
        print(json.dumps(r, indent=2, ensure_ascii=False))
    elif args.cmd == "sample-gold":
        r = GoldSampler(config).run()
        print(json.dumps(r, indent=2, ensure_ascii=False))
    elif args.cmd == "consolidate-gold":
        r = GoldConsolidator(config).run(input_path=args.input)
        print(json.dumps(r, indent=2, ensure_ascii=False))
    elif args.cmd == "classify":
        r = Classifier(config).run(limit=args.limit)
        print(json.dumps(r, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
