# ASSUMPTIONS

Append-only log of assumptions, limitations, and anything flagged for the human.

## Phase 0 (2026-06-27)
- Sandbox: the plan specifies Docker for untrusted-code execution. Docker availability
  on this machine is unverified; if Docker is unavailable at Phase B, the fallback is a
  hardened subprocess sandbox (no network, rlimits, scratch-only FS, non-root) — to be
  decided and logged at Phase B.
- Wei et al. (2025) taxonomy leaf codes/examples must be retrieved from the authors'
  public artifact and pinned before classification (plan 2.4 caveat); the GE*/AE* codes
  in Appendix A are the labeling target until the canonical list is pinned.

## Phase B — sandbox (2026-06-27)
- **Docker is unavailable** on this host (no docker CLI/daemon/Docker.app; no colima/podman).
  Installing a Linux VM (colima) is possible via Homebrew but **impractical** for judging
  ~tens of thousands of submissions x hundreds of tests at acceptable throughput, and the
  host/container split complicates the API-key-bearing generation steps. Per the user's
  authorization we use a **hardened subprocess sandbox** instead.
- **Isolation provided:** macOS `sandbox-exec` profile denies **all network** and **all
  filesystem writes outside the per-run scratch dir** (verified); rlimits bound **CPU time**,
  **address space** (best-effort — RLIMIT_AS is unreliable on macOS), and **output file
  size**; the child runs in its **own session** so a fork bomb is killed as a process group
  at the **wall-clock timeout**; **output is capped**; execution is **non-root** (uid 501).
- **Limitations:** RLIMIT_AS memory capping is best-effort on macOS; Linux seccomp syscall
  filtering is not available (sandbox-exec category denials + rlimits are used instead). For
  an untrusted-at-scale production release, run inside Docker/Linux. The submissions here are
  competitive-programming solutions (stdin->compute->stdout), a low-adversarial threat model.
- **Paper threats sentence (stage for Phase H):** "Untrusted submissions were executed in a
  hardened subprocess sandbox (network- and filesystem-isolated via the OS sandbox, with CPU,
  memory, output, and wall-clock limits and process-group teardown) rather than Docker, which
  was unavailable on the host; this does not affect verdicts, only the isolation mechanism."

## Phase H — references source (2026-06-28)
- **Plan 11.2 mandates Semantic Scholar** for verbatim BibTeX. The keyless Semantic Scholar API
  rate-limited this host persistently (HTTP 429) from both the fetcher and WebFetch, so it was
  **unusable**. We instead fetch verbatim `.bib` from **DBLP** (the authoritative CS bibliography)
  by hand-verified DBLP key — `ReferenceFetcher` now targets DBLP and logs provenance (DBLP key,
  title, venue, DOI) to `logs/refs_provenance.json`. This preserves the rule's intent (real,
  verifiable, never hand-written references); only the source differs. All 9 entries in
  `paper/references.bib` are provenance-backed; none are hand-authored.
- **Wei et al. correction:** the earlier hand-written stub used a fabricated title; the real paper
  is *Evaluating and improving LLM-based competitive program generation* (Inf. Softw. Technol.,
  2026), which contains the GE/AE taxonomy used as our instrument.

## Phase I — reproducibility (2026-06-28)
- `run.py all` is the single-entry reproduction driver; it honors the LLM cache and stops at the two
  human-labeling gates. A full cold run costs real API money (~\$180 for classification); a warm
  cache (`logs/cache`) reproduces at \$0 and deterministically. Sandbox is macOS `sandbox-exec` +
  rlimits (no Docker — see Phase B); on Linux `src/judge/sandbox_runner.py` must be ported.
