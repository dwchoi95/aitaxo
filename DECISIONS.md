# DECISIONS

Append-only log of concrete choices (especially non-FIXED config values), with rationale.

## Phase 0 (2026-06-27)

- **Python 3.13 (venv `env/`) instead of plan-default 3.11.** Use the existing `env/`
  virtualenv (Python 3.13.7) the user created. 3.13 is compatible with all required
  packages; pinning the venv avoids a redundant rebuild. (Plan 0.5 allows adapting the
  stack if justified and logged.)
- **Sandbox Dockerfiles live in `judge_docker/`, not `env/`.** The plan puts sandbox
  Dockerfiles in `env/`, but `env/` is our Python virtualenv. To avoid the clash, the
  Phase-B Dockerfiles go in `judge_docker/`.
- **Test filename convention: `tests/<pkg>/test_<step>.py`** (with the `test_` prefix),
  mirroring `src/<pkg>/<step>.py` 1:1 (plan 3.0.1 asks to pick one convention).
- **`generator.k_max = 16`** (plan range 15-20). gpt-3.5-turbo has a low pass rate on
  these competitive problems, so most attempts are buggy; 16 attempts reliably yields
  the target of >=10 non-AC submissions for most problems while capping wasted calls.
  Raise and document if the Phase-G saturation curve still climbs.
- **`human_arm.cap_per_problem = 10`.** Mirrors the AI side (plan 2.2 symmetry) so no
  single high-traffic problem dominates; sampled uniformly within a problem+language
  when over the cap.
- **`difficulty_bins.edges = [1400, 1900, 2400]`** (labels easy/medium/hard/expert).
  Provisional, roughly aligned with Codeforces Div2/Div1 difficulty bands; finalized in
  Phase A after inspecting the test-split `cf_rating` distribution.
- **`repair.model = gpt-5.5`, `repair.attempts = 3`.** A strong coder distinct from the
  generator (gpt-3.5-turbo) to produce verified minimal patches for label grounding
  (E.3); 3 attempts caps cost while allowing retries.
- **`prompt.size_cap_chars = 6000`** (head+tail truncation). Bounds context for large
  CodeContests tests/descriptions (plan Appendix D size cap).
- **`dataset.source_restriction = CODEFORCES`.** Plan A.6 default: restrict the main
  study to Codeforces-sourced test problems for clean dates + full `cf_rating`/`cf_tags`
  needed by RQ2. Count reported in Phase A.
- **`judge.m = 5`** (plan default; may drop to 3 to cut cost, logged if so).

## Phase A (2026-06-27)
- **difficulty_bins finalized = edges [1400,1900,2400]** (easy/medium/hard/expert). On the
  165 Codeforces test problems the resulting counts are easy 53 / medium 25 / hard 36 /
  expert 51 (rating 800-3500, median 1900) — a workable spread for CMH/logistic
  stratification; kept as provisionally set.
- **Problem set P = 165 Codeforces-sourced test problems** (source==CODEFORCES). All have
  >=1 oracle solution and >=1 test (median 203 tests/problem). Human incorrect coverage:
  C++ 164/165, Python3 114/165 -> C++ is the larger arm (relevant to the Phase D primary-
  language review). The validation split (117 problems) is stashed in data/sensitivity/
  for the contamination probe only, never merged.

## Phase A data layout revision (2026-06-27, user request)
- Per-problem storage is JSONL-split: `tests.jsonl` (one `{kind,input,output}` per line,
  kind in public/private/generated); `<lang>/correct.jsonl` and `<lang>/incorrect.jsonl`
  (one `{idx, code}` per line) for lang in {cpp, python3}. Replaces the earlier single
  JSON blobs so records are separable.
- code_contests solutions carry ONLY `code` + `language` (anonymized): no userid, no
  timestamp, no per-submission verdict/time/memory. `verdict`, `exec_time_ms`,
  `peak_mem_kb` are produced by our sandbox judge and enriched into `incorrect.jsonl`
  during Phase B (oracle self-test) / Phase C (human) / Phase D (AI). `tests.jsonl` keeps
  `kind` because the public sample tests feed the generation prompt's example I/O.
- problems/ (test split, post-2021-09-21) is the main study; sensitivity/ (validation
  split, pre-cutoff) is the contamination probe only and is never merged.

## Plan revision — Decision 1: single language C++ (2026-06-27, confirmed)
- **Analysis language fixed to C++; Python3 dropped from the pipeline.** Rationale:
  (a) the reused Wei et al. taxonomy has language-dependent leaves — GE4 integer
  overflow/precision is C++-specific and essentially unreachable in Python3's
  arbitrary-precision ints; GE5.1 compile errors and GE5.2 slow unsynchronized I/O
  manifest differently per language — so a single C++ arm maximizes taxonomy fit and
  removes language as a confound; (b) C++ is the competitive-programming standard;
  (c) data volume: collected human non-AC = 17,670 C++ vs 7,273 Python3 (Java 8,463,
  Python2 166), and C++ coverage is uniform across difficulty bins while Python3 is
  sparse on hard/expert problems (expert: 13/51 problems, 92 submissions).
- Plan edits: 2.2 -> C++ single FIXED; removed the Phase D language-review STOP (0.3 and
  Phase D step 5); simplified Phase B/C/D to single-language; 2.4 gained a construct-
  validity note + instruction to pin language-dependent leaves from the authors' repo
  (github.com/minnanWei/LLMs-Competitive-Program-Generation); Phase H Threats now states
  single-language control removes the language confound, with Python3 generalization as
  future work; config.yaml languages=[cpp], primary_language=cpp.
- Already-collected Python3/Java/Python2 human data is retained for the descriptive
  language-distribution report only and never enters the analysis pipeline (not deleted).

## Plan revision — Decision 2: final dataset composition rules (2026-06-27, confirmed)
- Added Section 2.9 (authoritative) with the one-line definition
  **Final dataset = {problems with (human C++ non-AC >=1) AND (AI C++ non-AC >=1)}**
  and 8 rules: (1) problem start = test ∩ Codeforces ∩ post-2021-09-21; (2) human filter
  = C++ non-AC after harness re-judge (unexpected AC dropped+counted); (3) AI gen = C++
  gpt-3.5-turbo until 10 non-AC (cap k_max 15-20); (4) per-problem floor >=1 non-AC;
  (5) primary analysis on the both-arm intersection, report intersection count + per-arm
  totals; (6) symmetric ~10 cap with uniform random sampling (seed logged), no forced
  1:1 count match; (7) sparse-category collapse to parent family (expected freq <5);
  (8) appendix 1:1 matched sensitivity analysis. Rules are operationalized in Phase A
  (1,2,4), end of Phase D (3,5,6), and Phase G (5,7,8).
