import asyncio
import json
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from src.execute.validator import Validator
from src.models.gpt import Gpt


class AiSubmission:
    # Zero-shot AI submission generation, one corpus per model. For each kept problem, prompt the
    # model (PaR-style: task framing + the problem description, which already carries the input/output
    # format and examples) and draw a FIXED budget of k_max samples at temperature 1.0 -- no early
    # stop, every generation kept. Equal sampling effort makes the arms comparable, and the non-AC
    # yield then reflects each model's true failure rate. Generations are fired as concurrent async
    # calls; each is validated by the same sandbox (public+private) as the human submissions. Results
    # go to <pid>/ai/<model>/{correct,incorrect}.jsonl. gpt-3.5-turbo is the contamination-clean
    # primary arm; newer models (e.g. gpt-5.4-nano) are contrast arms whose contamination is NOT
    # controlled (they were likely trained on these problems) and which therefore yield few bugs.
    def __init__(self, config):
        b = config["ai_submission"]
        self.models = b["models"]
        self.temp = b["temperature"]
        self.k_max = b["k_max"]
        self.min_incorrect = b["min_incorrect"]
        self.concurrency = b["concurrency"]
        self.workers = b["workers"]
        self.data = Path(config["paths"]["problems"])
        self.gpt = Gpt(config)
        self.validator = Validator(config)
        prompts = Path(__file__).resolve().parent.parent / "prompts" / "ai"
        self.system = (prompts / "system.md").read_text(encoding="utf-8").strip()
        self.user_tmpl = (prompts / "user.md").read_text(encoding="utf-8")

    def run(self, limit=None, models=None):
        return asyncio.run(self._run(limit, models))

    async def _run(self, limit, models):
        models = models or self.models
        pids = sorted(p.name for p in self.data.glob("*/") if (p / "meta.json").exists())
        if limit:
            pids = pids[:limit]
        self.api = asyncio.Semaphore(self.concurrency)
        self.pool = ThreadPoolExecutor(max_workers=self.workers)
        results = await asyncio.gather(*[self._process(m, pid) for m in models for pid in pids])
        self.pool.shutdown()
        out = {}
        for m in models:
            rs = [r for r in results if r["model"] == m]
            out[m] = {"problems": len(rs),
                      "total_attempts": sum(r["attempts"] for r in rs),
                      "ai_correct": sum(r["ac"] for r in rs),
                      "ai_incorrect": sum(r["non_ac"] for r in rs),
                      "problems_below_min_incorrect": sum(1 for r in rs if r["non_ac"] < self.min_incorrect)}
        return out

    async def _process(self, model, pid):
        # fixed budget: exactly k_max samples, no early stop; keep every generation's verdict
        d = self.data / pid
        user = self._prompt(d)
        texts = await asyncio.gather(*[self._gen(model, user, i) for i in range(self.k_max)])
        codes = [c for c in (self._extract(t) for t in texts) if c]
        verdicts = await asyncio.gather(*[self._judge(d, c) for c in codes])
        correct = [c for c, v in zip(codes, verdicts) if v == "AC"]
        incorrect = [c for c, v in zip(codes, verdicts) if v != "AC"]
        ai = d / "ai" / model
        ai.mkdir(parents=True, exist_ok=True)
        self._write(ai / "correct.jsonl", correct)
        self._write(ai / "incorrect.jsonl", incorrect)
        return {"model": model, "problem_id": pid, "attempts": self.k_max,
                "ac": len(correct), "non_ac": len(incorrect)}

    async def _gen(self, model, user, nonce):
        async with self.api:
            return await self.gpt.complete(model, self.system, user, self.temp, nonce)

    async def _judge(self, d, code):
        loop = asyncio.get_event_loop()
        res = await loop.run_in_executor(self.pool, self.validator.judge, str(d), code)
        return res["verdict"]

    def _prompt(self, d):
        # PaR-style: the CodeContests description already contains the input/output format and
        # the examples, so it serves as the full problem context (no separate test section).
        desc = (d / "description.txt").read_text(encoding="utf-8").strip()
        return self.user_tmpl.replace("{description}", desc)

    def _extract(self, text):
        m = re.search(r"```(?:[a-zA-Z+]*)\n(.*?)```", text, re.DOTALL)
        if m:
            return m.group(1).strip() or None
        if "#include" in text or "int main" in text:
            return text.strip()
        return None

    def _write(self, path, sources):
        with path.open("w", encoding="utf-8") as f:
            for s in sources:
                f.write(json.dumps({"source": s}, ensure_ascii=False) + "\n")
