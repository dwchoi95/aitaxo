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
