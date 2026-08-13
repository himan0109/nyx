import subprocess
from ..utils import save_result, timestamp


def run(target: str, forms: bool = True, dump_dbs: bool = False,
        dump_tables: bool = False, dry_run: bool = False) -> dict:
    if dry_run:
        return {
            "module": "network.sqlinject",
            "target": target,
            "dry_run": True,
            "timestamp": timestamp(),
            "status": "dry_run_ok",
        }

    cmd = ["sqlmap", "-u", target, "--batch", "--random-agent", "--level=3", "--risk=2"]
    if forms:
        cmd.append("--forms")
    if dump_dbs:
        cmd.append("--dbs")
    if dump_tables:
        cmd.append("--tables")

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)

    vulnerable = "is vulnerable" in result.stdout.lower() or "Parameter:" in result.stdout
    dbs = []
    tables = []

    for line in result.stdout.splitlines():
        if "[*]" in line and not line.strip().startswith("#"):
            item = line.split("[*]")[-1].strip()
            if dump_dbs:
                dbs.append(item)
            elif dump_tables:
                tables.append(item)

    data = {
        "module": "network.sqlinject",
        "target": target,
        "timestamp": timestamp(),
        "vulnerable": vulnerable,
        "databases": dbs,
        "tables": tables,
        "raw": result.stdout[:3000],
    }
    save_result("network_sqli", data)
    return data
