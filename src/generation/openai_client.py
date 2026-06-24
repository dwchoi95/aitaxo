"""GPT-4o code generation client.

Generates a *single* Python solution per call so we can record full metadata
(model, temperature, prompt, raw response) alongside each datapoint.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from problems import Problem


SYSTEM_PROMPT = (
    "You are a competitive programming assistant. Given a problem statement, "
    "produce a complete, self-contained Python 3 program that reads from "
    "standard input and writes to standard output. Output ONLY the code "
    "inside a single fenced ```python block. No prose, no examples."
)


def _user_prompt(problem: Problem) -> str:
    return f"# Problem\n\n{problem.statement}\n\nWrite the Python 3 solution."


_CODE_BLOCK = re.compile(r"```(?:python)?\s*\n(.*?)```", re.DOTALL)


def _extract_code(text: str) -> str:
    match = _CODE_BLOCK.search(text)
    if match:
        return match.group(1).strip()
    return text.strip()


@dataclass
class Generation:
    code: str
    raw_response: str
    model: str
    temperature: float
    prompt_tokens: int | None
    completion_tokens: int | None


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=20),
    reraise=True,
)
def generate_python_solution(
    problem: Problem,
    *,
    client: OpenAI,
    model: str = "gpt-4o",
    temperature: float = 0.7,
    max_tokens: int = 2048,
) -> Generation:
    """Single-shot generation. Wrap with retries; caller controls concurrency."""
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": _user_prompt(problem)},
        ],
        temperature=temperature,
        max_tokens=max_tokens,
    )
    raw = response.choices[0].message.content or ""
    usage = response.usage
    return Generation(
        code=_extract_code(raw),
        raw_response=raw,
        model=model,
        temperature=temperature,
        prompt_tokens=usage.prompt_tokens if usage else None,
        completion_tokens=usage.completion_tokens if usage else None,
    )
