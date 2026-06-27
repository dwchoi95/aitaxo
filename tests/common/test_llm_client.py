from src.common.config import Config
from src.common.llm_client import LlmClient


def test_dry_run_assembles_without_api():
    client = LlmClient(Config())
    out = client.complete("gpt-3.5-turbo-0125",
                          [{"role": "user", "content": "hi"}],
                          temperature=1.0, max_tokens=10, dry_run=True)
    assert out["dry_run"] is True
    assert out["model"] == "gpt-3.5-turbo-0125"
    assert out["messages"][0]["content"] == "hi"
    assert out["params"]["temperature"] == 1.0
    assert isinstance(out["cache_key"], str) and len(out["cache_key"]) == 64


def test_provider_routing():
    client = LlmClient(Config())
    assert client._provider("claude-sonnet-4-6") == "anthropic"
    assert client._provider("gpt-3.5-turbo-0125") == "openai"
    assert client._provider("gpt-5.5") == "openai"
