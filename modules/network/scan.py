import subprocess
import re
from ..utils import save_result, timestamp


def run(target: str, ports: str = "1-1000", fast: bool = False, dry_run: bool = False) -> dict:
    if dry_run:
        return {
            "module": "network.scan",
            "target": target,
            "ports": ports,
            "dry_run": True,
            "timestamp": timestamp(),
            "status": "dry_run_ok",
        }

    flags = ["-sV", "--open"]
    if fast:
        flags = ["-T4", "-F", "--open"]

    cmd = ["nmap"] + flags + ["-p", ports, target]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

    open_ports = []
    for line in result.stdout.splitlines():
        m = re.match(r"(\d+)/(\w+)\s+open\s+(.+)", line.strip())
        if m:
            open_ports.append({
                "port": int(m.group(1)),
                "protocol": m.group(2),
                "service": m.group(3).strip(),
            })

    data = {
        "module": "network.scan",
        "target": target,
        "ports_scanned": ports,
        "timestamp": timestamp(),
        "open_ports": open_ports,
        "open_count": len(open_ports),
        "raw": result.stdout[:3000],
    }
    save_result("network_scan", data)
    return data
