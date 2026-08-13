import subprocess
import json
from pathlib import Path
from ..utils import load_config, save_result, timestamp

cfg = load_config()
EXIFTOOL_DIR = cfg["tool_paths"]["exiftool"]


def run(filepath: str, strip: bool = False, timeout: int = 30) -> dict:
    exiftool_bin = str(Path(EXIFTOOL_DIR) / "exiftool")
    if not Path(exiftool_bin).exists():
        exiftool_bin = "exiftool"

    if strip:
        cmd = [exiftool_bin, "-all=", filepath]
    else:
        cmd = [exiftool_bin, "-json", filepath]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)

    meta = {}
    if not strip:
        try:
            parsed = json.loads(result.stdout)
            meta = parsed[0] if parsed else {}
        except json.JSONDecodeError:
            meta = {"raw": result.stdout}

    sensitive_keys = [
        "gpslatitude", "gpslongitude", "gpsposition", "author", "creator",
        "createdate", "modifydate", "software", "make", "model",
        "serialnumber", "ownername",
    ]
    flagged = {k: v for k, v in meta.items() if k.lower().replace(" ", "") in sensitive_keys}

    data = {
        "module": "osint.metadata",
        "file": filepath,
        "timestamp": timestamp(),
        "stripped": strip,
        "metadata": meta,
        "sensitive_fields": flagged,
    }
    save_result("osint_metadata", data)
    return data
