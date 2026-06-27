from src.common.config import Config
from src.judge.sandbox_runner import SandboxRunner


def test_profile_denies_network_and_external_writes():
    p = SandboxRunner(Config())._profile("/var/folders/x/scratchdir")
    assert "(deny network*)" in p
    assert "(deny file-write*)" in p
    assert "scratchdir" in p
    assert p.startswith("(version 1)")
