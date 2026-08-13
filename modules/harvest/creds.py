import subprocess
import json
from ..utils import save_result, timestamp


def run(repo_url: str = "", local_path: str = "", dry_run: bool = False) -> dict:
    target = repo_url or local_path

    if dry_run:
        return {
            "module": "harvest.creds",
            "target": target,
            "dry_run": True,
            "timestamp": timestamp(),
            "description": "Scans git repos for secrets/credentials using trufflehog",
        }

    if repo_url:
        cmd = ["trufflehog", "git", repo_url, "--json", "--no-update"]
    else:
        cmd = ["trufflehog", "filesystem", local_path, "--json", "--no-update"]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

    secrets = []
    for line in result.stdout.splitlines():
        try:
            entry = json.loads(line)
            secrets.append({
                "detector": entry.get("DetectorName", ""),
                "verified": entry.get("Verified", False),
                "raw": entry.get("Raw", "")[:80] + "...",
                "source": entry.get("SourceMetadata", {}).get("Data", {}).get("Git", {}).get("file", ""),
            })
        except json.JSONDecodeError:
            pass

    data = {
        "module": "harvest.creds",
        "target": target,
        "timestamp": timestamp(),
        "secrets_found": secrets,
        "count": len(secrets),
        "verified_count": sum(1 for s in secrets if s.get("verified")),
    }
    save_result("harvest_creds", data)
    return data
