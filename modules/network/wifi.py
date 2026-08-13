import subprocess
import re
from ..utils import load_config, save_result, timestamp

cfg = load_config()
WORDLISTS = cfg.get("wordlists", {})


def scan_networks(interface: str = "wlan0") -> dict:
    result = subprocess.run(
        ["iwlist", interface, "scan"],
        capture_output=True, text=True, timeout=30,
    )

    networks = []
    current = {}
    for line in result.stdout.splitlines():
        line = line.strip()
        if line.startswith("Cell"):
            if current:
                networks.append(current)
            current = {}
        elif "ESSID" in line:
            m = re.search(r'ESSID:"(.+)"', line)
            if m:
                current["ssid"] = m.group(1)
        elif "Encryption key" in line:
            current["encrypted"] = "on" in line.lower()
        elif "Signal level" in line:
            m = re.search(r"Signal level=(.+?) ", line)
            if m:
                current["signal"] = m.group(1).strip()
        elif "Address" in line:
            m = re.search(r"Address: (.+)", line)
            if m:
                current["bssid"] = m.group(1).strip()

    if current:
        networks.append(current)

    data = {
        "module": "network.wifi.scan",
        "interface": interface,
        "timestamp": timestamp(),
        "networks": networks,
        "count": len(networks),
    }
    save_result("network_wifi_scan", data)
    return data


def crack_wpa(capture_file: str, wordlist: str = "", dry_run: bool = False) -> dict:
    wl = wordlist or WORDLISTS.get("rockyou", "/usr/share/wordlists/rockyou.txt")

    if dry_run:
        return {
            "module": "network.wifi.crack",
            "capture_file": capture_file,
            "wordlist": wl,
            "dry_run": True,
            "timestamp": timestamp(),
        }

    cmd = ["aircrack-ng", capture_file, "-w", wl]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)

    key_found = None
    for line in result.stdout.splitlines():
        if "KEY FOUND" in line:
            m = re.search(r"KEY FOUND! \[ (.+?) \]", line)
            if m:
                key_found = m.group(1)

    data = {
        "module": "network.wifi.crack",
        "capture_file": capture_file,
        "timestamp": timestamp(),
        "key_found": key_found,
        "raw": result.stdout[-1000:],
    }
    save_result("network_wifi_crack", data)
    return data
