import subprocess
import json
import socket
import sys
from pathlib import Path
from ..utils import load_config, save_result, timestamp

cfg = load_config()
AUTO_DOMAIN_DIR = cfg["tool_paths"]["auto_domain"]


def _whois(target: str) -> str:
    try:
        result = subprocess.run(["whois", target], capture_output=True, text=True, timeout=20)
        return result.stdout[:2000]
    except Exception as e:
        return str(e)


def _dns(target: str) -> dict:
    records = {}
    for rtype in ["A", "MX", "NS", "TXT"]:
        try:
            r = subprocess.run(
                ["dig", "+short", rtype, target],
                capture_output=True, text=True, timeout=10,
            )
            records[rtype] = [l.strip() for l in r.stdout.splitlines() if l.strip()]
        except Exception:
            records[rtype] = []
    return records


def _availability(target: str) -> bool:
    script = str(Path(AUTO_DOMAIN_DIR) / "AutoDomainSearch.py")
    try:
        r = subprocess.run(
            ["python3", script, target],
            capture_output=True, text=True, timeout=15,
        )
        return "Available" in r.stdout and "Not Available" not in r.stdout
    except Exception:
        return False


def run(target: str) -> dict:
    dns = _dns(target)
    whois_raw = _whois(target)
    available = _availability(target)

    data = {
        "module": "osint.domain",
        "target": target,
        "timestamp": timestamp(),
        "available": available,
        "dns_records": dns,
        "whois_excerpt": whois_raw[:1500],
    }
    save_result("osint_domain", data)
    return data
