import argparse
import json

from src.common.config import Config
from src.data.builder import Builder


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("build")
    args = parser.parse_args()
    config = Config("config.yaml")
    if args.cmd == "build":
        r = Builder(config).run()
        print(json.dumps(r, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
