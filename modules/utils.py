import json
import os
import yaml
from datetime import datetime
from pathlib import Path

_CONFIG_PATH = Path(__file__).parent.parent / "config.yaml"
_cfg = None


def load_config() -> dict:
    global _cfg
    if _cfg is None:
        with open(_CONFIG_PATH) as f:
            _cfg = yaml.safe_load(f)
    return _cfg


def timestamp() -> str:
    return datetime.now().isoformat(timespec="seconds")


def save_result(name: str, data: dict) -> Path:
    cfg = load_config()
    sessions_dir = Path(cfg["output"]["sessions_dir"])

    today = datetime.now().strftime("%Y-%m-%d")
    session_dir = sessions_dir / today
    session_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.now().strftime("%H%M%S")
    outfile = session_dir / f"{name}_{ts}.json"
    with open(outfile, "w") as f:
        json.dump(data, f, indent=2, default=str)

    return outfile
