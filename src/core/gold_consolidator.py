import csv
import json
from pathlib import Path

from src.core.classifier import COLS
from src.taxonomy.taxonomy import TAXONOMY


class GoldConsolidator:
    # Turn the consolidated human annotation (annotator1/2 merged, disagreements adjudicated by a
    # third) into data/classifications/gold.csv with the SAME schema as full.csv, so the two join on
    # item_id for judge<->gold agreement. Only item_id, labels, rationale are read from the annotation
    # file; the remaining fields (problem_id, cf_rating, family, model, stage, idx, verdict) are
    # mapped in from gold_key.jsonl + the problem meta.
    def __init__(self, config):
        self.problems = Path(config["paths"]["problems"])
        self.analysis = Path(config["paths"]["analysis"])
        self.key_path = self.analysis / "gold_key.jsonl"
        self.default_input = Path(config["paths"]["gold"]) / "label.csv"
        self.out = Path(config["paths"]["classifications"]) / "gold.csv"

    def run(self, input_path=None):
        inp = Path(input_path) if input_path else self.default_input
        key = {}
        for line in self.key_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                k = json.loads(line)
                key[k["item_id"]] = k
        meta_cache = {}

        def meta(pid):
            if pid not in meta_cache:
                m = json.loads((self.problems / pid / "meta.json").read_text(encoding="utf-8"))
                meta_cache[pid] = (m.get("cf_rating") or "", ",".join(m.get("cf_tags") or []))
            return meta_cache[pid]

        rows, missing, unlabeled, invalid = [], [], 0, 0
        for r in csv.DictReader(inp.open(encoding="utf-8")):
            iid = (r.get("item_id") or "").strip()
            if iid not in key:
                missing.append(iid)
                continue
            k = key[iid]
            rating, tags = meta(k["problem_id"])
            labels = self._labels(r.get("labels"))
            if any(x not in TAXONOMY and x != "UNCOVERED" for x in labels):
                invalid += 1
            if not labels:
                unlabeled += 1
            rows.append({"item_id": iid, "problem_id": k["problem_id"], "cf_rating": rating,
                         "tags": tags, "model": k["model"], "stage": k["stage"], "idx": k["idx"],
                         "verdict": k["verdict"], "labels": ",".join(labels),
                         "rationale": r.get("rationale", "")})
        self.out.parent.mkdir(parents=True, exist_ok=True)
        with self.out.open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=COLS)
            w.writeheader()
            w.writerows(rows)
        return {"input": str(inp), "output": str(self.out), "gold_rows": len(rows),
                "labeled": len(rows) - unlabeled, "unlabeled": unlabeled,
                "rows_with_invalid_leaf": invalid, "item_ids_not_in_key": len(missing)}

    def _labels(self, s):
        # accept either a JSON array (e.g. ["GE1.2","GE2.2"]) or a comma-separated string
        s = (s or "").strip()
        try:
            v = json.loads(s)
            ls = [v] if isinstance(v, str) else list(v)
        except (ValueError, TypeError):
            ls = [x.strip().strip('[]"\' ') for x in s.split(",")]
        return [str(x).strip() for x in ls if str(x).strip()]
