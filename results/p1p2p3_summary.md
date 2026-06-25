# P1–P3: Strengthening analyses (AI vs human, sub-types, repair baseline)

Three follow-up analyses run on the full-test, 10-generations-per-task dataset
(428 problems, 3,691 AI bugs, 1,203 paired human bugs).

## P1 — AI vs Human bug distribution (`p1_human_vs_ai.py`)
Judged every human `faulty.py` against the **full hidden tests** and classified by
the same coarse categories as AI bugs; compared with a chi-square test.

| Category | AI (3,691) | Human (1,203) |
|---|---|---|
| Wrong answer (WA) | 76.1% | 91.5% |
| Time limit (TLE)  | 13.7% | 6.1% |
| Runtime error (RE)| 9.2%  | 2.4% |
| Compile/output(CE)| 1.1%  | 0.0% |

- **Distributions differ significantly**: χ²=139.8, dof=3, p≈4.1×10⁻³⁰.
- AI fails in **more diverse/severe** ways (2–4× more TLE/RE/CE); humans concentrate on WA.
- **Locality**: human fault locations are **100% single-line** (median 1). Human bugs
  are localized slips; AI WA bugs are whole-program wrong approaches (S2/S4 = 90%) with
  no single "buggy line." → core evidence that AI bugs differ *in kind*.
- (1 of 1,204 human faulty passed our full tests and was excluded.)

## P2 — Sub-type labeling of Spec-Misinterpretation (`p2_subtype_label.py`)
All 2,808 WA bugs labeled into S1–S5 by an independent annotator model
(`gpt-4o-mini`, different from the generator); reliability via a second independent pass.

| Sub-type | Count | Share |
|---|---|---|
| S2 core-condition oversimplification | 1,609 | 57.3% |
| S4 failed paradigm recognition       | 918   | 32.7% |
| S3 wrong algorithm / formula         | 182   | 6.5% |
| S1 output / case oversimplification  | 54    | 1.9% |
| S5 edge / language-semantics         | 45    | 1.6% |

- **Cohen's κ = 0.759** (raw agreement 0.86, n=300) → meets target κ≥0.7.
- **S2 + S4 = 90%**: LLM semantic defects are mostly *replacing the real requirement
  with an easier proxy* or *not recognizing the required algorithm*.

## P3 — LLM repair baseline (`p3_llm_apr.py`)
280 difficulty-stratified WA bugs (70/band). Each repairer gets problem + buggy code +
first failing test; the patch is re-judged on the full tests.

| Repairer | Easy | Med | Hard | V.hard | Total |
|---|---|---|---|---|---|
| Self (`gpt-3.5-turbo`)  | 3/70  | 0/70 | 0/70 | 0/70 | **1.1%** |
| Cross (`gpt-4o-mini`)   | 26/70 | 4/70 | 0/70 | 0/70 | **10.7%** |

- **Self-repair collapses to 1.1%** — the generating model reproduces its own
  misunderstanding (direct consequence of systematicity; benchmark limitation L3).
- **Cross-model only 10.7%**, concentrated on easy problems; 0% on hard/very-hard.
- Dominant sub-types resist repair even with the failing test given: S2 19/170 (cross),
  S4 5/84 (cross). → motivates spec-grounded repair (tests-only oracle is insufficient).

## Paper integration
- `main.tex` (5 pp): new subsections *AI Bugs versus Human Bugs* (tab:aihuman) and
  *Repairability* (tab:apr); sub-type table (tab:subtypes) + κ; abstract/conclusion updated.
- `benchmark.tex` (7 pp): AI-vs-human added to RQ1; sub-type distribution + κ; LLM-APR
  numbers and table in RQ3; L3 and RA3 updated to the measured rates.
