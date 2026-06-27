import argparse
import subprocess
import sys

from src.common.config import Config


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("test")
    # one add_parser(...) per step is added as each phase's step class is implemented
    args = parser.parse_args()
    config = Config("config.yaml")
    if args.cmd == "test":
        sys.exit(subprocess.call([sys.executable, "-m", "pytest", "-q"]))


if __name__ == "__main__":
    main()
