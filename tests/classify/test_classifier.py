from src.common.config import Config
from src.classify.classifier import Classifier


def test_slug_sanitizes_model_name():
    c = Classifier(Config())
    assert c._slug("gpt-5.5") == "gpt-5-5"
    assert c._slug("claude-sonnet-4-6") == "claude-sonnet-4-6"
