"""CLI: `python -m aitaxo.cli generate --limit 5`"""
from __future__ import annotations

import argparse
import json
import logging
import sys

from .config import load_config
from .pipeline import run_pipeline
from .problems import iter_codenet_problems


def cmd_generate(args: argparse.Namespace) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    cfg = load_config()
    stats = run_pipeline(cfg, limit=args.limit, source=args.source, save_all=args.save_all)
    json.dump(stats, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


def cmd_inspect(args: argparse.Namespace) -> int:
    cfg = load_config()
    n = 0
    for problem in iter_codenet_problems(cfg.codenet_root, limit=args.limit):
        print(f"=== {problem.problem_id} ({len(problem.tests)} tests) ===")
        print(problem.statement[:400])
        if problem.tests:
            print(f"--- sample stdin ---\n{problem.tests[0].stdin}")
            print(f"--- sample stdout ---\n{problem.tests[0].expected_stdout}")
        print()
        n += 1
    print(f"({n} problems shown)")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="aitaxo")
    sub = parser.add_subparsers(dest="cmd", required=True)

    gen = sub.add_parser("generate", help="Run the generate→test pipeline")
    gen.add_argument("--limit", type=int, default=5)
    gen.add_argument("--source", default="codenet", choices=["codenet"])
    gen.add_argument("--save-all", action="store_true", help="also save passing cases")
    gen.set_defaults(func=cmd_generate)

    ins = sub.add_parser("inspect", help="Print problem statements (no API calls)")
    ins.add_argument("--limit", type=int, default=3)
    ins.set_defaults(func=cmd_inspect)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
