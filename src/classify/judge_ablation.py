import json
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from src.classify.judge_selector import JudgeSelector
from src.classify.taxonomy_judge import TaxonomyJudge

UNCOVERED = "UNCOVERED"


def _prf(pairs):
    tp = fp = fn = exact = 0
    for P, G in pairs:
        tp += len(P & G)
        fp += len(P - G)
        fn += len(G - P)
        exact += int(P == G)
    prec = tp / (tp + fp) if tp + fp else 0.0
    rec = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
    n = len(pairs)
    avg_pred = sum(len(P) for P, _ in pairs) / n
    return {"precision": round(prec, 3), "recall": round(rec, 3), "f1": round(f1, 3),
            "exact": round(exact / n, 3), "avg_pred_leaves": round(avg_pred, 2)}


class JudgeAblation:
    # Validate prompt/effort changes on the gold set before committing to Phase E. Compares the
    # baseline (old multi-label prompt, from saved selection predictions) against the revised
    # primary/secondary prompt at low and medium reasoning effort, for both slate models, with a
    # primary-leaf metric (main), a primary+secondary set metric (secondary), and a confusion
    # table for systematic bias.
    def __init__(self, config):
        self.config = config
        self.judge = TaxonomyJudge(config)
        self.sel = JudgeSelector(config)
        self.slate = config["judge"]["slate"]
        self.art = Path(config["paths"]["artifacts"])
        self.results = Path(config["paths"]["results"])

    def run(self, efforts=("low", "medium"), limit=None, workers=8):
        items = self.sel._gold_items()
        if limit:
            items = items[:limit]
        rows, confusions = [], {}
        for model in self.slate:
            base = self._baseline(model)
            if base:
                rows.append({"condition": "baseline", "view": "set", "model": model, **_prf(base)})
        out_dir = self.art / "judge_ablation"
        out_dir.mkdir(parents=True, exist_ok=True)
        for effort in efforts:
            for model in self.slate:
                preds = self._classify_all(items, model, effort, workers)
                (out_dir / f"{self._slug(model)}_{effort}.jsonl").write_text(
                    "\n".join(json.dumps(p, ensure_ascii=False) for p in preds) + "\n", encoding="utf-8")
                prim = [({p["primary"]} if p["primary"] else set(), set(p["gold"])) for p in preds]
                full = [(set(p["leaves"]), set(p["gold"])) for p in preds]
                rows.append({"condition": f"revised+{effort}", "view": "primary", "model": model, **_prf(prim)})
                rows.append({"condition": f"revised+{effort}", "view": "set", "model": model, **_prf(full)})
                confusions[f"{model}|{effort}"] = self._confusion(preds)
        self._write(rows)
        return {"rows": rows, "confusions": confusions, "items": len(items)}

    def _classify_all(self, items, model, effort, workers):
        def one(it):
            r = self.judge.classify(it["submission"], model, effort=effort)
            return {"submission_id": it["submission"]["submission_id"], "primary": r["primary"],
                    "secondary": r["secondary"], "leaves": r["leaves"],
                    "uncovered": r["uncovered"], "gold": sorted(it["gold"])}
        with ThreadPoolExecutor(max_workers=workers) as ex:
            return list(ex.map(one, items))

    def _baseline(self, model):
        f = self.art / "judge_selection" / f"{self._slug(model)}.jsonl"
        if not f.exists():
            return None
        pairs = []
        for l in f.read_text(encoding="utf-8").split("\n"):
            if l:
                d = json.loads(l)
                pairs.append((set(d["predicted"]), set(d["gold"])))
        return pairs

    def _confusion(self, preds):
        # systematic bias: for single-gold items the judge got wrong, gold leaf -> judge primary
        conf = Counter()
        for p in preds:
            G = set(p["gold"])
            if len(G) == 1 and p["primary"] and p["primary"] not in G:
                conf[(next(iter(G)), p["primary"])] += 1
        return [{"gold": a, "judge_primary": b, "n": n} for (a, b), n in conf.most_common(10)]

    def _write(self, rows):
        import csv
        d = self.results / "tables"
        d.mkdir(parents=True, exist_ok=True)
        cols = ["condition", "view", "model", "precision", "recall", "f1", "exact", "avg_pred_leaves"]
        with (d / "judge_ablation.csv").open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=cols)
            w.writeheader()
            for r in rows:
                w.writerow({c: r.get(c) for c in cols})

    def _slug(self, model):
        return model.replace("/", "-").replace(".", "-")
