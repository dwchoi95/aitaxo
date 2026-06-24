"""Smoke tests for the executor — runnable without any API key."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from execution.runner import run_python_code
from problems.schema import TestCase


def test_pass():
    code = "n = int(input())\nprint(n * 2)\n"
    r = run_python_code(code, TestCase(stdin="3\n", expected_stdout="6\n"))
    assert r.failure_type == "pass", r


def test_wrong_answer():
    code = "n = int(input())\nprint(n + 1)\n"
    r = run_python_code(code, TestCase(stdin="3\n", expected_stdout="6\n"))
    assert r.failure_type == "wrong_answer", r


def test_runtime_error():
    code = "raise ValueError('boom')\n"
    r = run_python_code(code, TestCase(stdin="", expected_stdout=""))
    assert r.failure_type == "runtime_error", r


def test_syntax_error():
    code = "def (:\n"
    r = run_python_code(code, TestCase(stdin="", expected_stdout=""))
    assert r.failure_type == "compile_error", r


def test_timeout():
    code = "while True: pass\n"
    r = run_python_code(code, TestCase(stdin="", expected_stdout=""), timeout_sec=0.5)
    assert r.failure_type == "timeout", r


if __name__ == "__main__":
    test_pass()
    test_wrong_answer()
    test_runtime_error()
    test_syntax_error()
    test_timeout()
    print("ok: 5/5 runner tests passed")
