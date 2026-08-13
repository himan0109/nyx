import shutil
from pathlib import Path
from ..utils import load_config, save_result, timestamp

cfg = load_config()
APK_DIR = Path(cfg["tool_paths"]["apks"])
KEYDROID_DIR = Path(cfg["tool_paths"]["keydroid"])


def list_payloads() -> dict:
    apks = []
    for d in [APK_DIR, KEYDROID_DIR]:
        if d.exists():
            for f in d.glob("*.apk"):
                apks.append({
                    "name": f.name,
                    "path": str(f),
                    "size_kb": round(f.stat().st_size / 1024, 1),
                })

    data = {
        "module": "payload.apk",
        "timestamp": timestamp(),
        "apks": apks,
        "count": len(apks),
    }
    save_result("payload_apk_list", data)
    return data


def copy_to(apk_name: str, dest: str) -> dict:
    for d in [APK_DIR, KEYDROID_DIR]:
        src = d / apk_name
        if src.exists():
            dest_path = Path(dest)
            shutil.copy2(src, dest_path)
            return {
                "module": "payload.apk.copy",
                "source": str(src),
                "destination": str(dest_path),
                "timestamp": timestamp(),
                "status": "ok",
            }
    return {"error": f"APK '{apk_name}' not found", "timestamp": timestamp()}
