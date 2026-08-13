import subprocess
from pathlib import Path
from ..utils import load_config, save_result, timestamp

cfg = load_config()
WORDLISTS = cfg.get("wordlists", {})

SERVICES = ["ssh", "ftp", "http", "https", "smb", "rdp", "telnet", "mysql", "postgres"]


def run(target: str, service: str = "ssh", username: str = "admin",
        wordlist: str = "", port: int = 0, dry_run: bool = False) -> dict:
    wl = wordlist or WORDLISTS.get("rockyou", "/usr/share/wordlists/rockyou.txt")
    port_flag = ["-s", str(port)] if port else []

    if dry_run:
        return {
            "module": "network.brute",
            "target": target,
            "service": service,
            "username": username,
            "wordlist": wl,
            "dry_run": True,
            "timestamp": timestamp(),
            "available_services": SERVICES,
        }

    cmd = (
        ["hydra", "-l", username, "-P", wl] +
        port_flag +
        [target, service, "-t", "4", "-V"]
    )
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)

    found = []
    for line in result.stdout.splitlines():
        if "[" in line and "login:" in line:
            found.append(line.strip())

    data = {
        "module": "network.brute",
        "target": target,
        "service": service,
        "username": username,
        "timestamp": timestamp(),
        "credentials_found": found,
        "raw": result.stdout[:2000],
    }
    save_result("network_brute", data)
    return data


def crack_hash(hash_str: str, hash_type: str = "md5", wordlist: str = "") -> dict:
    wl = wordlist or WORDLISTS.get("rockyou", "/usr/share/wordlists/rockyou.txt")
    hash_file = "/tmp/nyx_hash.txt"
    with open(hash_file, "w") as f:
        f.write(hash_str + "\n")

    cmd = ["hashcat", "-m", _hashcat_mode(hash_type), hash_file, wl, "--force"]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

    cracked = []
    for line in result.stdout.splitlines():
        if ":" in line and not line.startswith("#"):
            cracked.append(line.strip())

    data = {
        "module": "network.hash_crack",
        "hash": hash_str,
        "hash_type": hash_type,
        "timestamp": timestamp(),
        "cracked": cracked,
    }
    save_result("network_hashcrack", data)
    return data


def _hashcat_mode(hash_type: str) -> str:
    modes = {
        "md5": "0", "sha1": "100", "sha256": "1400", "sha512": "1700",
        "ntlm": "1000", "bcrypt": "3200", "wpa": "22000",
    }
    return modes.get(hash_type.lower(), "0")
