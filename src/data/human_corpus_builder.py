import json
import random
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from src.judge.submission_judge import SubmissionJudge


class HumanCorpusBuilder:
    # Phase C: judge the human C++ incorrect_solutions for each judgeable problem, keep only
    # genuinely non-AC ones (Section 2.9 rule 2), cap per problem (rule 6), enforce the >=1
    # non-AC floor (rule 4). Unexpected-AC submissions are dropped and counted.
    def __init__(self, config):
        self.config = config
        self.lang = config["languages"]["primary"]
        self.judge = SubmissionJudge(config)
        self.problems = Path(config["paths"]["data"]) / "problems"
        self.out = Path(config["paths"]["artifacts"]) / "human"
        self.cap = config["human_arm"]["cap_per_problem"]
        self.max_judge = config["human_arm"]["max_judge_per_problem"]
        self.seed = config["human_arm"]["sample_seed"]

    def run(self, limit=None):
        pids = self._judgeable()
        if limit:
            pids = pids[:limit]
        tasks = [(pid, rec) for pid in pids for rec in self._sample(pid)]
        verdicts = self._judge_all(tasks)
        self.out.mkdir(parents=True, exist_ok=True)
        corpus = (self.out / "corpus.jsonl").open("w", encoding="utf-8")
        per_problem, kept_total, ac_total = {}, 0, 0
        for pid in pids:
            rows = [(rec, verdicts[(pid, rec["idx"])]) for rec in self._sample(pid)]
            non_ac = [(rec, v) for rec, v in rows if v["verdict"] != "AC"]
            ac_n = sum(1 for _, v in rows if v["verdict"] == "AC")
            kept = non_ac[:self.cap]
            for rec, v in kept:
                corpus.write(json.dumps(self._record(pid, rec, v), ensure_ascii=False) + "\n")
            per_problem[pid] = {"judged": len(rows), "ac_unexpected": ac_n, "non_ac_kept": len(kept)}
            kept_total += len(kept)
            ac_total += ac_n
        corpus.close()
        report = {"problems": len(pids), "kept_submissions": kept_total,
                  "unexpected_ac_dropped": ac_total,
                  "problems_with_ge1_non_ac": sum(1 for p in per_problem.values() if p["non_ac_kept"] >= 1),
                  "per_problem": per_problem}
        (self.out / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        return report

    def _judgeable(self):
        f = Path(self.config["paths"]["artifacts"]) / "judgeable_problems.json"
        return sorted(json.loads(f.read_text(encoding="utf-8"))["judgeable"])

    def _sample(self, pid):
        f = self.problems / pid / self.lang / "incorrect.jsonl"
        recs = [json.loads(l) for l in f.read_text(encoding="utf-8").split("\n") if l]
        return self._pick(recs, pid)

    def _pick(self, recs, pid):
        recs = list(recs)
        random.Random(f"{self.seed}:{pid}").shuffle(recs)
        return recs[:self.max_judge]

    def _judge_all(self, tasks):
        def one(t):
            pid, rec = t
            return ((pid, rec["idx"]), self.judge.judge(self.problems / pid, rec["code"], self.lang))
        with ThreadPoolExecutor(max_workers=8) as ex:
            return dict(ex.map(one, tasks))

    def _record(self, pid, rec, verdict):
        meta = json.loads((self.problems / pid / "meta.json").read_text(encoding="utf-8"))
        return {"submission_id": f"human:{pid}:{rec['idx']}", "problem_id": pid, "arm": "human",
                "language": self.lang, "source": rec["code"], "verdict": verdict["verdict"],
                "peak_time_ms": verdict["peak_time_ms"], "peak_mem_kb": verdict["peak_mem_kb"],
                "difficulty_bin": meta["difficulty_bin"], "algo_families": meta["algo_families"]}
