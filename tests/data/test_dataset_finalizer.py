from src.common.config import Config
from src.data.dataset_finalizer import DatasetFinalizer


def test_ai_record_keeps_only_non_ac_verdicts(monkeypatch):
    f = DatasetFinalizer(Config())
    samples = [{"attempt": 0, "code": "a", "verdict": "AC"},
               {"attempt": 1, "code": "b", "verdict": "WA"},
               {"attempt": 2, "code": None, "verdict": "NO_CODE"},
               {"attempt": 3, "code": "d", "verdict": "CE"}]
    kept = [s for s in samples if s["verdict"] not in ("AC", "NO_CODE")][:f.cap]
    assert [s["verdict"] for s in kept] == ["WA", "CE"]
