# Gold annotation packet

346 items sampled (Cochran 95% / ±5%, stratified by arm × verdict). Each item is
a competitive-programming submission with a confirmed bug. Provenance (human vs AI)
is hidden on purpose — label only the bug.

## What to do

1. Read **CODEBOOK.md** (the taxonomy + examples).
2. **Two annotators independently** fill one CSV each:
   - Annotator 1 → `annotation_annotator1.csv`
   - Annotator 2 → `annotation_annotator2.csv`
3. For each row, open its `detail_file` (under `items/`), decide the bug, and enter
   leaf codes in the **`labels`** column, **semicolon-separated** (e.g. `GE4.2;AE3.2`).
   - If no leaf fits, set **`uncovered`** to `yes` and explain in `notes`.
4. When both CSVs are complete, tell the agent **"annotation complete"** — it will
   validate, compute inter-annotator κ, and emit a disputed-items file for the
   adjudicator.

Do not edit `item_id`, `detail_file`, or `gold_manifest.json`.
