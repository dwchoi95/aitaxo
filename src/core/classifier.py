import asyncio
import csv
import hashlib
import json
import re
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from src.execute.validator import Validator
from src.models.gpt import Gpt
from src.taxonomy.taxonomy import TAXONOMY

COLS = ["item_id", "problem_id", "cf_rating", "tags", "model", "stage", "idx",
        "verdict", "labels", "rationale"]


class Classifier:
    # Taxonomy classification by the AI labeler (gpt-5.4). Every non-AC submission (human-written and
    # AI-written) is labeled with one or more Wei leaves (multi-label) given the SAME evidence as the
    # human annotators (problem statement + buggy code + verdict), self-consistency over m samples
    # aggregated by majority. All rows go to data/classifications/full.csv (the bug's author is in the
    # `model` column); the parallel human-annotation gold lives in gold.csv. The run is RESUMABLE:
    # each item's row is appended as soon as it finishes, and a re-run skips item_ids already present,
    # so an interrupted/dropped run continues where it stopped (LLM samples are also cached).
    def __init__(self, config):
        j = config["judge"]
        self.model = j["model"]
        self.m = j["m"]
        self.temp = j["temperature"]
        self.cap = j["size_cap_chars"]
        self.concurrency = j["concurrency"]
        self.workers = j["workers"]
        self.data = Path(config["paths"]["problems"])
        self.out = Path(config["paths"]["classifications"])
        self.gpt = Gpt(config)
        self.validator = Validator(config)
        prompts = Path(__file__).resolve().parent.parent / "prompts" / "judge"
        self.system = (prompts / "system.md").read_text(encoding="utf-8").replace("{rubric}", self._rubric())
        self.user_tmpl = (prompts / "user.md").read_text(encoding="utf-8")

    def run(self, limit=None):
        return asyncio.run(self._run(limit))

    async def _run(self, limit):
        items = self._items()
        if limit:
            items = items[:limit]
        self.out.mkdir(parents=True, exist_ok=True)
        self.out_path = self.out / "full.csv"   # the AI labeler (gpt-5.4); gold.csv holds the human gold
        if not self.out_path.exists():
            with self.out_path.open("w", encoding="utf-8", newline="") as f:
                csv.writer(f).writerow(COLS)
        done = self._done()
        todo = [it for it in items if it["item_id"] not in done]
        self.api = asyncio.Semaphore(self.concurrency)
        self.pool = ThreadPoolExecutor(max_workers=self.workers)
        self.writelock = asyncio.Lock()
        recs = await asyncio.gather(*[self._process(it) for it in todo])
        self.pool.shutdown()
        return {"total": len(items), "already_done": len(items) - len(todo),
                "newly_classified": len(recs),
                "uncovered": sum(1 for r in recs if r["uncovered"]),
                "output": str(self.out_path)}

    def _items(self):
        # every non-AC submission. item_id matches analysis/label (sha1 of model:pid:idx, or
        # model:reflect:pid:idx) so classifications join to the gold/code files. Human bugs:
        # <pid>/human/incorrect.jsonl; AI zero-shot: <pid>/ai/<model>/incorrect.jsonl; AI post-
        # self-refine remaining: <pid>/ai/<model>/reflect.jsonl (fixed == False).
        items = []
        for d in sorted(self.data.glob("*/")):
            if not (d / "meta.json").exists():
                continue
            pid = d.name
            meta = json.loads((d / "meta.json").read_text(encoding="utf-8"))
            rating = meta.get("cf_rating") or ""
            tags = ",".join(meta.get("cf_tags") or [])   # original Codeforces tags, verbatim

            def add(model, arm, stage, idx, source):
                key = f"{model}:{pid}:{idx}" if stage == "zero_shot" else f"{model}:reflect:{pid}:{idx}"
                items.append({"item_id": hashlib.sha1(key.encode("utf-8")).hexdigest()[:10],
                              "problem_id": pid, "arm": arm, "model": model, "stage": stage,
                              "idx": idx, "source": source, "cf_rating": rating, "tags": tags})

            hf = d / "human" / "incorrect.jsonl"
            if hf.exists():
                for idx, line in enumerate(l for l in hf.read_text(encoding="utf-8").split("\n") if l):
                    add("human", "human", "zero_shot", idx, json.loads(line)["source"])
            for sub in sorted((d / "ai").glob("*/")):
                if not sub.is_dir():
                    continue
                zf = sub / "incorrect.jsonl"
                if zf.exists():
                    for idx, line in enumerate(l for l in zf.read_text(encoding="utf-8").split("\n") if l):
                        add(sub.name, "ai", "zero_shot", idx, json.loads(line)["source"])
                rf = sub / "reflect.jsonl"
                if rf.exists():
                    for line in (l for l in rf.read_text(encoding="utf-8").split("\n") if l):
                        rec = json.loads(line)
                        if not rec["fixed"]:
                            add(sub.name, "ai", "reflect", rec["idx"], rec["final_source"])
        return items

    async def _process(self, it):
        rec = await self._classify(it)
        row = [it["item_id"], it["problem_id"], it["cf_rating"], it["tags"], it["model"],
               it["stage"], it["idx"], rec["verdict"],
               ",".join(rec["labels"]) if rec["labels"] else "UNCOVERED", rec["rationale"]]
        async with self.writelock:
            with self.out_path.open("a", encoding="utf-8", newline="") as f:
                csv.writer(f).writerow(row)
        return rec

    async def _classify(self, it):
        d = self.data / it["problem_id"]
        loop = asyncio.get_event_loop()
        res = await loop.run_in_executor(self.pool, self.validator.judge, str(d), it["source"])
        user = self._user(d, it, res)
        samples = await asyncio.gather(*[self._one(user, i) for i in range(self.m)])
        agg = self._aggregate([self._parse(s) for s in samples])
        return {"verdict": res["verdict"], **agg}

    async def _one(self, user, nonce):
        async with self.api:
            return await self.gpt.complete(self.model, self.system, user, self.temp, nonce)

    def _done(self):
        done = set()
        if self.out_path.exists():
            with self.out_path.open(encoding="utf-8") as f:
                r = csv.reader(f)
                next(r, None)
                for row in r:
                    if row:
                        done.add(row[0])
        return done

    def _user(self, d, it, res):
        # same evidence the human annotators get: problem statement + buggy code + verdict
        desc = (d / "description.txt").read_text(encoding="utf-8")
        repl = {"{description}": self._clip(desc),
                "{submission}": self._clip(it["source"]), "{verdict}": res["verdict"]}
        out = self.user_tmpl
        for k, v in repl.items():
            out = out.replace(k, v)
        return out

    def _parse(self, text):
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if not m:
            return {"labels": [], "rationale": ""}
        try:
            obj = json.loads(m.group(0))
        except json.JSONDecodeError:
            return {"labels": [], "rationale": ""}
        labels = [l for l in obj.get("labels", []) if l in TAXONOMY]
        return {"labels": labels, "rationale": obj.get("rationale", "")}

    def _aggregate(self, samples):
        # multi-label self-consistency: keep every leaf voted by a majority of the m samples; if none
        # reaches a majority, fall back to the single most-voted leaf.
        thresh = (self.m + 1) // 2
        cnt = Counter(l for s in samples for l in s["labels"])
        labels = sorted(c for c, n in cnt.items() if n >= thresh)
        if not labels and cnt:
            labels = [cnt.most_common(1)[0][0]]
        return {"labels": labels, "uncovered": not labels,
                "rationale": next((s["rationale"] for s in samples if s["labels"]), "")}

    def _rubric(self):
        return "\n".join(f"{c} {v[0]}: {v[1]}" for c, v in TAXONOMY.items())

    def _clip(self, s, cap=None):
        cap = cap or self.cap
        return s if len(s) <= cap else s[: cap // 2] + "\n...[clipped]...\n" + s[-cap // 2:]
