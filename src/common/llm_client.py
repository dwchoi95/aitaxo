import hashlib
import json
import time
from pathlib import Path


class LlmClient:
    def __init__(self, config):
        self.config = config
        self.cache_dir = Path(config["paths"]["cache"])
        self.log_dir = Path(config["paths"]["llm_calls"])
        self._openai = None
        self._anthropic = None

    # one public method: complete a chat request, with cache + retry + logging.
    # nonce gives self-consistency samples distinct cache keys (and an OpenAI seed) so repeated
    # identical prompts produce independent draws instead of a single cached one.
    def complete(self, model, messages, temperature=0.0, max_tokens=1024, n=1, nonce=None,
                 reasoning_effort=None, dry_run=False):
        params = {"temperature": temperature, "max_tokens": max_tokens, "n": n}
        if nonce is not None:
            params["nonce"] = nonce
        if reasoning_effort is not None:
            params["reasoning_effort"] = reasoning_effort
        key = self._key(model, params, messages)
        if dry_run:
            return {"dry_run": True, "model": model, "params": params,
                    "messages": messages, "cache_key": key}
        cached = self._read_cache(key)
        if cached is not None:
            self._log(key, model, params, messages, cached, True, 0.0)
            return cached
        t0 = time.time()
        result = self._call_with_retry(model, messages, params)
        latency = time.time() - t0
        self._write_cache(key, result)
        self._log(key, model, params, messages, result, False, latency)
        return result

    def _provider(self, model):
        return "anthropic" if model.startswith("claude") else "openai"

    def _call_with_retry(self, model, messages, params, retries=5):
        for attempt in range(retries):
            try:
                if self._provider(model) == "openai":
                    return self._call_openai(model, messages, params)
                return self._call_anthropic(model, messages, params)
            except Exception as e:
                # billing/quota exhaustion will not recover within the backoff window — fail
                # fast so the caller can stop cleanly and save partial progress
                if "insufficient_quota" in str(e) or "billing" in str(e).lower():
                    raise
                if attempt == retries - 1:
                    raise
                time.sleep(2 ** attempt)

    def _call_openai(self, model, messages, params):
        client = self._openai_client()
        kw = {"model": model, "messages": messages, "n": params["n"]}
        if "nonce" in params:
            kw["seed"] = params["nonce"]
        # gpt-5 / o-series reasoning models: no temperature, use max_completion_tokens
        if model.startswith(("gpt-5", "o1", "o3", "o4")):
            kw["max_completion_tokens"] = params["max_tokens"]
            if "reasoning_effort" in params:
                kw["reasoning_effort"] = params["reasoning_effort"]
        else:
            kw["max_tokens"] = params["max_tokens"]
            kw["temperature"] = params["temperature"]
        r = client.chat.completions.create(**kw)
        return {"texts": [c.message.content for c in r.choices],
                "usage": {"in": r.usage.prompt_tokens, "out": r.usage.completion_tokens}}

    def _call_anthropic(self, model, messages, params):
        client = self._anthropic_client()
        system = "\n".join(m["content"] for m in messages if m["role"] == "system")
        convo = [m for m in messages if m["role"] != "system"]
        kw = {"model": model, "messages": convo, "max_tokens": params["max_tokens"],
              "temperature": params["temperature"]}
        if system:
            kw["system"] = system
        r = client.messages.create(**kw)
        return {"texts": ["".join(b.text for b in r.content if b.type == "text")],
                "usage": {"in": r.usage.input_tokens, "out": r.usage.output_tokens}}

    def _openai_client(self):
        if self._openai is None:
            from openai import OpenAI
            self._openai = OpenAI()
        return self._openai

    def _anthropic_client(self):
        if self._anthropic is None:
            from anthropic import Anthropic
            self._anthropic = Anthropic()
        return self._anthropic

    def _key(self, model, params, messages):
        blob = json.dumps({"model": model, "params": params, "messages": messages}, sort_keys=True)
        return hashlib.sha256(blob.encode()).hexdigest()

    def _read_cache(self, key):
        f = self.cache_dir / f"{key}.json"
        return json.loads(f.read_text()) if f.exists() else None

    def _write_cache(self, key, result):
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        (self.cache_dir / f"{key}.json").write_text(json.dumps(result, ensure_ascii=False))

    def _log(self, key, model, params, messages, result, cache_hit, latency):
        self.log_dir.mkdir(parents=True, exist_ok=True)
        rec = {"key": key, "model": model, "params": params, "messages": messages,
               "result": result, "cache_hit": cache_hit, "latency_s": round(latency, 3),
               "ts": time.time()}
        fname = f"{int(time.time() * 1000)}_{key[:8]}.json"
        (self.log_dir / fname).write_text(json.dumps(rec, ensure_ascii=False))
