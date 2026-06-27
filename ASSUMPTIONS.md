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
