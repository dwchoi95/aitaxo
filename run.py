import argparse
import subprocess
import sys

from src.common.config import Config
from src.data.problem_set_builder import ProblemSetBuilder


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("test")
    sub.add_parser("build-problems")
    # one add_parser(...) per step is added as each phase's step class is implemented
    args = parser.parse_args()
    config = Config("config.yaml")
    if args.cmd == "test":
        sys.exit(subprocess.call([sys.executable, "-m", "pytest", "-q"]))
    elif args.cmd == "build-problems":
        ProblemSetBuilder(config).run()


if __name__ == "__main__":
    main()
