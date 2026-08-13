import subprocess
import json
import sys
from pathlib import Path
from ..utils import load_config, save_result, timestamp

cfg = load_config()
IPGEO_DIR = cfg["tool_paths"]["ipgeoloc"]


def run(target: str, timeout: int = 30) -> dict:
    script = str(Path(IPGEO_DIR) / "ipgeolocation.py")
    cmd = ["python3", script, "-t", target, "-g"]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)

    geo = {}
    for line in result.stdout.splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            geo[k.strip().lower().replace(" ", "_")] = v.strip()

    data = {
        "module": "osint.ip_geo",
        "target": target,
        "timestamp": timestamp(),
        "geolocation": geo,
        "raw": result.stdout,
    }
    save_result("osint_ip_geo", data)
    return data
