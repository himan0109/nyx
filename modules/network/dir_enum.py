import subprocess
import re
from ..utils import load_config, save_result, timestamp

cfg = load_config()
WORDLISTS = cfg.get("wordlists", {})

TOOLS = ["gobuster", "dirb"]


def run(target: str, wordlist: str = "", extensions: str = "php,html,txt,js",
        threads: int = 20, dry_run: bool = False) -> dict:
    wl = wordlist or WORDLISTS.get("common", "/usr/share/wordlists/dirb/common.txt")

    if dry_run:
        return {
            "module": "network.dir_enum",
            "target": target,
            "wordlist": wl,
            "dry_run": True,
            "timestamp": timestamp(),
        }

    cmd = [
        "gobuster", "dir",
        "-u", target,
        "-w", wl,
        "-x", extensions,
        "-t", str(threads),
        "--no-error",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

    found = []
    for line in result.stdout.splitlines():
        m = re.match(r"/([\w./\-]+)\s+\(Status: (\d+)\)", line.strip())
        if m:
            found.append({"path": "/" + m.group(1), "status": int(m.group(2))})

    data = {
        "module": "network.dir_enum",
        "target": target,
        "timestamp": timestamp(),
        "paths_found": found,
        "count": len(found),
        "raw": result.stdout[:2000],
    }
    save_result("network_dir_enum", data)
    return data


def nuclei_scan(target: str, templates: str = "cves", dry_run: bool = False) -> dict:
    if dry_run:
        return {
            "module": "network.nuclei",
            "target": target,
            "templates": templates,
            "dry_run": True,
            "timestamp": timestamp(),
        }

    cmd = ["nuclei", "-u", target, "-t", templates, "-json"]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

    findings = []
    import json
    for line in result.stdout.splitlines():
        try:
            findings.append(json.loads(line))
        except json.JSONDecodeError:
            pass

    data = {
        "module": "network.nuclei",
        "target": target,
        "templates": templates,
        "timestamp": timestamp(),
        "findings": findings,
        "count": len(findings),
    }
    save_result("network_nuclei", data)
    return data
