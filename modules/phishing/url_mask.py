import subprocess
import re
from pathlib import Path
from ..utils import load_config, save_result, timestamp

cfg = load_config()
FACAD1NG_DIR = cfg["tool_paths"]["facad1ng"]

SHORTENERS = ["tinyurl", "osdb", "dagd", "clckru"]


def run(url: str, custom_word: str = "", shortener: str = "tinyurl") -> dict:
    script = str(Path(FACAD1NG_DIR) / "facad1ng.py")
    cmd = ["python3", script, "-u", url, "-s", shortener]
    if custom_word:
        cmd += ["-w", custom_word]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

    masked_urls = re.findall(r"https?://\S+", result.stdout)

    data = {
        "module": "phishing.url_mask",
        "original_url": url,
        "shortener": shortener,
        "timestamp": timestamp(),
        "masked_urls": masked_urls,
        "raw": result.stdout.strip(),
        "available_shorteners": SHORTENERS,
    }
    save_result("phishing_urlmask", data)
    return data
