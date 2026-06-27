from src.common.config import Config
from src.generation.ai_generator import AiGenerator


def _g():
    return AiGenerator(Config())


def test_extract_fenced_block():
    g = _g()
    assert g._extract("text\n```cpp\nint main(){}\n```\nmore") == "int main(){}"
    assert g._extract("```\n#include <x>\n```") == "#include <x>"


def test_extract_unfenced_code_and_none():
    g = _g()
    assert g._extract("#include <bits/stdc++.h>\nint main(){}") is not None
    assert g._extract("Sorry, I cannot help.") is None


def test_clip_bounds_length():
    g = _g()
    long = "a" * (g.size_cap + 500)
    out = g._clip(long)
    assert len(out) <= g.size_cap + 40
    assert g._clip("short") == "short"
