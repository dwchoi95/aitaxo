# Reproducing "Do AI and Human Programmers Fail Differently?"

This rebuilds every artifact from a clean clone: dataset → gold labels → classifications →
`results/` (the tables/figures/numbers the paper cites) → `paper/main.pdf`. `run.py` is the single
entry point; there is no Makefile.

## 0. What you need

- **macOS.** The execution sandbox uses `sandbox-exec` (network + filesystem-write denial) plus
  `resource.setrlimit` (CPU, file-size, stack). There is no Docker dependency. On Linux the harness
  has no `sandbox-exec`; port `src/judge/sandbox_runner.py` before running untrusted code.
- **Python 3.11+** (developed on 3.13).
- **API keys**, exported in a gitignored `.env` at the repo root (loaded automatically by `run.py`):
  - `OPENAI_API_KEY` — AI code generation (`gpt-3.5-turbo-0125`) and the selected judge (`gpt-5.5`).
  - `ANTHROPIC_API_KEY` — the judge-selection slate (`claude-sonnet-4-6`).
- **Cost.** A cold run spends real money (full classification of 2800 submissions was ~\$180 on the
  judge alone). Every LLM call is cached under `logs/cache` keyed by model + params + messages, so a
  re-run with a warm cache is free and deterministic. Keep `logs/cache` to reproduce at \$0.

## 1. Set up

```bash
python -m venv env
env/bin/pip install -r requirements.txt
printf 'OPENAI_API_KEY=sk-...\nANTHROPIC_API_KEY=sk-ant-...\n' > .env
env/bin/python run.py test          # 41 tests should pass
```

## 2. One command

```bash
env/bin/python run.py all
```

`all` runs every phase in order, honoring the cache. It **stops at two human-labeling gates** and
prints what to do; after each, fill the named CSVs and re-run `run.py all` (completed/cached work is
reused, so it resumes where it stopped):

1. **Gold annotation gate.** After gold sampling, two annotators each fill
   `human/annotation_annotator{1,2}.csv` (provenance-blind packet + codebook are emitted next to
   them; see the generated `README`). `run.py all` resumes by computing inter-annotator κ and
   emitting `human/annotation_adjudication.csv` (disputed items only).
2. **Gold adjudication gate.** A third labeler fills `final_labels` for the disputed items in
   `human/annotation_adjudication.csv`. `run.py all` resumes by finalizing the gold set, selecting
   the judge, classifying both arms, and writing `results/`.

It finishes by fetching references from DBLP and printing `ALL_DONE`.

## 3. Phases and what each needs (if you prefer to run them individually)

| Step | Command | Needs |
|------|---------|-------|
| A. Problem set + judgeable gate | `run.py build-problems`, `run.py check-judge` | network (HF dataset) |
| B/C. Human arm | `run.py build-human` | — |
| C. AI arm (generation + self-reflection) | `run.py build-ai` | `OPENAI_API_KEY` |
| D. Finalize dataset (both-arm intersection) | `run.py finalize-dataset` | — |
| Gold sample → **human** | `run.py prepare-gold` | human annotation |
| Gold κ + disputes → **human** | `run.py adjudicate-gold` | human adjudication |
| Gold finalize | `run.py finalize-gold` | — |
| F. Judge selection | `run.py select-judge` | `OPENAI_API_KEY`, `ANTHROPIC_API_KEY` |
| E. Classify + analyze | `run.py phase-e` | `OPENAI_API_KEY` (cached) |
| Analyze only (from cached classifications) | `run.py analyze --classifications artifacts/classifications/gpt-5-5_final.jsonl --rq3 artifacts/classifications/gpt-5-5_rq3_submissions.jsonl` | — |
| References | `run.py fetch-refs` | network (DBLP) |

## 4. Build the paper

```bash
cd paper && latexmk -pdf main.tex        # -> paper/main.pdf (single main.tex + references.bib)
```

`paper/main.tex` reads figures from `../results/figures/` and every numeric macro it defines traces
to a file under `results/` (e.g. `results/SUMMARY.md`, `results/tables/*.csv`). `references.bib` is
fetched verbatim from DBLP; provenance for each entry is in `logs/refs_provenance.json`.

## 5. Determinism check

The analysis is fully deterministic given the classifications: re-running step E's analysis on the
cached classification files regenerates `results/SUMMARY.md` byte-for-byte. LLM steps are
non-deterministic in general, which is why every call is cached and the self-consistency samples
(`m=3`) are logged; with `logs/cache` present the whole pipeline reproduces exactly.
