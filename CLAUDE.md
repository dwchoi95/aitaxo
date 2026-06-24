# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository status

Research project implementing experiments for `T3_AI-Generated-Code-Aware_APR.md` (Korean proposal, ICSE 2027 target). The proposal is the source of truth for goals — read it first.

**Research goal (don't mistake this for a data collector).** Thesis: *AI-generated bugs differ from human bugs, so they must be repaired differently.* The data pipeline is a means, not the end. The full research arc is four steps:

1. **Build & contrast the dataset** — generate code with GPT-4o/Claude/Gemini, keep only test-failing code, hand-label it; build a CodeNet human-bug **control group** on the same problems.
2. **Define the Taxonomy** — 5 AI-specific bug categories (Spec-Mismatch ← core target, Hallucinated-API, Incomplete-Logic, Test-Gaming, Style-Overfitting), validated by 2-author independent labeling with Cohen's κ ≥ 0.7 (RQ1).
3. **Measure the existing-APR baseline** — run FastFixer/PaR/PyDex/CREF on the AI bugs and *quantify the per-category repair gap* — i.e. prove existing tools fail on AI bugs (RQ2).
4. **Propose the new repair method** — **Spec-Grounded Repair**: LLM extracts structured constraints from the NL spec (input ranges, output format, edge cases) and uses them as a second oracle beyond "tests pass" (RQ3). Plus AI-aware educational feedback explaining the AI's *misunderstanding* (RQ4).

**Currently implemented**: only step 1's first slice — MVP data-generation pipeline (CodeNet → single-shot GPT-4o → sandbox → JSONL of failures). All other deliverables (multi-provider generation, human control group, Taxonomy labeling, APR baselines, Spec-Grounded Repair, feedback) are not yet implemented.

## Architecture

```
problem (CodeNet HTML + sample I/O)
  → generation (OpenAI GPT-4o, single-shot Python)
  → execution (subprocess sandbox, 5s timeout, lenient stdout compare)
  → pipeline (writes JSONL, default: only failing cases)
```

| Concern | Module |
|---|---|
| Normalized `Problem` / `TestCase` schema | `src/aitaxo/problems/schema.py` |
| CodeNet HTML loader (BeautifulSoup, preserves `<pre>` as fenced blocks) | `src/aitaxo/problems/codenet.py` |
| GPT-4o client (tenacity retry, fenced-code extraction) | `src/aitaxo/generation/openai_client.py` |
| Sandbox runner (subprocess, classifies pass/WA/RE/TLE/CE) | `src/aitaxo/execution/runner.py` |
| End-to-end pipeline | `src/aitaxo/pipeline.py` |
| CLI (`inspect`, `generate`) | `src/aitaxo/cli.py` |
| Config (env-driven) | `src/aitaxo/config.py` |

`Problem.source` is a literal — when adding Codeforces, extend the literal type and add a loader, don't fork the schema.

The sandbox is intentionally thin. RLIMIT_AS is set on Linux only (no-op on macOS). Before scaling beyond a few hundred generations, wrap with Docker/firejail.

Output comparison is lenient: per-line trailing whitespace stripped, final newlines stripped. This matches CodeNet's verification convention. Stricter problems will need per-problem comparators.

## Commands

```bash
# Setup
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env       # fill in OPENAI_API_KEY

# Verify executor (no API key needed)
.venv/bin/python tests/test_runner.py

# Verify problem loader (no API key needed)
PYTHONPATH=src .venv/bin/python -m aitaxo.cli inspect --limit 3

# Run pipeline end-to-end (BURNS API CREDITS)
PYTHONPATH=src .venv/bin/python -m aitaxo.cli generate --limit 5
```

Outputs land in `data/generated/codenet_<model>_<UTC-timestamp>.jsonl`. One JSON record per failure (or all cases if `--save-all`). Each record carries the full problem statement, generated code, raw LLM response, token counts, and per-test execution results — everything needed for downstream labeling.

## External data location

Datasets live outside the repo at `/Users/cdw/VSCode/aria/data/` (override via `AITAXO_DATA_ROOT`). The MVP uses:

- `Project_CodeNet/problem_descriptions/p#####.html` — problem statements
- `Project_CodeNet/derived/input_output/data/p#####/{input,output}.txt` — one sample I/O per problem
- `Project_CodeNet/metadata/p#####.csv` — submission status table (not yet used)

CodeNet only ships **one sample I/O pair per problem**. That's enough to filter out plainly broken generations but doesn't expose edge-case bugs. When the proposal calls for richer test coverage, generate hidden tests from the spec (this is part of the unwritten Spec-Grounded Repair step).

`Codeforces/codeforces/verifiable/*.parquet` (codeforces-cots) is available but unused in MVP — needs `pandas`/`pyarrow` to read.

## Working language

Proposal, labeling rubric, feedback templates are **Korean**. Preserve Korean text verbatim; don't translate category names (Spec-Mismatch, Hallucinated-API, etc.) or prompt strings.

## Next deliverables (from proposal §3)

Not yet implemented — each is a discrete next step:

1. **Multi-provider generation** — Claude + Gemini alongside GPT-4o (extend `generation/`).
2. **Taxonomy labeling tool** — CLI/web UI for 2-author classification + Cohen's κ computation.
3. **Spec-Grounded constraint extractor** — LLM parses statement → structured constraints used as a second oracle.
4. **APR baseline adapters** — wrap FastFixer / PaR / PyDex / CREF to consume the failure JSONL.
5. **Educational feedback generator** — `[spec, buggy_code, category, repair] → "AI misread X as Y"` template.
