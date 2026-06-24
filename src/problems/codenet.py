"""Load Project CodeNet problems into the normalized Problem schema.

CodeNet stores:
  - problem_descriptions/p#####.html   — HTML problem statement
  - derived/input_output/data/p#####/{input,output}.txt — single sample I/O

We strip HTML to plain text, but keep <pre> blocks (input/output examples)
verbatim because formatting matters for code-generation prompts.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Iterator

from bs4 import BeautifulSoup

from .schema import Problem, TestCase


def _html_to_text(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")

    for pre in soup.find_all("pre"):
        pre.replace_with(f"\n```\n{pre.get_text()}\n```\n")

    text = soup.get_text("\n")
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return text


def load_codenet_problem(codenet_root: Path, problem_id: str) -> Problem | None:
    """Load one CodeNet problem by id (e.g. 'p00001'). Returns None if missing."""
    desc_path = codenet_root / "problem_descriptions" / f"{problem_id}.html"
    io_dir = codenet_root / "derived" / "input_output" / "data" / problem_id

    if not desc_path.exists():
        return None

    statement = _html_to_text(desc_path.read_text(encoding="utf-8", errors="replace"))

    tests: list[TestCase] = []
    input_path = io_dir / "input.txt"
    output_path = io_dir / "output.txt"
    if input_path.exists() and output_path.exists():
        tests.append(
            TestCase(
                stdin=input_path.read_text(encoding="utf-8", errors="replace"),
                expected_stdout=output_path.read_text(encoding="utf-8", errors="replace"),
                name="sample",
            )
        )

    return Problem(
        problem_id=problem_id,
        source="codenet",
        statement=statement,
        tests=tests,
        metadata={"description_path": str(desc_path)},
    )


def iter_codenet_problems(
    codenet_root: Path,
    limit: int | None = None,
    require_tests: bool = True,
) -> Iterator[Problem]:
    """Yield CodeNet problems in id order, optionally requiring sample I/O."""
    desc_dir = codenet_root / "problem_descriptions"
    if not desc_dir.exists():
        raise FileNotFoundError(f"CodeNet problem_descriptions not found: {desc_dir}")

    yielded = 0
    for html in sorted(desc_dir.glob("p*.html")):
        problem_id = html.stem
        problem = load_codenet_problem(codenet_root, problem_id)
        if problem is None:
            continue
        if require_tests and not problem.tests:
            continue
        yield problem
        yielded += 1
        if limit is not None and yielded >= limit:
            return
