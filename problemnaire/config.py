import json
from dataclasses import dataclass, field, asdict
from pathlib import Path


CONFIG_DIR = Path.home() / ".problemnaire"
CONFIG_FILE = CONFIG_DIR / "config.json"


@dataclass
class Config:
    api_key: str = ""
    handles: dict = field(default_factory=dict)   # {"cf": "...", "lc": "...", "cc": "..."}
    verified: dict = field(default_factory=dict)  # {"cf": True, "lc": False, "cc": False}


def load_config() -> Config:
    if not CONFIG_FILE.exists():
        return Config()
    with open(CONFIG_FILE, encoding="utf-8") as f:
        data = json.load(f)
    c = Config()
    c.api_key = data.get("api_key", "")
    c.handles = data.get("handles", {})
    c.verified = data.get("verified", {})
    return c


def save_config(config: Config) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(asdict(config), f, indent=2)


def is_setup_complete(config: Config) -> bool:
    return bool(config.handles)


def has_api_key(config: Config) -> bool:
    return bool(config.api_key)
