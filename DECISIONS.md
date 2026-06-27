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

## Phase B — judge harness (2026-06-27)
- **Sandbox:** Docker unavailable on host -> hardened subprocess (sandbox-exec network/FS
  isolation + rlimits + process-group teardown + non-root). Full rationale + limits in
  ASSUMPTIONS.md.
- **C++ compiler = GNU g++-16** (Homebrew), not Apple clang: clang lacks `<bits/stdc++.h>`
  and GCC extensions competitive C++ relies on (clang -> 100% oracle CE). Flags
  `-O2 -std=gnu++17 -include cassert`. `-include cassert` is needed because GCC 16 trimmed
  transitive includes that 2021-era code assumed; `gnu++17` enables GNU extensions. An
  era-faithful older GCC (g++-11) is **unusable on this macOS** (links against an SDK whose
  `assert.h` it cannot find). x86 SIMD `#pragma GCC target(...)` lines are stripped (invalid
  on Apple ARM; pure optimization hints, no semantic effect).
- **rlimits:** CPU time + output file size enforced; **RLIMIT_STACK raised to the hard cap
  (~64MB)** for deep competitive recursion (verified: recursion depth 1e6 runs clean, so no
  systemic false-RE); **RLIMIT_AS deliberately NOT set** (on macOS it falsely kills normal
  processes rather than capping real memory).
- **Output comparison:** whitespace-token, **case-insensitive** (Codeforces YES/No
  convention), numeric tokens at **1e-4 relative/absolute tolerance** (stored float answers
  are approximations; 1e-6 rejected valid oracles). Recorded as the harness comparison rule.
- **Judgeable subset (gate):** a problem is judgeable iff its known-correct oracle judges AC
  under the harness. Result: **144/165 judgeable, oracle-AC = 100% on judgeable**; 21 excluded
  — 19 special-judge/interactive (verified: multiple oracle solutions of the same problem
  produce mutually different valid outputs, so static output comparison is invalid), 1
  runtime-incompatible (1580F: ARM/UB segfault unrelated to stack), 1 compiler-incompatible
  (1608G). Excluded set persisted to `artifacts/judgeable_problems.json`; Phases C/D operate
  only on the 144 judgeable problems. This is the standard special-judge/interactive exclusion.

## Phase C — human corpus (2026-06-27)
- **Sampling:** per judgeable problem, judge a seeded random sample of up to
  `max_judge_per_problem = 40` C++ incorrect_solutions, keep up to `cap_per_problem = 10`
  non-AC (uniform random within problem), enforce the >=1 non-AC floor. `sample_seed =
  20260627` (FIXED) for reproducibility. 40 is enough to surface >=10 non-AC while bounding
  cost; the kept 10 mirror the AI cap (symmetry, Section 2.9 rule 6).
