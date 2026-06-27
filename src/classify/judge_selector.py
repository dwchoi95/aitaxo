import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from src.classify.taxonomy_judge import TaxonomyJudge

UNCOVERED = "UNCOVERED"


class JudgeSelector:
    # Phase F (RQ4): run each judge in the slate over the human-labeled gold items (provenance-
    # blind) and select the judge whose taxonomy predictions agree best with the gold labels.
    def __init__(self, config):
        self.config = config
        self.judge = TaxonomyJudge(config)
        self.slate = config["judge"]["slate"]
        self.art = Path(config["paths"]["artifacts"])
        self.results = Path(config["paths"]["results"])
        self.human = Path(config["paths"]["human"])

    def run(self, limit=None, dry_run=False, workers=8):
        items = self._gold_items()
        if limit:
            items = items[:limit]
        rows = []
        preds_dir = self.art / "judge_selection"
        preds_dir.mkdir(parents=True, exist_ok=True)
        for model in self.slate:
            preds = self._classify_all(items, model, dry_run, workers)
            if dry_run:
                rows.append({"model": model, "items": len(items), "dry_run": True})
                continue
            (preds_dir / f"{self._slug(model)}.jsonl").write_text(
                "\n".join(json.dumps(p, ensure_ascii=False) for p in preds) + "\n", encoding="utf-8")
            rows.append({"model": model, **self._agreement(preds, items)})
        if dry_run:
            return {"slate": self.slate, "items": len(items), "rows": rows}
        chosen = max(rows, key=lambda r: (r["micro_f1"], r["mean_jaccard"]))
        self._write_table(rows)
        return {"items": len(items), "rows": rows, "chosen": chosen["model"],
                "chosen_micro_f1": chosen["micro_f1"]}

    def _gold_items(self):
        gold = [json.loads(l) for l in (self.human / "gold_labels.jsonl")
                .read_text(encoding="utf-8").split("\n") if l]
        subs = {}
        for l in (self.art / "dataset" / "final.jsonl").read_text(encoding="utf-8").split("\n"):
            if l:
                s = json.loads(l)
                subs[s["submission_id"]] = s
        out = []
        for g in gold:
            s = subs.get(g["submission_id"])
            if s:
                out.append({"submission": s, "gold": set(g["gold_leaves"])})
        return out

    def _classify_all(self, items, model, dry_run, workers):
        def one(it):
            r = self.judge.classify(it["submission"], model, dry_run)
            pred = set() if dry_run else set(r.get("leaves", [])) | ({UNCOVERED} if r.get("uncovered") else set())
            return {"submission_id": it["submission"]["submission_id"], "predicted": sorted(pred),
                    "gold": sorted(it["gold"])}
        with ThreadPoolExecutor(max_workers=workers) as ex:
            return list(ex.map(one, items))

    def _agreement(self, preds, items):
        tp = fp = fn = exact = 0
        jacc = 0.0
        for p in preds:
            pr, go = set(p["predicted"]), set(p["gold"])
            tp += len(pr & go)
            fp += len(pr - go)
            fn += len(go - pr)
            exact += int(pr == go)
            jacc += 1.0 if not pr and not go else len(pr & go) / len(pr | go)
        prec = tp / (tp + fp) if tp + fp else 0.0
        rec = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
        n = len(preds)
        return {"items": n, "precision": round(prec, 4), "recall": round(rec, 4),
                "micro_f1": round(f1, 4), "mean_jaccard": round(jacc / n, 4),
                "exact_set_agreement": round(exact / n, 4)}

    def _write_table(self, rows):
        import csv
        d = self.results / "tables"
        d.mkdir(parents=True, exist_ok=True)
        cols = ["model", "items", "precision", "recall", "micro_f1", "mean_jaccard", "exact_set_agreement"]
        with (d / "judge_selection.csv").open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=cols)
            w.writeheader()
            for r in rows:
                w.writerow({c: r.get(c) for c in cols})

    def _slug(self, model):
        return model.replace("/", "-").replace(".", "-")
