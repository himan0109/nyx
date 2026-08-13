import subprocess
import json
import re
from pathlib import Path
from ..utils import load_config, save_result, timestamp

cfg = load_config()
SHERLOCK_DIR = cfg["tool_paths"]["sherlock"]


def run(target: str, timeout: int = 120) -> dict:
    outfile = f"/tmp/sherlock_{target}.txt"
    cmd = [
        "python3", f"{SHERLOCK_DIR}/sherlock_project/sherlock.py",
        target,
        "--output", outfile,
        "--print-found",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)

    found = []
    if Path(outfile).exists():
        with open(outfile) as f:
            for line in f:
                line = line.strip()
                if line.startswith("http"):
                    found.append(line)

    urls_in_stdout = re.findall(r"https?://\S+", result.stdout)
    all_found = list(dict.fromkeys(found + urls_in_stdout))

    data = {
        "module": "osint.username",
        "target": target,
        "timestamp": timestamp(),
        "accounts_found": len(all_found),
        "accounts": all_found,
        "raw_stderr": result.stderr[-500:] if result.stderr else "",
    }
    save_result("osint_username", data)
    return data
