import json
import os
from pathlib import Path
from datetime import datetime
from ..utils import load_config, timestamp

cfg = load_config()
SESSIONS_DIR = Path(cfg["output"]["sessions_dir"])


def run(session: str = "latest") -> dict:
    if session == "latest":
        sessions = sorted(SESSIONS_DIR.glob("*"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not sessions:
            return {"error": "No sessions found"}
        session_dir = sessions[0]
    else:
        session_dir = SESSIONS_DIR / session

    results = {}
    for jfile in session_dir.glob("*.json"):
        try:
            with open(jfile) as f:
                results[jfile.stem] = json.load(f)
        except Exception:
            pass

    md = _build_markdown(session_dir.name, results)
    html = _build_html(session_dir.name, results, md)

    md_path = session_dir / "report.md"
    html_path = session_dir / "report.html"

    with open(md_path, "w") as f:
        f.write(md)
    with open(html_path, "w") as f:
        f.write(html)

    return {
        "module": "report.builder",
        "session": session_dir.name,
        "timestamp": timestamp(),
        "results_compiled": len(results),
        "report_md": str(md_path),
        "report_html": str(html_path),
        "markdown": md,
    }


def _build_markdown(session: str, results: dict) -> str:
    lines = [
        f"# nyx Security Report",
        f"**Session:** {session}  ",
        f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  ",
        f"**Modules run:** {len(results)}",
        "",
        "---",
        "",
    ]

    osint = {k: v for k, v in results.items() if k.startswith("osint")}
    phishing = {k: v for k, v in results.items() if k.startswith("phishing")}
    network = {k: v for k, v in results.items() if k.startswith("network")}
    exploit = {k: v for k, v in results.items() if k.startswith("exploit")}
    harvest = {k: v for k, v in results.items() if k.startswith("harvest")}

    if osint:
        lines += ["## OSINT Findings", ""]
        for k, v in osint.items():
            target = v.get("target", v.get("file", ""))
            lines.append(f"### {k.replace('_', ' ').title()}")
            if "accounts" in v:
                lines.append(f"- Social accounts found: **{v.get('accounts_found', 0)}**")
                for acc in v.get("accounts", [])[:10]:
                    lines.append(f"  - {acc}")
            if "registered_on" in v:
                lines.append(f"- Registered sites: **{v.get('registered_count', 0)}**")
                for site in v.get("registered_on", []):
                    lines.append(f"  - {site}")
            if "geolocation" in v:
                geo = v["geolocation"]
                lines.append(f"- Location: {geo.get('country', '')} / {geo.get('city', '')}")
                lines.append(f"- ISP: {geo.get('isp', '')}")
            if "summary" in v:
                lines.append(f"- Summary: {json.dumps(v['summary'], indent=2)}")
            lines.append("")

    if network:
        lines += ["## Network Findings", ""]
        for k, v in network.items():
            lines.append(f"### {k.replace('_', ' ').title()}")
            if "open_ports" in v:
                lines.append(f"- Open ports: **{v.get('open_count', 0)}**")
                for p in v.get("open_ports", []):
                    lines.append(f"  - {p['port']}/{p['protocol']} — {p['service']}")
            if "credentials_found" in v:
                for cred in v.get("credentials_found", []):
                    lines.append(f"- **CREDENTIAL:** {cred}")
            if "vulnerable" in v:
                lines.append(f"- SQL Injectable: **{v.get('vulnerable')}**")
            if "paths_found" in v:
                lines.append(f"- Paths found: **{v.get('count', 0)}**")
                for p in v.get("paths_found", [])[:10]:
                    lines.append(f"  - {p['path']} [{p['status']}]")
            lines.append("")

    if phishing:
        lines += ["## Phishing Campaigns", ""]
        for k, v in phishing.items():
            lines.append(f"### {k.replace('_', ' ').title()}")
            if v.get("public_url"):
                lines.append(f"- Public URL: {v['public_url']}")
            if v.get("template"):
                lines.append(f"- Template: {v['template']}")
            lines.append("")

    if harvest:
        lines += ["## Credential Harvest", ""]
        for k, v in harvest.items():
            lines.append(f"### {k.replace('_', ' ').title()}")
            lines.append(f"- Items found: **{v.get('count', 0)}**")
            if v.get("verified_count"):
                lines.append(f"- Verified: **{v['verified_count']}**")
            lines.append("")

    if exploit:
        lines += ["## Exploit Activity", ""]
        for k, v in exploit.items():
            lines.append(f"### {k.replace('_', ' ').title()}")
            lines.append(f"- Module: {v.get('module', k)}")
            lines.append("")

    lines += ["---", f"*Generated by nyx — {datetime.now().isoformat()}*"]
    return "\n".join(lines)


def _build_html(session: str, results: dict, md: str) -> str:
    try:
        import markdown
        body = markdown.markdown(md, extensions=["tables", "fenced_code"])
    except ImportError:
        body = f"<pre>{md}</pre>"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>nyx Report — {session}</title>
<style>
body{{font-family:monospace;background:#0d0d0d;color:#c0c0c0;max-width:900px;margin:40px auto;padding:20px;}}
h1{{color:#8b00ff;}} h2{{color:#6600cc;border-bottom:1px solid #333;padding-bottom:4px;}}
h3{{color:#9933ff;}} strong{{color:#ffffff;}}
code{{background:#1a1a1a;padding:2px 6px;border-radius:3px;color:#00ff88;}}
pre{{background:#1a1a1a;padding:16px;border-radius:6px;overflow-x:auto;}}
a{{color:#8b00ff;}}
</style>
</head>
<body>
{body}
</body>
</html>"""
