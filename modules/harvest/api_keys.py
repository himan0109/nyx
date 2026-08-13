import subprocess
import json
from pathlib import Path
from ..utils import load_config, save_result, timestamp

cfg = load_config()
UNSECURED_DIR = cfg["tool_paths"]["unsecured_api"]


def run(query: str, max_results: int = 50, dry_run: bool = False) -> dict:
    if dry_run:
        return {
            "module": "harvest.api_keys",
            "query": query,
            "dry_run": True,
            "timestamp": timestamp(),
            "description": "Scans GitHub for exposed API keys (OpenAI sk-proj-*, Anthropic sk-ant-api*, Google AIzaSy*)",
            "project": str(UNSECURED_DIR),
        }

    project_dir = Path(UNSECURED_DIR) / "UnsecuredAPIKeys.CLI"
    cmd = ["dotnet", "run", "--project", str(project_dir), "--", query, "--max", str(max_results)]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300, cwd=UNSECURED_DIR)

    keys = []
    for line in result.stdout.splitlines():
        try:
            entry = json.loads(line)
            keys.append(entry)
        except json.JSONDecodeError:
            if "sk-" in line or "AIzaSy" in line:
                keys.append({"raw": line.strip()})

    data = {
        "module": "harvest.api_keys",
        "query": query,
        "timestamp": timestamp(),
        "keys_found": keys,
        "count": len(keys),
        "raw": result.stdout[:2000],
    }
    save_result("harvest_api_keys", data)
    return data
