import json
import math
import random
from collections import defaultdict
from pathlib import Path

from src.judge.submission_judge import SubmissionJudge
from src.taxonomy.taxonomy import FAMILIES, TAXONOMY, VERDICT_CANDIDATES

Z = {0.90: 1.645, 0.95: 1.96, 0.99: 2.576}


class GoldSampler:
    # Phase F prepare-gold: size the gold set by the Cochran proportion formula (+ finite-
    # population correction), stratify by arm x verdict, draw a seeded sample, assign opaque
    # shuffled item ids, and emit a provenance-blind annotation packet (codebook, per-item
    # detail files, two annotator CSVs, README). Stops for the human labelers.
    def __init__(self, config):
        self.config = config
        self.art = Path(config["paths"]["artifacts"])
        self.problems = Path(config["paths"]["data"]) / "problems"
        self.lang = config["languages"]["primary"]
        self.size_cap = config["prompt"]["size_cap_chars"]
        self.conf = config["gold"]["confidence"]
        self.margin = config["gold"]["margin"]
        self.p = config["gold"]["p"]
        self.min_per_cell = config["gold"]["min_per_cell"]
        self.seed = config["gold"]["seed"]
        self.judge = SubmissionJudge(config)
        self.out = config["paths"]["human"] if "human" in config["paths"] else str(self.art / "human")
        self.out = Path(self.out)

    def run(self):
        subs = [json.loads(l) for l in (self.art / "dataset" / "final.jsonl")
                .read_text(encoding="utf-8").split("\n") if l]
        n_target, n0 = self._cochran(len(subs))
        strata = defaultdict(list)
        for s in subs:
            strata[(s["arm"], s["verdict"])].append(s)
        alloc = self._allocate(n_target, strata, len(subs))
        sample = self._draw(strata, alloc)
        rng = random.Random(f"{self.seed}:shuffle")
        rng.shuffle(sample)
        items = [{**s, "item_id": f"g{i + 1:04d}"} for i, s in enumerate(sample)]
        self._emit(items)
        return {"population": len(subs), "cochran_n0": n0, "target_after_fpc": n_target,
                "sampled": len(items), "allocation": {f"{a}:{v}": c for (a, v), c in sorted(alloc.items())}}

    def _cochran(self, N):
        z = Z[self.conf]
        n0 = (z * z * self.p * (1 - self.p)) / (self.margin * self.margin)
        n = n0 / (1 + (n0 - 1) / N)
        return math.ceil(n), round(n0, 1)

    def _allocate(self, n, strata, N):
        alloc = {}
        for cell, rows in strata.items():
            want = max(self.min_per_cell, round(n * len(rows) / N))
            alloc[cell] = min(want, len(rows))
        return alloc

    def _draw(self, strata, alloc):
        out = []
        for cell, k in alloc.items():
            rows = list(strata[cell])
            random.Random(f"{self.seed}:{cell[0]}:{cell[1]}").shuffle(rows)
            out.extend(rows[:k])
        return out

    def _emit(self, items):
        (self.out / "items").mkdir(parents=True, exist_ok=True)
        manifest = []
        for it in items:
            detail = f"items/{it['item_id']}.md"
            (self.out / detail).write_text(self._item_md(it), encoding="utf-8")
            manifest.append({"item_id": it["item_id"], "submission_id": it["submission_id"],
                             "problem_id": it["problem_id"], "arm": it["arm"], "verdict": it["verdict"],
                             "detail_file": detail})
        (self.out / "gold_manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        for ann in ("annotator1", "annotator2"):
            self._write_csv(self.out / f"annotation_{ann}.csv", manifest)
        (self.out / "CODEBOOK.md").write_text(self._codebook(), encoding="utf-8")
        (self.out / "README.md").write_text(self._readme(len(items)), encoding="utf-8")

    def _item_md(self, it):
        pid = it["problem_id"]
        v = self.judge.judge(self.problems / pid, it["source"], self.lang)
        ff = v["first_failing_test"] or {}
        oracle = json.loads([l for l in (self.problems / pid / self.lang / "correct.jsonl")
                             .read_text(encoding="utf-8").split("\n") if l][0])["code"]
        desc = self._clip((self.problems / pid / "description.txt").read_text(encoding="utf-8"))
        msg = v.get("compiler_stderr") or v.get("runtime_error") or "(none)"
        parts = [f"# Item {it['item_id']}", "",
                 "## Problem", "", desc, "",
                 f"## Submission (verdict: {it['verdict']})", "", "```cpp", it["source"], "```", "",
                 "## First failing test", "",
                 f"- Input: `{self._clip(ff.get('input', '(n/a)'), 800)}`",
                 f"- Expected: `{self._clip(ff.get('expected', '(n/a)'), 800)}`",
                 f"- Actual: `{self._clip(ff.get('actual', '(n/a)'), 800)}`", "",
                 "## Compiler / runtime message", "", "```", self._clip(msg, 1500), "```", "",
                 "## Reference correct solution (for your judgment only)", "",
                 "```cpp", self._clip(oracle), "```", ""]
        return "\n".join(parts)

    def _write_csv(self, path, manifest):
        lines = ["item_id,detail_file,labels,uncovered,notes"]
        for m in manifest:
            lines.append(f"{m['item_id']},{m['detail_file']},,no,")
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def _codebook(self):
        out = ["# Codebook — Wei et al. competitive-programming bug taxonomy", "",
               "Pinned from github.com/minnanWei/LLMs-Competitive-Program-Generation (Tables 1-2).",
               "Assign **one or more** leaf codes per item. Codes marked **[lang]** are",
               "language-dependent (relevant to C++ here). If no leaf fits, set `uncovered=yes`",
               "and describe the pattern in `notes`.", ""]
        fam_order = list(FAMILIES)
        for fam in fam_order:
            out.append(f"## {fam} — {FAMILIES[fam]}")
            out.append("")
            for code, (name, defn, ex, langdep) in TAXONOMY.items():
                if code.split(".")[0] == fam:
                    tag = " **[lang]**" if langdep else ""
                    out.append(f"- **{code} {name}**{tag}: {defn} _Example:_ {ex}")
            out.append("")
        out.append("## Verdict → likely candidate leaves (guidance, not a restriction)")
        out.append("")
        for verd, cands in VERDICT_CANDIDATES.items():
            shown = ", ".join(cands) if len(cands) <= 8 else ", ".join(cands[:8]) + ", …"
            out.append(f"- **{verd}**: {shown}")
        out.append("")
        return "\n".join(out)

    def _readme(self, n):
        return "\n".join([
            "# Gold annotation packet", "",
            f"{n} items sampled (Cochran 95% / ±5%, stratified by arm × verdict). Each item is",
            "a competitive-programming submission with a confirmed bug. Provenance (human vs AI)",
            "is hidden on purpose — label only the bug.", "",
            "## What to do", "",
            "1. Read **CODEBOOK.md** (the taxonomy + examples).",
            "2. **Two annotators independently** fill one CSV each:",
            "   - Annotator 1 → `annotation_annotator1.csv`",
            "   - Annotator 2 → `annotation_annotator2.csv`",
            "3. For each row, open its `detail_file` (under `items/`), decide the bug, and enter",
            "   leaf codes in the **`labels`** column, **semicolon-separated** (e.g. `GE4.2;AE3.2`).",
            "   - If no leaf fits, set **`uncovered`** to `yes` and explain in `notes`.",
            "4. When both CSVs are complete, tell the agent **\"annotation complete\"** — it will",
            "   validate, compute inter-annotator κ, and emit a disputed-items file for the",
            "   adjudicator.", "",
            "Do not edit `item_id`, `detail_file`, or `gold_manifest.json`.", ""])

    def _clip(self, s, cap=None):
        cap = cap or self.size_cap
        s = s if s is not None else ""
        return s if len(s) <= cap else s[: cap // 2] + " …[clipped]… " + s[-cap // 2:]
