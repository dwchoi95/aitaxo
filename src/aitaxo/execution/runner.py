"""Subprocess sandbox for running generated Python against test I/O.

This is a *thin* sandbox: timeout + cwd isolation + memory cap on Linux.
For an MVP this is acceptable; before scaling up, wrap with Docker/firejail
to defend against malicious generations that try to touch the filesystem
or network.
"""
from __future__ import annotations

import resource
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from ..problems import Problem, TestCase

FailureType = Literal["pass", "wrong_answer", "runtime_error", "timeout", "compile_error"]


@dataclass
class ExecutionResult:
    test_name: str
    failure_type: FailureType
    stdout: str
    stderr: str
    exit_code: int | None
    duration_sec: float


def _set_limits(memory_mb: int) -> None:
    if sys.platform == "linux":
        bytes_ = memory_mb * 1024 * 1024
        try:
            resource.setrlimit(resource.RLIMIT_AS, (bytes_, bytes_))
        except (ValueError, OSError):
            pass


def _normalize(s: str) -> str:
    """Lenient comparison: strip trailing whitespace per line and final newlines."""
    return "\n".join(line.rstrip() for line in s.splitlines()).rstrip()


def run_python_code(
    code: str,
    test: TestCase,
    *,
    timeout_sec: float = 5.0,
    memory_mb: int = 512,
) -> ExecutionResult:
    """Run `code` against one test case. Returns pass/fail classification."""
    import time

    with tempfile.TemporaryDirectory() as tmpdir:
        script = Path(tmpdir) / "solution.py"
        script.write_text(code, encoding="utf-8")

        started = time.perf_counter()
        try:
            proc = subprocess.run(
                [sys.executable, str(script)],
                input=test.stdin,
                capture_output=True,
                text=True,
                timeout=timeout_sec,
                cwd=tmpdir,
                preexec_fn=(lambda: _set_limits(memory_mb)) if sys.platform == "linux" else None,
            )
        except subprocess.TimeoutExpired as exc:
            return ExecutionResult(
                test_name=test.name,
                failure_type="timeout",
                stdout=exc.stdout.decode() if isinstance(exc.stdout, bytes) else (exc.stdout or ""),
                stderr=exc.stderr.decode() if isinstance(exc.stderr, bytes) else (exc.stderr or ""),
                exit_code=None,
                duration_sec=time.perf_counter() - started,
            )

        duration = time.perf_counter() - started

        if proc.returncode != 0:
            failure_type: FailureType = "runtime_error"
            if "SyntaxError" in proc.stderr or "IndentationError" in proc.stderr:
                failure_type = "compile_error"
            return ExecutionResult(
                test_name=test.name,
                failure_type=failure_type,
                stdout=proc.stdout,
                stderr=proc.stderr,
                exit_code=proc.returncode,
                duration_sec=duration,
            )

        actual = _normalize(proc.stdout)
        expected = _normalize(test.expected_stdout)
        if actual == expected:
            return ExecutionResult("pass" if test.name == "sample" else test.name, "pass", proc.stdout, proc.stderr, 0, duration)
        return ExecutionResult(
            test_name=test.name,
            failure_type="wrong_answer",
            stdout=proc.stdout,
            stderr=proc.stderr,
            exit_code=0,
            duration_sec=duration,
        )


def classify_failure(results: list[ExecutionResult]) -> FailureType:
    """Aggregate per-test results into one label. 'pass' iff every test passes."""
    if not results:
        return "runtime_error"
    if all(r.failure_type == "pass" for r in results):
        return "pass"
    for kind in ("compile_error", "runtime_error", "timeout", "wrong_answer"):
        if any(r.failure_type == kind for r in results):
            return kind  # type: ignore[return-value]
    return "wrong_answer"


def run_problem(code: str, problem: Problem, **kwargs) -> list[ExecutionResult]:
    return [run_python_code(code, t, **kwargs) for t in problem.tests]
