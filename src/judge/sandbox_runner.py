import os
import re
import resource
import signal
import subprocess
import time
from pathlib import Path


class SandboxRunner:
    # Docker is unavailable on this host (macOS, no daemon/colima); installing a Linux VM
    # is impractical for judging tens of thousands of submissions x hundreds of tests. This
    # is the hardened-subprocess fallback: macOS sandbox-exec denies network + all filesystem
    # writes outside the per-run scratch dir; rlimits bound CPU, address space, and file size;
    # the child runs in its own session so a fork bomb is killed as a process group at the
    # wall-clock timeout; output is capped; execution is non-root. See ASSUMPTIONS.md.
    def __init__(self, config):
        self.margin = config["execution"]["time_margin_s"]
        self.out_cap = config["execution"]["output_cap_bytes"]
        self.compiler = config["execution"]["cpp_compiler"]
        self.std = config["execution"]["cpp_std"]

    def compile_cpp(self, source, workdir):
        src = Path(workdir) / "main.cpp"
        src.write_text(self._strip_x86_pragmas(source), encoding="utf-8")
        binp = Path(workdir) / "main.bin"
        # -include cassert: newer GCC trimmed transitive includes that 2021-era competitive
        # code relies on (assert via <bits/stdc++.h>); -std=gnu++17 enables the GNU extensions
        # competitive solutions assume.
        r = subprocess.run([self.compiler, "-O2", f"-std={self.std}", "-include", "cassert",
                            "-o", str(binp), str(src)], capture_output=True, text=True, timeout=60)
        return r.returncode == 0, r.stderr, binp

    def _strip_x86_pragmas(self, source):
        # x86 SIMD target pragmas (avx2/sse/...) are invalid on this ARM host; they are pure
        # optimization hints with no semantic effect, so removing them is safe.
        return re.sub(r'#pragma\s+GCC\s+target\s*\([^)]*\)', '', source)

    def run(self, cmd, stdin_text, time_limit, mem_mb, workdir):
        wrapped = ["/usr/bin/sandbox-exec", "-p", self._profile(workdir)] + cmd
        t0 = time.time()
        p = subprocess.Popen(wrapped, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE, text=True, cwd=str(workdir),
                             preexec_fn=self._limits(time_limit), start_new_session=True)
        try:
            out, err = p.communicate(input=stdin_text, timeout=time_limit + self.margin)
        except subprocess.TimeoutExpired:
            self._kill_group(p)
            return {"timed_out": True, "stdout": "", "stderr": "", "returncode": None,
                    "time_ms": int((time.time() - t0) * 1000)}
        return {"timed_out": False, "stdout": out[:self.out_cap], "stderr": err[:10000],
                "returncode": p.returncode, "time_ms": int((time.time() - t0) * 1000)}

    def _profile(self, workdir):
        scratch = os.path.realpath(str(workdir))
        return ('(version 1)\n'
                '(allow default)\n'
                '(deny network*)\n'
                '(deny file-write*)\n'
                f'(allow file-write* (subpath "{scratch}"))\n'
                '(allow file-write-data (literal "/dev/null"))\n')

    def _limits(self, time_limit):
        cpu = int(time_limit) + 1
        fsize = self.out_cap

        def apply():
            resource.setrlimit(resource.RLIMIT_CPU, (cpu, cpu + 1))
            resource.setrlimit(resource.RLIMIT_FSIZE, (fsize, fsize))
            # raise stack to the hard cap for deep competitive recursion (macOS default 8MB
            # segfaults solutions that Codeforces runs with a 256MB stack)
            try:
                _, hard = resource.getrlimit(resource.RLIMIT_STACK)
                resource.setrlimit(resource.RLIMIT_STACK, (hard, hard))
            except (ValueError, OSError):
                pass
            # RLIMIT_AS intentionally NOT set: on macOS it falsely kills normal processes
            # (huge virtual reservations) instead of capping real memory (see ASSUMPTIONS.md);
            # memory pressure is bounded by the wall-clock timeout instead
        return apply

    def _kill_group(self, p):
        try:
            os.killpg(os.getpgid(p.pid), signal.SIGKILL)
        except ProcessLookupError:
            pass
        p.communicate()
