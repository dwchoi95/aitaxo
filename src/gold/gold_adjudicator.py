import csv
from pathlib import Path

from src.taxonomy.taxonomy import TAXONOMY

UNCOVERED = "UNCOVERED"


class GoldAdjudicator:
    # After "annotation complete": validate both annotator CSVs, compute inter-annotator
    # agreement (per-leaf Cohen's kappa, macro-averaged, since labels are multi-label), and
    # emit an adjudication CSV listing only the items where the two annotators disagree.
    def __init__(self, config):
        self.out = Path(config["paths"]["human"])

    def run(self):
        a1 = self._load("annotation_annotator1.csv")
        a2 = self._load("annotation_annotator2.csv")
        invalid = self._validate(a1, a2)
        items = sorted(set(a1) & set(a2))
        kappa = self._macro_kappa(a1, a2, items)
        exact = sum(1 for i in items if a1[i] == a2[i]) / len(items)
        jacc = sum(self._jaccard(a1[i], a2[i]) for i in items) / len(items)
        disputed = [i for i in items if a1[i] != a2[i]]
        self._write_adjudication(disputed, a1, a2)
        return {"items": len(items), "invalid_codes": invalid,
                "macro_cohen_kappa": round(kappa, 4), "exact_set_agreement": round(exact, 4),
                "mean_jaccard": round(jacc, 4), "disputed": len(disputed),
                "adjudication_file": str(self.out / "annotation_adjudication.csv")}

    def _load(self, fname):
        out = {}
        for r in csv.DictReader((self.out / fname).open(encoding="utf-8")):
            leaves = {c.strip() for c in (r.get("labels") or "").split(";") if c.strip()}
            if (r.get("uncovered") or "").strip().lower() == "yes":
                leaves.add(UNCOVERED)
            out[r["item_id"]] = leaves
        return out

    def _validate(self, a1, a2):
        if set(a1) != set(a2):
            raise ValueError("annotator CSVs cover different item sets")
        bad = set()
        for labels in list(a1.values()) + list(a2.values()):
            bad |= {c for c in labels if c != UNCOVERED and c not in TAXONOMY}
        return sorted(bad)

    def _macro_kappa(self, a1, a2, items):
        leaves = {c for i in items for c in (a1[i] | a2[i])}
        ks = [self._leaf_kappa(a1, a2, items, leaf) for leaf in leaves]
        ks = [k for k in ks if k is not None]
        return sum(ks) / len(ks) if ks else 1.0

    def _leaf_kappa(self, a1, a2, items, leaf):
        n = len(items)
        both = sum(1 for i in items if leaf in a1[i] and leaf in a2[i])
        only1 = sum(1 for i in items if leaf in a1[i] and leaf not in a2[i])
        only2 = sum(1 for i in items if leaf not in a1[i] and leaf in a2[i])
        neither = n - both - only1 - only2
        po = (both + neither) / n
        p1 = (both + only1) / n
        p2 = (both + only2) / n
        pe = p1 * p2 + (1 - p1) * (1 - p2)
        if pe >= 1.0:
            return None
        return (po - pe) / (1 - pe)

    def _jaccard(self, s1, s2):
        if not s1 and not s2:
            return 1.0
        return len(s1 & s2) / len(s1 | s2)

    def _write_adjudication(self, disputed, a1, a2):
        with (self.out / "annotation_adjudication.csv").open("w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(["item_id", "detail_file", "annotator1_labels", "annotator2_labels", "final_labels"])
            for i in disputed:
                w.writerow([i, f"items/{i}.md", ";".join(sorted(a1[i])), ";".join(sorted(a2[i])), ""])
