import json
from pathlib import Path


class DatasetFinalizer:
    # Phase D end (Section 2.9 rule 5/6): combine the human and AI non-AC corpora, keep the
    # both-arm intersection (problems with human AND AI C++ non-AC >= 1) as the primary
    # RQ1/RQ2 set, report intersection count + per-arm totals + one-arm-only counts.
    def __init__(self, config):
        self.config = config
        self.art = Path(config["paths"]["artifacts"])
        self.problems = Path(config["paths"]["data"]) / "problems"
        self.cap = config["human_arm"]["cap_per_problem"]
        self.lang = config["languages"]["primary"]
        self.out = self.art / "dataset"

    def run(self):
        human = self._human_by_problem()
        ai = self._ai_by_problem()
        h_pids = {p for p, r in human.items() if r}
        a_pids = {p for p, r in ai.items() if r}
        inter = sorted(h_pids & a_pids)
        self.out.mkdir(parents=True, exist_ok=True)
        h_total = a_total = 0
        with (self.out / "final.jsonl").open("w", encoding="utf-8") as f:
            for pid in inter:
                for rec in human[pid]:
                    f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                    h_total += 1
                for rec in ai[pid]:
                    f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                    a_total += 1
        summary = {"intersection_problems": len(inter),
                   "human_only_problems": len(h_pids - a_pids),
                   "ai_only_problems": len(a_pids - h_pids),
                   "human_submissions": h_total, "ai_submissions": a_total,
                   "intersection_pids": inter}
        (self.out / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
        return summary

    def _human_by_problem(self):
        out = {}
        f = self.art / "human" / "corpus.jsonl"
        for line in f.read_text(encoding="utf-8").split("\n"):
            if line:
                rec = json.loads(line)
                out.setdefault(rec["problem_id"], []).append(rec)
        return out

    def _ai_by_problem(self):
        out = {}
        for f in sorted((self.art / "ai_submissions" / "zero_shot").glob("*.json")):
            pid = f.stem
            samples = json.loads(f.read_text(encoding="utf-8"))
            non_ac = [s for s in samples if s["verdict"] not in ("AC", "NO_CODE")][:self.cap]
            out[pid] = [self._ai_record(pid, s) for s in non_ac]
        return out

    def _ai_record(self, pid, s):
        meta = json.loads((self.problems / pid / "meta.json").read_text(encoding="utf-8"))
        return {"submission_id": f"ai:{pid}:{s['attempt']}", "problem_id": pid,
                "arm": "ai_zero_shot", "language": self.lang, "source": s["code"],
                "verdict": s["verdict"], "peak_time_ms": s.get("peak_time_ms", 0),
                "peak_mem_kb": 0, "difficulty_bin": meta["difficulty_bin"],
                "algo_families": meta["algo_families"]}
