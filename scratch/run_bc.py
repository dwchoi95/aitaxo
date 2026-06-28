import json
from concurrent.futures import ThreadPoolExecutor
from src.common.config import Config
from src.classify.taxonomy_judge import TaxonomyJudge
from src.classify.judge_selector import JudgeSelector

cfg = Config()
j = TaxonomyJudge(cfg)
items = JudgeSelector(cfg)._gold_items()

def run(its, effort, out):
    def one(it):
        r = j.classify(it["submission"], "gpt-5.5", effort=effort)
        return {"submission_id": it["submission"]["submission_id"], "arm": it["submission"]["arm"],
                "primary": r["primary"], "secondary": r["secondary"], "leaves": r["leaves"],
                "gold": sorted(it["gold"])}
    with ThreadPoolExecutor(max_workers=8) as ex:
        res = list(ex.map(one, its))
    open(out, "w").write("\n".join(json.dumps(x, ensure_ascii=False) for x in res) + "\n")
    print("wrote", out, len(res), flush=True)

run(items, "low", "artifacts/judge_ablation/g5_tuned_low.jsonl")        # (b) full 346
run(items[:100], "medium", "artifacts/judge_ablation/g5_tuned_med100.jsonl")  # (c) 100 medium
print("BC_DONE", flush=True)
