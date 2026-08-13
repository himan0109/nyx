import subprocess
import json
from pathlib import Path
from ..utils import load_config, save_result, timestamp

cfg = load_config()
OMINIS_DIR = cfg["tool_paths"]["ominis"]


def run(target: str, pages: int = 3, timeout: int = 60) -> dict:
    script = str(Path(OMINIS_DIR) / "ominis.py")
    cmd = ["python3", script, "-s", target, "-p", str(pages)]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)

    import re
    urls = re.findall(r"https?://\S+", result.stdout)

    data = {
        "module": "osint.web_osint",
        "target": target,
        "timestamp": timestamp(),
        "results_found": len(urls),
        "urls": urls,
        "raw": result.stdout[:3000],
    }
    save_result("osint_web", data)
    return data
