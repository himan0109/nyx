import subprocess
import json
import re
from ..utils import load_config, save_result, timestamp

cfg = load_config()
HOLEHE_DIR = cfg["tool_paths"]["holehe"]


def run(target: str, timeout: int = 120) -> dict:
    cmd = ["holehe", target, "--only-used", "--no-color"]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)

    registered = []
    not_found = []
    for line in result.stdout.splitlines():
        if "[+]" in line:
            site = line.split("[+]")[-1].strip()
            registered.append(site)
        elif "[-]" in line:
            site = line.split("[-]")[-1].strip()
            not_found.append(site)

    data = {
        "module": "osint.email",
        "target": target,
        "timestamp": timestamp(),
        "registered_on": registered,
        "not_found_on": not_found,
        "registered_count": len(registered),
    }
    save_result("osint_email", data)
    return data
