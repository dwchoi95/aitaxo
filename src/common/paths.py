from pathlib import Path


class Paths:
    def __init__(self, config):
        p = config["paths"]
        self.data = Path(p["data"])
        self.artifacts = Path(p["artifacts"])
        self.results = Path(p["results"])
        self.logs = Path(p["logs"])
        self.human = Path(p["human"])
        self.paper = Path(p["paper"])
        self.cache = Path(p["cache"])
        self.llm_calls = Path(p["llm_calls"])

    def ensure(self):
        for d in (self.data, self.artifacts, self.results, self.logs,
                  self.human, self.cache, self.llm_calls):
            d.mkdir(parents=True, exist_ok=True)
