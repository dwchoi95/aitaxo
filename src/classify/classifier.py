import json
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from src.classify.taxonomy_judge import TaxonomyJudge


class Classifier:
    # Phase E orchestrator: run the TaxonomyJudge over a dataset with a given judge model.
    # dry_run assembles prompts only (no API) to validate Tier-1 candidate sizing and prompt
    # lengths before any spend; the real run writes one classification record per submission.
    def __init__(self, config):
        self.config = config
        self.judge = TaxonomyJudge(config)
        self.art = Path(config["paths"]["artifacts"])
        self.chosen = config["judge"]["chosen"]
        self.slate = config["judge"]["slate"]

    def run(self, dataset="final", model=None, limit=None, dry_run=False, workers=6):
        subs = self._load(dataset)
        if limit:
            subs = subs[:limit]
        model = model or self.chosen or self.slate[0]
        if dry_run:
            results = [self.judge.classify(s, model, True) for s in subs]
            return self._dry_summary(subs, results, model)
        # resilient: collect as each completes; on a hard error (e.g. quota) stop cleanly and
        # still write everything finished so far. Cached calls make a later resume free.
        results, stopped = [], None
        with ThreadPoolExecutor(max_workers=workers) as ex:
            futs = [ex.submit(self.judge.classify, s, model, False) for s in subs]
            try:
                for fut in as_completed(futs):
                    results.append(fut.result())
            except Exception as e:
                stopped = str(e)[:200]
                for fu in futs:
                    fu.cancel()
        tag = Path(dataset).stem if str(dataset).endswith(".jsonl") else dataset
        out = self.art / "classifications" / f"{self._slug(model)}_{tag}.jsonl"
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open("w", encoding="utf-8") as f:
            for r in results:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        summ = self._summary(results, model, str(out))
        summ.update({"completed": len(results), "total": len(subs), "stopped_early": stopped})
        return summ

    def _load(self, dataset):
        if str(dataset).endswith(".jsonl"):
            return [json.loads(l) for l in Path(dataset).read_text(encoding="utf-8").split("\n") if l]
        if dataset == "gold":
            man = json.loads((Path(self.config["paths"]["human"]) / "gold_manifest.json")
                             .read_text(encoding="utf-8"))
            by_id = {s["submission_id"]: s for s in self._load("final")}
            return [by_id[m["submission_id"]] for m in man if m["submission_id"] in by_id]
        f = self.art / "dataset" / "final.jsonl"
        return [json.loads(l) for l in f.read_text(encoding="utf-8").split("\n") if l]

    def _dry_summary(self, subs, results, model):
        chars = [r["prompt_chars"] for r in results]
        tier1 = Counter()
        for s in subs:
            tier1[s["verdict"]] = len(TaxonomyJudge.tier1_candidates(s["verdict"]))
        return {"model": model, "submissions": len(subs), "dry_run": True,
                "prompt_chars_min": min(chars), "prompt_chars_max": max(chars),
                "prompt_chars_mean": round(sum(chars) / len(chars)),
                "tier1_candidate_count_by_verdict": dict(tier1),
                "verdict_distribution": dict(Counter(s["verdict"] for s in subs))}

    def _summary(self, results, model, path):
        leaf = Counter(l for r in results for l in r["leaves"])
        return {"model": model, "submissions": len(results), "output": path,
                "uncovered": sum(1 for r in results if r["uncovered"]),
                "needs_review": sum(1 for r in results if r["needs_review"]),
                "top_leaves": dict(leaf.most_common(10))}

    def _slug(self, model):
        return model.replace("/", "-").replace(".", "-")
