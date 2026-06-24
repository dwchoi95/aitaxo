from dataclasses import dataclass, field
from typing import Literal


@dataclass(frozen=True)
class TestCase:
    stdin: str
    expected_stdout: str
    name: str = "sample"


@dataclass(frozen=True)
class Problem:
    """A normalized programming problem from any source.

    `statement` is the cleaned natural-language problem text fed to the LLM.
    `tests` is the list of (stdin, expected_stdout) pairs used as the oracle.
    """

    problem_id: str
    source: Literal["codenet", "codeforces"]
    statement: str
    tests: list[TestCase] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
