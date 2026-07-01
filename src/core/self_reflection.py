import asyncio
import json
import re
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from src.execute.validator import Validator
from src.models.gpt import Gpt


class SelfReflection:
    # Self-Refine on the zero-shot AI bugs. Each non-AC submission is fed back into the SAME
    # conversation that produced it (system -> zero-shot user -> assistant=buggy code), then the
    # model is shown its results on the PUBLIC example tests (what a contestant sees on an online
    # judge) and asked to revise. Up to `rounds` revise turns, early stop when the revision judges AC
    # over all tests. Trajectories are written to <pid>/ai/<model>/reflect.jsonl, linked by index to
    # the original incorrect.jsonl bug. Only the contamination-clean arm (gpt-3.5-turbo) is reflected.
    def __init__(self, config):
        r = config["reflect"]
        self.models = r["models"]
        self.temp = r["temperature"]
        self.rounds = r["rounds"]
        self.concurrency = r["concurrency"]
        self.workers = r["workers"]
        self.data = Path(config["paths"]["problems"])
        self.gpt = Gpt(config)
        self.validator = Validator(config)
        ai = Path(__file__).resolve().parent.parent / "prompts" / "ai"
        self.system = (ai / "system.md").read_text(encoding="utf-8").strip()
        self.user_tmpl = (ai / "user.md").read_text(encoding="utf-8")
        self.reflect_tmpl = (ai / "reflection.md").read_text(encoding="utf-8")

    def run(self, limit=None, models=None, problem=None):
        return asyncio.run(self._run(limit, models, problem))

    async def _run(self, limit, models, problem):
        models = models or self.models
        items = self._items(models, problem)
        if limit:
            items = items[:limit]
        self.api = asyncio.Semaphore(self.concurrency)
        self.pool = ThreadPoolExecutor(max_workers=self.workers)
        results = await asyncio.gather(*[self._reflect(it) for it in items])
        self.pool.shutdown()
        by = defaultdict(list)
        for r in results:
            by[(r["model"], r["pid"])].append(r)
        for (m, pid), rs in by.items():
            rs.sort(key=lambda r: r["idx"])
            with (self.data / pid / "ai" / m / "reflect.jsonl").open("w", encoding="utf-8") as f:
                for r in rs:
                    rec = {k: r[k] for k in ("idx", "rounds_used", "final_verdict", "fixed",
                                             "final_source", "trajectory")}
                    f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        out = {}
        for m in models:
            rs = [r for r in results if r["model"] == m]
            fixed = sum(1 for r in rs if r["fixed"])
            out[m] = {"bugs_reflected": len(rs), "fixed": fixed,
                      "fix_rate": round(fixed / len(rs), 4) if rs else 0.0,
                      "still_buggy": len(rs) - fixed}
        return out

    def _items(self, models, problem=None):
        items = []
        for d in sorted(self.data.glob("*/")):
            if not (d / "meta.json").exists() or (problem and d.name != problem):
                continue
            user = self._prompt(d)
            for m in models:
                f = d / "ai" / m / "incorrect.jsonl"
                if not f.exists():
                    continue
                for idx, line in enumerate(l for l in f.read_text(encoding="utf-8").split("\n") if l):
                    items.append({"model": m, "pid": d.name, "idx": idx, "user": user,
                                  "source": json.loads(line)["source"]})
        return items

    async def _reflect(self, it):
        d = self.data / it["pid"]
        messages = [{"role": "system", "content": self.system},
                    {"role": "user", "content": it["user"]},
                    {"role": "assistant", "content": self._fence(it["source"])}]
        code = it["source"]
        final = await self._verdict(d, code)
        trajectory = []
        for _ in range(self.rounds):
            feedback = await self._feedback(d, code)
            messages.append({"role": "user", "content": self.reflect_tmpl.replace("{feedback}", feedback)})
            text = await self._gen(it["model"], messages, it["idx"])
            messages.append({"role": "assistant", "content": text})
            code = self._extract(text) or code
            final = await self._verdict(d, code)
            trajectory.append({"round": len(trajectory) + 1, "verdict": final})
            if final == "AC":
                break
        return {"model": it["model"], "pid": it["pid"], "idx": it["idx"],
                "rounds_used": len(trajectory), "final_verdict": final, "fixed": final == "AC",
                "final_source": code, "trajectory": trajectory}

    async def _gen(self, model, messages, nonce):
        async with self.api:
            return await self.gpt.chat(model, messages, self.temp, nonce)

    async def _verdict(self, d, code):
        loop = asyncio.get_event_loop()
        res = await loop.run_in_executor(self.pool, self.validator.judge, str(d), code)
        return res["verdict"]

    async def _feedback(self, d, code):
        loop = asyncio.get_event_loop()
        pub = await loop.run_in_executor(self.pool, self.validator.public_results, str(d), code)
        if not pub["compiled"]:
            return "Your code failed to compile. Compiler error:\n" + pub["compiler_stderr"]
        blocks = []
        for i, t in enumerate(pub["tests"], 1):
            status = "PASS" if t["pass"] else "FAIL"
            blocks.append(f"Example {i} [{status}]\ninput:\n{t['input'].rstrip()}\n"
                          f"expected:\n{t['expected'].rstrip()}\nyour output:\n{t['actual'].rstrip()}")
        note = ("It passes all the example tests above but is still rejected on the hidden tests, so "
                "there is a deeper bug. Reconsider your logic and edge cases."
                if all(t["pass"] for t in pub["tests"]) else "Fix the failing example(s) above.")
        return "Results on the example tests:\n\n" + "\n\n".join(blocks) + "\n\n" + note

    def _prompt(self, d):
        desc = (d / "description.txt").read_text(encoding="utf-8").strip()
        return self.user_tmpl.replace("{description}", desc)

    def _fence(self, code):
        return f"```cpp\n{code}\n```"

    def _extract(self, text):
        m = re.search(r"```(?:[a-zA-Z+]*)\n(.*?)```", text, re.DOTALL)
        if m:
            return m.group(1).strip() or None
        if "#include" in text or "int main" in text:
            return text.strip()
        return None
