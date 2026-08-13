import json
import requests
from ..utils import load_config

cfg = load_config()
_notify = cfg.get("notify", {})


def send(data: dict, title: str = "nyx result") -> dict:
    results = {"telegram": False, "discord": False}

    token = _notify.get("telegram_token", "")
    chat_id = _notify.get("telegram_chat_id", "")
    webhook = _notify.get("discord_webhook", "")

    message = _format_message(title, data)

    if token and chat_id:
        results["telegram"] = _send_telegram(token, chat_id, message)

    if webhook:
        results["discord"] = _send_discord(webhook, title, message)

    return results


def _format_message(title: str, data: dict) -> str:
    lines = [f"*nyx | {title}*", ""]
    module = data.get("module", "")
    target = data.get("target", data.get("file", ""))
    ts = data.get("timestamp", "")

    if module:
        lines.append(f"Module: `{module}`")
    if target:
        lines.append(f"Target: `{target}`")
    if ts:
        lines.append(f"Time: {ts}")

    lines.append("")

    for key, val in data.items():
        if key in ("module", "target", "timestamp", "raw", "raw_stderr"):
            continue
        if isinstance(val, list) and val:
            lines.append(f"*{key}* ({len(val)}):")
            for item in val[:5]:
                lines.append(f"  • {item}")
            if len(val) > 5:
                lines.append(f"  ... +{len(val) - 5} more")
        elif isinstance(val, dict):
            lines.append(f"*{key}*: {json.dumps(val, indent=2)[:200]}")
        elif val:
            lines.append(f"*{key}*: {val}")

    return "\n".join(lines)


def _send_telegram(token: str, chat_id: str, message: str) -> bool:
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        resp = requests.post(url, json={
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "Markdown",
        }, timeout=10)
        return resp.status_code == 200
    except Exception:
        return False


def _send_discord(webhook: str, title: str, message: str) -> bool:
    try:
        resp = requests.post(webhook, json={
            "embeds": [{
                "title": f"nyx | {title}",
                "description": message[:2000],
                "color": 0x8b00ff,
            }]
        }, timeout=10)
        return resp.status_code in (200, 204)
    except Exception:
        return False
