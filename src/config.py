import os
from dataclasses import dataclass
from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass


@dataclass(frozen=True)
class Config:
    data_root: Path
    out_dir: Path
    model: str
    temperature: float
    openai_api_key: str | None

    @property
    def codenet_root(self) -> Path:
        return self.data_root / "Project_CodeNet"

    @property
    def codeforces_root(self) -> Path:
        return self.data_root / "Codeforces"


def load_config() -> Config:
    data_root = Path(
        os.environ.get("AITAXO_DATA_ROOT", "/Users/cdw/VSCode/aria/data")
    ).expanduser()
    out_dir = Path(os.environ.get("AITAXO_OUT_DIR", "./data/generated")).expanduser()
    out_dir.mkdir(parents=True, exist_ok=True)
    return Config(
        data_root=data_root,
        out_dir=out_dir,
        model=os.environ.get("AITAXO_MODEL", "gpt-4o"),
        temperature=float(os.environ.get("AITAXO_TEMPERATURE", "0.7")),
        openai_api_key=os.environ.get("OPENAI_API_KEY"),
    )
