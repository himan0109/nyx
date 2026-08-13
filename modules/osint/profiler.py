import concurrent.futures
import json
from ..utils import save_result, timestamp
from . import username as username_mod
from . import email as email_mod
from . import ip_geo as ip_geo_mod
from . import web_osint as web_osint_mod
from . import domain as domain_mod


def run(target: str, target_type: str = "username") -> dict:
    """
    Aggregate multiple OSINT sources in parallel.
    target_type: 'username' | 'email' | 'ip' | 'domain'
    """
    tasks = {}

    if target_type in ("username", "auto"):
        tasks["username"] = (username_mod.run, target)
        tasks["web"] = (web_osint_mod.run, target)

    if target_type in ("email", "auto"):
        tasks["email"] = (email_mod.run, target)

    if target_type in ("ip", "auto"):
        tasks["ip_geo"] = (ip_geo_mod.run, target)

    if target_type in ("domain", "auto"):
        tasks["domain"] = (domain_mod.run, target)
        tasks["web"] = (web_osint_mod.run, target)

    results = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = {
            executor.submit(fn, arg): name
            for name, (fn, arg) in tasks.items()
        }
        for future in concurrent.futures.as_completed(futures):
            name = futures[future]
            try:
                results[name] = future.result()
            except Exception as e:
                results[name] = {"error": str(e)}

    profile = {
        "module": "osint.profiler",
        "target": target,
        "target_type": target_type,
        "timestamp": timestamp(),
        "sources_queried": list(results.keys()),
        "findings": results,
        "summary": _summarize(results),
    }
    save_result("osint_profile", profile)
    return profile


def _summarize(results: dict) -> dict:
    summary = {}
    if "username" in results:
        r = results["username"]
        summary["social_accounts"] = r.get("accounts_found", 0)
    if "email" in results:
        r = results["email"]
        summary["email_registrations"] = r.get("registered_count", 0)
    if "ip_geo" in results:
        geo = results["ip_geo"].get("geolocation", {})
        summary["location"] = {
            "country": geo.get("country", ""),
            "city": geo.get("city", ""),
            "isp": geo.get("isp", ""),
        }
    if "domain" in results:
        r = results["domain"]
        summary["domain_available"] = r.get("available")
        summary["dns_a_records"] = r.get("dns_records", {}).get("A", [])
    return summary
