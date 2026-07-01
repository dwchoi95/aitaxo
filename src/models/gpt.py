import asyncio
import hashlib
import json
from pathlib import Path

from openai import AsyncOpenAI


class Gpt:
    # General async OpenAI chat wrapper, reused across tasks (generation now, judging later). Each
    # call requests a single completion with only model/messages/temperature; many calls are fired
    # concurrently for throughput. Completions are cached by (model, temperature, messages, nonce)
    # so re-runs are free; nonce lives only in the cache key (not sent to the API), so it
    # distinguishes repeated samples of the same prompt without forcing a fixed seed. Transient
    # errors are retried with backoff; quota/billing errors fail fast.
    def __init__(self, config):
        self.client = AsyncOpenAI()
        self.cache = Path(config["paths"]["cache"])

    async def complete(self, model, system, user, temperature, nonce, retries=3):
        msgs = [{"role": "system", "content": system}, {"role": "user", "content": user}]
        return await self.chat(model, msgs, temperature, nonce, retries)

    async def chat(self, model, messages, temperature, nonce, retries=3):
        # arbitrary multi-turn message thread (used by self-refine, which appends to the zero-shot
        # conversation). Cached by (model, temperature, messages, nonce) like complete().
        key = self._key(model, temperature, nonce, messages)
        cached = self._read(key)
        if cached is not None:
            return cached
        kwargs = {"model": model, "messages": messages, "temperature": temperature}
        for attempt in range(retries):
            try:
                r = await self.client.chat.completions.create(**kwargs)
                text = r.choices[0].message.content or ""
                self._write(key, text)
                return text
            except Exception as e:
                s = str(e).lower()
                if "insufficient_quota" in s or "billing" in s:
                    raise
                if "temperature" in s and "temperature" in kwargs:
                    # some reasoning models accept only the default temperature; drop it and retry
                    del kwargs["temperature"]
                    continue
                if attempt == retries - 1:
                    raise
                await asyncio.sleep(min(30, 2 ** attempt))

    def _key(self, model, temperature, nonce, msgs):
        blob = json.dumps([model, temperature, nonce, msgs], sort_keys=True)
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()

    def _read(self, key):
        f = self.cache / f"{key}.json"
        return json.loads(f.read_text(encoding="utf-8")) if f.exists() else None

    def _write(self, key, text):
        self.cache.mkdir(parents=True, exist_ok=True)
        (self.cache / f"{key}.json").write_text(json.dumps(text, ensure_ascii=False), encoding="utf-8")
