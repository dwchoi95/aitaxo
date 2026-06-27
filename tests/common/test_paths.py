from src.common.config import Config
from src.common.paths import Paths


def test_paths_resolve():
    p = Paths(Config())
    assert str(p.data) == "data"
    assert str(p.artifacts) == "artifacts"
    assert str(p.cache) == "logs/cache"
