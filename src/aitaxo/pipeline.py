"""End-to-end MVP pipeline: load problems → generate code → run tests → save failures."""
from __future__ import annotations

import dataclasses
import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path

from openai import OpenAI

from .config import Config, load_config
from .execution.runner import classify_failure, run_problem
from .generation import generate_python_solution
from .problems import Problem, iter_codenet_problems

log = logging.getLogger(__name__)


def _record(problem: Problem, generation, results, status, error: str | None = None) -> dict:
    return {
        "problem_id": problem.problem_id,
        "source": problem.source,
        "statement": problem.statement,
        "tests": [dataclasses.asdict(t) for t in problem.tests],
        "generation": dataclasses.asdict(generation) if generation else None,
        "execution": {
            "status": status,
            "results": [dataclasses.asdict(r) for r in results],
            "error": error,
        },
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def run_pipeline(
    config: Config | None = None,
    *,
    limit: int = 10,
    source: str = "codenet",
    save_all: bool = False,
) -> dict:
    """Run the MVP pipeline.

    Args:
        limit: number of problems to process
        source: 'codenet' (only one supported in MVP)
        save_all: if True, save both passing and failing cases (useful for debugging)

    Writes one JSONL file per run to `config.out_dir` and returns summary stats.
    """
    cfg = config or load_config()
    if not cfg.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY not set. Copy .env.example to .env and fill it in.")

    client = OpenAI(api_key=cfg.openai_api_key)

    if source != "codenet":
        raise NotImplementedError(f"source={source!r} not supported in MVP")

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_path = cfg.out_dir / f"codenet_{cfg.model}_{timestamp}.jsonl"

    stats = {"total": 0, "pass": 0, "wrong_answer": 0, "runtime_error": 0,
             "compile_error": 0, "timeout": 0, "generation_error": 0}

    started = time.perf_counter()
    with out_path.open("w", encoding="utf-8") as fh:
        for problem in iter_codenet_problems(cfg.codenet_root, limit=limit, require_tests=True):
            stats["total"] += 1
            log.info("→ %s", problem.problem_id)

            try:
                generation = generate_python_solution(
                    problem, client=client, model=cfg.model, temperature=cfg.temperature
                )
            except Exception as exc:
                log.warning("generation failed on %s: %s", problem.problem_id, exc)
                stats["generation_error"] += 1
                record = _record(problem, None, [], "generation_error", error=repr(exc))
                fh.write(json.dumps(record, ensure_ascii=False) + "\n")
                continue

            results = run_problem(generation.code, problem)
            status = classify_failure(results)
            stats[status] = stats.get(status, 0) + 1

            if save_all or status != "pass":
                record = _record(problem, generation, results, status)
                fh.write(json.dumps(record, ensure_ascii=False) + "\n")
                fh.flush()

    stats["elapsed_sec"] = round(time.perf_counter() - started, 2)
    stats["out_path"] = str(out_path)
    return stats
