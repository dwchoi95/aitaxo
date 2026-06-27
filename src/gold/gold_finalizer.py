import csv
import json
from collections import Counter
from pathlib import Path

UNCOVERED = "UNCOVERED"


class GoldFinalizer:
    # Combine the two annotator CSVs and the adjudicated disputes into one gold-label file:
    # agreed items take the shared label set, disputed items take the adjudicator's final set.
    def __init__(self, config):
        self.out = Path(config["paths"]["human"])

    def run(self):
        manifest = {m["item_id"]: m for m in
                    json.loads((self.out / "gold_manifest.json").read_text(encoding="utf-8"))}
        a1 = self._load_ann("annotation_annotator1.csv")
        a2 = self._load_ann("annotation_annotator2.csv")
        adj = self._load_adj()
        records, n_agreed, n_adj = [], 0, 0
        for item_id, m in manifest.items():
            if a1[item_id] == a2[item_id]:
                gold, source = a1[item_id], "agreed"
                n_agreed += 1
            else:
                gold, source = adj[item_id], "adjudicated"
                n_adj += 1
            records.append({"item_id": item_id, "submission_id": m["submission_id"],
                            "problem_id": m["problem_id"], "arm": m["arm"], "verdict": m["verdict"],
                            "gold_leaves": sorted(gold), "source": source})
        with (self.out / "gold_labels.jsonl").open("w", encoding="utf-8") as f:
            for r in records:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        leaf = Counter(l for r in records for l in r["gold_leaves"])
        return {"items": len(records), "agreed": n_agreed, "adjudicated": n_adj,
                "uncovered_items": sum(1 for r in records if r["gold_leaves"] == [UNCOVERED]),
                "distinct_leaves": len([l for l in leaf if l != UNCOVERED]),
                "top_leaves": dict(leaf.most_common(8))}

    def _load_ann(self, fname):
        out = {}
        for r in csv.DictReader((self.out / fname).open(encoding="utf-8")):
            leaves = {c.strip() for c in (r.get("labels") or "").split(";") if c.strip()}
            if (r.get("uncovered") or "").strip().lower() == "yes":
                leaves.add(UNCOVERED)
            out[r["item_id"]] = leaves
        return out

    def _load_adj(self):
        out = {}
        for r in csv.DictReader((self.out / "annotation_adjudication.csv").open(encoding="utf-8")):
            out[r["item_id"]] = {c.strip() for c in (r.get("final_labels") or "").split(";") if c.strip()}
        return out
