# PROGRESS

Phase-by-phase checklist with validation-gate results (see RESEARCH_EXECUTION_PLAN.md).

| Phase | Status | Validation gate | Date |
|---|---|---|---|
| 0 — Setup | DONE | pytest 4 passed; config loads; LlmClient dry-run; data/artifacts/results-sub/logs/paper ignored; tests mirror src | 2026-06-27 |
| A — Problem set | DONE | 165 problems; manifest==165; 0 missing oracle/tests; incorrect C++164/Py3 114; pytest 8 | 2026-06-27 |
| B — Judge harness | DONE | hardened sandbox; 144 judgeable / 21 excluded; oracle 100% AC gate on judgeable subset | 2026-06-27 |
| C — Human corpus | DONE | harness-confirmed non-AC kept (≤10/problem); 19.5% unexpected-AC dropped+counted | 2026-06-27 |
| D — AI generation | DONE | gpt-3.5-turbo C++; 3.8% zero-shot AC (contamination control holds); self-reflection trajectories; intersection 142 problems / 2800 subs (1397 human + 1403 AI) | 2026-06-28 |
| F — Gold + judge select | DONE | gold 346 items, inter-annotator κ=0.62; judge=gpt-5.5 (micro-F1 0.449>claude 0.359); prompt v3 (code-grounded) family F1 0.66 / leaf 0.58 | 2026-06-28 |
| E — Classification | DONE | 2800 submissions classified; resilient resume past a quota stop via LLM cache | 2026-06-28 |
| G — Analysis | DONE | RQ1 V=0.37, GE1 AI 40.1% vs human 10.7% (h=0.71); RQ2 GEE OR=6.9; RQ3 persistence; saturation 23/31; GE1 gold-validated (h=0.61) | 2026-06-28 |
| H — Paper | DONE | single main.tex+references.bib, 10pt; 9 DBLP-verified refs (all cited+provenance-backed); Discussion/RQ4/pipeline fig; Korean glosses; meta-scan 0; 5pp, 0 undefined | 2026-06-28 |
| I — Repro | DONE | `run.py all` (2 human gates, cache-honoring) + `repro/REPRODUCE.md`; analysis reproduces results/SUMMARY.md byte-for-byte; docs current | 2026-06-28 |
