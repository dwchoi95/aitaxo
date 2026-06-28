import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

SEARCH = "https://dblp.org/search/publ/api"
UA = {"User-Agent": "aitaxo-refbot/1.0 (academic reference verification)"}


class ReferenceFetcher:
    # Populate references.bib only from verbatim BibTeX of an authoritative bibliographic source
    # (plan 11.2). Semantic Scholar's keyless API rate-limited this host (429), so we use DBLP --
    # the authoritative CS bibliography -- fetching each entry's verbatim .bib and logging
    # provenance (DBLP key, title, venue, DOI) for the integrity audit. No entry is hand-written.
    def __init__(self, config):
        self.config = config
        self.logs = Path(config["paths"]["logs"])
        self.bib = Path("paper/references.bib")

    def run(self, works):
        blocks, provenance = [], []
        for w in works:
            if w.get("dblp_key"):                       # verified key -> fetch .bib directly
                chosen = {"key": w["dblp_key"], "title": w.get("title"), "venue": w.get("venue"),
                          "year": w.get("year"), "doi": w.get("doi")}
            else:
                chosen = self._pick(self._search(w["query"]), w.get("match"))
            if not chosen:
                provenance.append({"key": w["key"], "query": w.get("query"), "status": "NOT_FOUND"})
                continue
            bibtex = self._rekey(self._bib(chosen["key"]), w["key"])
            if not bibtex.strip().startswith("@"):
                provenance.append({"key": w["key"], "query": w["query"], "status": "NO_BIB"})
                continue
            blocks.append(bibtex.strip())
            provenance.append({"key": w["key"], "query": w.get("query"), "dblp_key": chosen["key"],
                               "title": chosen.get("title"), "venue": chosen.get("venue"),
                               "year": chosen.get("year"), "doi": chosen.get("doi")})
            time.sleep(2.0)
        self.bib.parent.mkdir(parents=True, exist_ok=True)
        self.bib.write_text("\n\n".join(blocks) + "\n", encoding="utf-8")
        self.logs.mkdir(parents=True, exist_ok=True)
        (self.logs / "refs_provenance.json").write_text(
            json.dumps(provenance, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"requested": len(works), "fetched": len(blocks),
                "missing": [p["key"] for p in provenance if p.get("status")]}

    def _search(self, query, retries=6):
        url = f"{SEARCH}?q={urllib.parse.quote(query)}&format=json&h=8"
        for attempt in range(retries):
            try:
                with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
                    hits = json.loads(r.read()).get("result", {}).get("hits", {}).get("hit", [])
                return [h["info"] for h in hits]
            except Exception as e:
                if attempt == retries - 1:
                    return []
                time.sleep(3 * 2 ** attempt if ("429" in str(e)) else 2)
        return []

    def _pick(self, hits, match):
        if not hits:
            return None
        cand = hits
        if match:
            m = match.lower()
            cand = [h for h in hits if m in (h.get("title") or "").lower()] or hits
        # prefer a published venue over the arXiv/CoRR preprint
        pub = [h for h in cand if (h.get("venue") or "").lower() not in ("corr", "arxiv")]
        return (pub or cand)[0]

    def _bib(self, key, retries=5):
        url = f"https://dblp.org/rec/{key}.bib?param=1"
        for attempt in range(retries):
            try:
                with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
                    return r.read().decode("utf-8")
            except Exception as e:
                if attempt == retries - 1:
                    return ""
                time.sleep(3 * 2 ** attempt if ("429" in str(e)) else 2)
        return ""

    def _rekey(self, bibtex, key):
        return re.sub(r"(@\w+\s*\{)[^,]+,", r"\1" + key + ",", bibtex, count=1)
