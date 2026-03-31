import json
from pathlib import Path

DEFAULT_CONFIG = {
    "acr_value": 1.0,
    "rank_value": 1,
    "regulate_target_v": 42.32,
}

CONFIG_PATH = Path(__file__).resolve().parent / "user_config.json"


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        return DEFAULT_CONFIG.copy()

    try:
        with CONFIG_PATH.open("r", encoding="utf-8") as f:
            data = json.load(f)
            if not isinstance(data, dict):
                return DEFAULT_CONFIG.copy()
    except (json.JSONDecodeError, OSError):
        return DEFAULT_CONFIG.copy()

    cfg = DEFAULT_CONFIG.copy()
    cfg.update(data)
    return cfg


def save_config(config: dict) -> None:
    cfg = DEFAULT_CONFIG.copy()
    cfg.update(config)

    with CONFIG_PATH.open("w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)
