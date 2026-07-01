# Root-Cause Human Audit Pack

This local pack contains 120 wrong-answer submissions sampled from the three
zero-shot arms: human, gpt-3.5-turbo-0125, gpt-5.4-nano. Each item includes the problem
statement, rejected code, one accepted reference implementation, and the first failing test.

Before labeling, read `codebook.md`. A spreadsheet-friendly copy of the same taxonomy is in
`taxonomy.csv`.

Fill `label.csv`:
- `root_labels`: comma-separated taxonomy leaf labels, e.g., `AE1.1,GE2.1`
- `root_rationale`: one or two sentences explaining the demonstrated root cause

Skipped items without a reproducible WA first-failing test: []
