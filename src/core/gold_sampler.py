import csv
import hashlib
import json
import random
from collections import Counter, defaultdict
from pathlib import Path

from src.execute.validator import Validator
from src.taxonomy.taxonomy import TAXONOMY, FAMILIES, FAMILY_DEFINITIONS, ALGORITHM_SPECIFIC_NOTE

LABEL_COLS = ["problem_id", "item_id", "verdict", "labels", "rationale"]


class GoldSampler:
    # Draw the human-annotation gold set (arm-balanced, verdict-stratified with rare verdicts floored,
    # capped per problem, fixed seed) and lay it out for easy hands-on labeling. Output goes to gold/:
    # one readable Markdown per problem (gold/<pid>.md = the statement once, then each sampled buggy
    # program as a syntax-highlighted code block with its item id and verdict), a single flat answer
    # sheet (gold/label.csv) ordered to match, and the codebook. Zip gold/ and hand the same package
    # to each annotator; they fill label.csv. The provenance-unblinding key is written OUTSIDE gold/
    # (analysis/gold_key.jsonl) so it is never in the annotator zip.
    def __init__(self, config):
        g = config["gold"]
        self.arms = g["arms"]
        self.per_arm = g["per_arm"]
        self.floors = g["verdict_floors"]
        self.cap = g["per_problem_cap"]
        self.seed = g["seed"]
        self.data = Path(config["paths"]["problems"])
        self.gold = Path(config["paths"]["gold"])
        self.analysis = Path(config["paths"]["analysis"])
        self.validator = Validator(config)

    def run(self):
        random.seed(self.seed)
        pool, ctx = self._pool()
        key, by_problem = [], defaultdict(list)
        for arm in self.arms:
            for verdict, pid, idx, source, _ in self._allocate(arm, pool[arm]):
                item_id = hashlib.sha1(f"{arm}:{pid}:{idx}".encode("utf-8")).hexdigest()[:10]
                by_problem[pid].append((item_id, verdict, source))
                key.append({"item_id": item_id, "arm": arm, "model": arm, "stage": "zero_shot",
                            "problem_id": pid, "idx": idx, "verdict": verdict})
        for pid in by_problem:
            random.shuffle(by_problem[pid])   # within-problem order (provenance not inferable from order)

        self.gold.mkdir(parents=True, exist_ok=True)
        for pid in sorted(by_problem):
            (self.gold / f"{pid}.md").write_text(self._md(pid, ctx[pid], by_problem[pid]), encoding="utf-8")
        with (self.gold / "label.csv").open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=LABEL_COLS)
            w.writeheader()
            for pid in sorted(by_problem):
                for item_id, verdict, _ in by_problem[pid]:
                    w.writerow({"problem_id": pid, "item_id": item_id, "verdict": verdict,
                                "labels": "", "rationale": ""})
        (self.gold / "codebook.md").write_text(self._codebook(), encoding="utf-8")
        self.analysis.mkdir(parents=True, exist_ok=True)
        with (self.analysis / "gold_key.jsonl").open("w", encoding="utf-8") as f:
            for k in key:
                f.write(json.dumps(k, ensure_ascii=False) + "\n")

        return {"gold": sum(len(v) for v in by_problem.values()),
                "per_arm": {a: sum(1 for k in key if k["arm"] == a) for a in self.arms},
                "by_verdict": dict(Counter(k["verdict"] for k in key)), "problems": len(by_problem),
                "gold_dir": str(self.gold), "key": str(self.analysis / "gold_key.jsonl")}

    def _md(self, pid, c, bugs):
        out = [f"# {pid}  (rating {c['rating']} · tags: {c['tags']})", "", c["description"].rstrip(), ""]
        for item_id, verdict, source in bugs:
            out += ["", "---", "", f"## item `{item_id}` · verdict: {verdict}", "",
                    "```cpp", source.rstrip(), "```", "",
                    "_label this item in `label.csv` (one or more leaf codes; see `codebook.md`)._"]
        return "\n".join(out) + "\n"

    def _pool(self):
        # arm -> verdict -> [(pid, idx, source, fft)]; plus per-problem description + rating + tags
        pool = defaultdict(lambda: defaultdict(list))
        ctx = {}
        for d in sorted(self.data.glob("*/")):
            if not (d / "meta.json").exists():
                continue
            meta = json.loads((d / "meta.json").read_text(encoding="utf-8"))
            ctx[d.name] = {"description": (d / "description.txt").read_text(encoding="utf-8"),
                           "rating": meta.get("cf_rating") or "?",
                           "tags": ", ".join(meta.get("cf_tags") or []) or "—"}
            for arm, rel in self.arms.items():
                f = d / rel
                if not f.exists():
                    continue
                for idx, line in enumerate(l for l in f.read_text(encoding="utf-8").split("\n") if l):
                    src = json.loads(line)["source"]
                    res = self.validator.judge(str(d), src)
                    pool[arm][res["verdict"]].append((d.name, idx, src, res.get("first_failing_test")))
        return pool, ctx

    def _allocate(self, arm, by_verdict):
        # rare verdicts to their floor (or all available), WA fills the rest; cap per problem throughout
        picked, used = [], 0
        for v in ["CE", "RE", "TLE"]:
            target = min(self.floors.get(v, 0), len(by_verdict.get(v, [])))
            chosen = self._take(by_verdict.get(v, []), target)
            picked += [(v, *c) for c in chosen]
            used += len(chosen)
        chosen = self._take(by_verdict.get("WA", []), self.per_arm - used)
        picked += [("WA", *c) for c in chosen]
        return picked

    def _take(self, candidates, n):
        cands = candidates[:]
        random.shuffle(cands)
        perp, out = Counter(), []
        for pid, idx, src, fft in cands:
            if len(out) >= n:
                break
            if perp[pid] < self.cap:
                out.append((pid, idx, src, fft))
                perp[pid] += 1
        return out

    def _codebook(self):
        lines = [f"# Bug taxonomy codebook (Wei et al., {len(TAXONOMY)} leaves)", "",
                 "For each item, read the problem and the buggy program in its `<problem_id>.md`, then",
                 "fill the `labels` column of `label.csv` for that item id.", "",
                 "`labels` is MULTI-LABEL: a comma-separated list of one or more leaf codes (e.g.",
                 "`GE2.2,GE6.2`) — include EVERY leaf whose mechanism is clearly present in the program",
                 "(a program may contain several independent errors). Prefer the most-specific leaf; use",
                 "`UNCOVERED` only if no leaf fits. The `verdict` column is the judge result (a weak hint).",
                 "", "Leaf definitions below are quoted verbatim from Wei et al. (2026), Section 4.2."]
        for title, prefix, note in [("General Errors", "GE", None),
                                    ("Algorithm-specific Errors", "AE", ALGORITHM_SPECIFIC_NOTE)]:
            lines += ["", f"## {title}"]
            if note:
                lines += ["", note]
            for fam in [c for c in FAMILIES if c.startswith(prefix)]:
                lines += ["", f"### {fam} {FAMILIES[fam]}", "", FAMILY_DEFINITIONS[fam], ""]
                for code, (name, defn, _) in TAXONOMY.items():
                    if code.startswith(fam + "."):
                        lines.append(f"- **{code} {name}** — {defn}")
        return "\n".join(lines) + "\n"
