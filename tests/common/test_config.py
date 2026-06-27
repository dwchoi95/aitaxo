from src.common.config import Config


def test_config_loads_fixed_values():
    c = Config()
    assert c["dataset"]["name"] == "deepmind/code_contests"
    assert c["dataset"]["split"] == "test"
    assert c["generator"]["model"] == "gpt-3.5-turbo"
    assert c["generator"]["temperature"] == 1.0
    assert c["self_reflection"]["n_iters"] == 5
    assert c["paths"]["data"] == "data"
