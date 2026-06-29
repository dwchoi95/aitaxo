import argparse
import json

from src.common.config import Config
from src.data.benchmark_builder import BenchmarkBuilder


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    bm = sub.add_parser("benchmark")
    bm.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()
    config = Config("config.yaml")
    if args.cmd == "benchmark":
        r = BenchmarkBuilder(config).run(limit=args.limit)
        print(json.dumps(r, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