- **Unexpected-AC is expected and reported:** ~24% (pilot) of CodeContests incorrect_solutions
  pass our test subset because CodeContests ships only a sample of the original Codeforces
  hidden tests. These are dropped + counted (rule 2); the rate is a reported test-weakness
  metric that motivates a stronger oracle (proposal's Spec-Grounded direction).
- **Enrichment:** each kept record carries judge verdict + peak_time_ms (peak_mem_kb = 0;
  memory is not measured — no reliable RLIMIT_AS on macOS), difficulty_bin, algo_families.

## Phase D — AI generation (2026-06-27)
- **Zero-shot = a single `n = k_max (16)` temperature-1.0 call per problem** (not 16 repeated
  calls): identical prompt+params would collide in the LLM cache, so one batch of 16 yields
  the diverse sample set; keep up to 10 non-AC (mirror human cap). Shortfall (<10 non-AC) is
  allowed and recorded.
- **Self-reflection:** conversation history grows each turn (initial D.2 attempt + up to
  n_iters = 5 D.3 repair turns fed verdict + one failing test), so each turn has a distinct
  cache key; stop on AC; full trajectory persisted. Generator = pinned snapshot
  `gpt-3.5-turbo-0125` (contamination-critical). `max_tokens = 2048` (non-FIXED). No oracle is
  ever shown to the generator.
- Smoke test (1575A): zero-shot AC 3 / WA 9 / CE 4, kept 10 non-AC; self-reflection WA->AC.

## Phase D + finalize — results (2026-06-27)
- AI generation (gpt-3.5-turbo C++, 144 judgeable problems): 2304 zero-shot samples,
  **88 AC (3.8% pass)** — very low, as expected for leakage-free post-2021-09-21 CF problems;
  1 no-code; 1423 non-AC kept (cap 10); 144/144 problems with >=1 AI non-AC; self-reflection
  solved 13.
- **Final dataset (Section 2.9 rule 5) = both-arm intersection = 142 problems**
  (human-only 0, ai-only 2). human non-AC 1397, AI non-AC 1403 (~balanced arms, 2800 total).
  artifacts/dataset/{final.jsonl,summary.json}.

## Phase F prep — taxonomy pinned from authors' repo (2026-06-27)
- Wei et al. taxonomy pinned from github.com/minnanWei/LLMs-Competitive-Program-Generation
  (README Tables 1-2) into `src/taxonomy/taxonomy.py` (single source for codebook + judge):
  **6 GE families / 13 leaves, 6 AE families / 18 leaves = 31 leaves.** Codes + family/leaf
  names are verbatim; one-line operational definitions + one example per leaf are this study's
  codebook authoring (the source provides names only) and are marked as such.
- **Language-dependent leaves (per the source) = GE2.1, GE2.2 (compilation / language-specific
  syntax), GE6.1, GE6.2 (overflow / implicit type conversion).** These directly justify the
  single-C++ design: GE6.1 integer overflow is reachable in C++ but not Python3 (arbitrary
  precision), and GE2.1 compile errors are C++-specific. Recorded for the construct-validity
  note (Section 2.4) and Threats.
- **Corrected the placeholder `TAG_TO_FAMILY`:** the earlier mapping mislabeled AE codes
  (had AE3=graphs, AE5=dp, AE6=brute force). Pinned meanings are AE1 Math, AE2 Greedy,
  **AE3 Dynamic Programming**, AE4 Divide&Conquer, AE5 Recursion/Memoization, **AE6 Graph
  Traversal/Search**. Mapping moved to the taxonomy module; `meta.json` algo_families
  recomputed from raw cf_tags (99/165 changed). **meta.json is the authoritative source for
  problem covariates** (difficulty_bin, algo_families, cf_tags); Phase G joins submissions to
  meta by problem_id rather than trusting baked corpus copies.

## Record for paper (2026-06-27, per user)
- **Unexpected-AC = 19.5%** of judged human incorrect_solutions pass our test subset ->
  evidence that CodeContests public/sample tests are weaker than the original Codeforces hidden
  suite, which **justifies harness re-judging** (we keep only harness-confirmed non-AC). Stage
  as a Threats sentence.
- **AI zero-shot pass rate = 3.8%** on post-2021-09-21 leakage-free Codeforces problems ->
  evidence the **contamination control is working** (a memorizing model would score far higher);
  use in Results/Threats.
- **Human non-AC count 1,397 is AFTER the <=10/problem cap** (137 problems at the cap of 10,
  5 below; max per problem = 10). AI non-AC 1,403 is likewise post-cap. Arms are ~balanced.

## Phase F — gold sampling (2026-06-27)
- Cochran proportion sizing on the final dataset (N=2800): n0=384.2 (z=1.96, p=0.5, e=0.05),
  after finite-population correction target=338; with a per-stratum floor of 5 the realized
  sample is **346 items**, stratified by **arm × verdict** (8 cells, all represented; WA
  dominates: human 158, AI 151; CE/RE/TLE at the floor except AI-CE=12). gold seed 20260627.
- Packet emitted to `human/` (provenance-blind, verified no arm leakage in item files):
  README.md, CODEBOOK.md (31 leaves + examples, lang-dependent marked), items/g0001..g0346.md
  (problem, submission, verdict, first failing test, messages, reference oracle), two annotator
  CSVs, gold_manifest.json (item→submission scoring key). `/human/items/` is gitignored
  (regenerable); README/CODEBOOK/CSVs/manifest are tracked. STOP for human labeling.
