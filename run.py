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
from src.classify.judge_ablation import JudgeAblation
from src.classify.judge_selector import JudgeSelector
from src.generation.ai_generator import AiGenerator
from src.gold.gold_adjudicator import GoldAdjudicator
from src.gold.gold_finalizer import GoldFinalizer
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
    sub.add_parser("adjudicate-gold")
    sub.add_parser("finalize-gold")
    sj = sub.add_parser("select-judge")
    sj.add_argument("--limit", type=int, default=None)
    sj.add_argument("--dry-run", action="store_true")
    ab = sub.add_parser("ablate-judge")
    ab.add_argument("--limit", type=int, default=None)
    ab.add_argument("--efforts", default="low,medium")
    cl = sub.add_parser("classify")
    cl.add_argument("--dataset", default="final", choices=["final", "gold"])
    cl.add_argument("--model", default=None)
    cl.add_argument("--limit", type=int, default=None)
    cl.add_argument("--dry-run", action="store_true")
    an = sub.add_parser("analyze")
    an.add_argument("--classifications", required=True)
    an.add_argument("--rq3", default=None)
    pe = sub.add_parser("phase-e")
    pe.add_argument("--limit", type=int, default=None)
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
    elif args.cmd == "adjudicate-gold":
        r = GoldAdjudicator(config).run()
        print(json.dumps(r, indent=2, ensure_ascii=False))
    elif args.cmd == "finalize-gold":
        r = GoldFinalizer(config).run()
        print(json.dumps(r, indent=2, ensure_ascii=False))
    elif args.cmd == "select-judge":
        r = JudgeSelector(config).run(limit=args.limit, dry_run=args.dry_run)
        print(json.dumps(r, indent=2, ensure_ascii=False))
    elif args.cmd == "ablate-judge":
        r = JudgeAblation(config).run(efforts=tuple(args.efforts.split(",")), limit=args.limit)
        print(json.dumps(r, indent=2, ensure_ascii=False))
    elif args.cmd == "classify":
        r = Classifier(config).run(dataset=args.dataset, model=args.model,
                                   limit=args.limit, dry_run=args.dry_run)
        print(json.dumps(r, indent=2, ensure_ascii=False))
    elif args.cmd == "analyze":
        r = RqAnalysis(config).run(args.classifications, args.rq3)
        print(json.dumps(r, indent=2, default=str))
    elif args.cmd == "phase-e":
        cl = Classifier(config)
        slug = cl._slug(config["judge"]["chosen"])
        print("[1/3] classifying main dataset (final.jsonl) ...", flush=True)
        r1 = cl.run(dataset="final", limit=args.limit)
        print(json.dumps(r1), flush=True)
        print("[2/3] classifying RQ3 self-reflection set ...", flush=True)
        rq3_src = str(Path(config["paths"]["artifacts"]) / "dataset" / "rq3_submissions.jsonl")
        r2 = cl.run(dataset=rq3_src, limit=args.limit)
        print(json.dumps(r2), flush=True)
        incomplete = (r1.get("stopped_early") or r2.get("stopped_early")
                      or r1["completed"] < r1["total"] or r2["completed"] < r2["total"])
        if incomplete:
            print(f"PHASE_E_INCOMPLETE -- classification stopped early "
                  f"(main {r1['completed']}/{r1['total']}, rq3 {r2['completed']}/{r2['total']}; "
                  f"reason: {r1.get('stopped_early') or r2.get('stopped_early')}). "
                  "Top up quota and re-run `run.py phase-e` (cached work is reused). Analysis skipped.",
                  flush=True)
        else:
            print("[3/3] analysis (RQ1 family+leaf, RQ2, RQ3, saturation, distributions) ...", flush=True)
            cdir = Path(config["paths"]["artifacts"]) / "classifications"
            summary = RqAnalysis(config).run(str(cdir / f"{slug}_final.jsonl"),
                                             str(cdir / f"{slug}_rq3_submissions.jsonl"))
            print(json.dumps(summary, indent=2, default=str), flush=True)
            print("PHASE_E_DONE -- stopped before paper; review results/", flush=True)


if __name__ == "__main__":
    main()
