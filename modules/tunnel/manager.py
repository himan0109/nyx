import subprocess
import time
import requests
import json
from ..utils import load_config

cfg = load_config()
_tunnel_proc = None
_public_url = None


def start(port: int = None) -> str:
    global _tunnel_proc, _public_url

    port = port or cfg.get("tunnel", {}).get("port", 8080)
    provider = cfg.get("tunnel", {}).get("provider", "ngrok")
    auth = cfg.get("tunnel", {}).get("auth_token", "")

    if _tunnel_proc and _tunnel_proc.poll() is None:
        return _public_url or ""

    if provider == "ngrok":
        cmd = ["ngrok", "http", str(port)]
        if auth:
            subprocess.run(["ngrok", "config", "add-authtoken", auth], capture_output=True)
    else:
        cmd = ["cloudflared", "tunnel", "--url", f"http://localhost:{port}"]

    _tunnel_proc = subprocess.Popen(
        cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    time.sleep(3)

    _public_url = _fetch_ngrok_url() if provider == "ngrok" else _fetch_cloudflared_url()
    return _public_url or ""


def stop():
    global _tunnel_proc, _public_url
    if _tunnel_proc:
        _tunnel_proc.terminate()
        _tunnel_proc = None
    _public_url = None


def get_public_url(port: int = None) -> str:
    global _public_url
    if _public_url:
        return _public_url
    return start(port)


def _fetch_ngrok_url() -> str:
    try:
        resp = requests.get("http://localhost:4040/api/tunnels", timeout=5)
        tunnels = resp.json().get("tunnels", [])
        for t in tunnels:
            if t.get("proto") == "https":
                return t["public_url"]
        if tunnels:
            return tunnels[0]["public_url"]
    except Exception:
        pass
    return ""


def _fetch_cloudflared_url() -> str:
    try:
        if _tunnel_proc:
            for _ in range(10):
                time.sleep(1)
        return ""
    except Exception:
        return ""
