"""Domain intelligence: WHOIS (RDAP), DNS records, subdomain enumeration (crt.sh).

Combined module because all three pivot on a single domain name and are
commonly consumed together in one report.
"""
from __future__ import annotations

import asyncio
import logging
import re
from datetime import datetime, timezone
from typing import Any, Optional
from urllib.parse import urlparse

import httpx

from app.services.http_factory import build_client

logger = logging.getLogger("pyscrapr.domain_intel")

DEFAULT_RECORD_TYPES = ["A", "AAAA", "MX", "TXT", "NS", "CAA", "SOA"]


def _normalize_domain(raw: str) -> str:
    """Accept URL or bare domain, return bare lowercase domain (no path, no port)."""
    raw = (raw or "").strip()
    if not raw:
        return ""
    if "://" in raw:
        host = urlparse(raw).hostname or ""
    else:
        host = raw.split("/", 1)[0]
    host = host.split(":", 1)[0].lower()
    return host.removeprefix("www.")


# --------------------------------------------------------------------- WHOIS

async def whois_lookup(domain: str) -> dict[str, Any]:
    """RDAP lookup via rdap.org (which bootstraps to the correct RDAP server).

    Returns a normalized dict. On 404 returns {registered: False}.
    """
    dom = _normalize_domain(domain)
    if not dom:
        return {"registered": False, "error": "empty domain"}

    url = f"https://rdap.org/domain/{dom}"
    async with build_client(timeout=20) as client:
        try:
            resp = await client.get(url, headers={"Accept": "application/rdap+json"})
        except httpx.HTTPError as e:
            logger.warning("RDAP request failed for %s: %s", dom, e)
            return {"registered": None, "error": f"rdap fetch failed: {e}"}

    if resp.status_code == 404:
        return {"registered": False, "domain": dom}
    if resp.status_code >= 400:
        return {
            "registered": None,
            "domain": dom,
            "error": f"rdap status {resp.status_code}",
        }

    try:
        data = resp.json()
    except Exception as e:
        return {"registered": None, "domain": dom, "error": f"bad json: {e}"}

    # Extract events
    events = {ev.get("eventAction"): ev.get("eventDate") for ev in data.get("events", []) or []}
    registration = events.get("registration")
    expiration = events.get("expiration")
    last_changed = events.get("last changed") or events.get("last update of RDAP database")

    # Registrar
    registrar = None
    for ent in data.get("entities", []) or []:
        roles = ent.get("roles") or []
        if "registrar" in roles:
            vcard = ent.get("vcardArray")
            if isinstance(vcard, list) and len(vcard) > 1:
                for item in vcard[1]:
                    if isinstance(item, list) and len(item) >= 4 and item[0] == "fn":
                        registrar = item[3]
                        break
            if not registrar:
                registrar = ent.get("handle")
            break

    # Registrant country (best-effort, often redacted)
    registrant_country = None
    for ent in data.get("entities", []) or []:
        roles = ent.get("roles") or []
        if "registrant" in roles:
            vcard = ent.get("vcardArray")
            if isinstance(vcard, list) and len(vcard) > 1:
                for item in vcard[1]:
                    if isinstance(item, list) and len(item) >= 4 and item[0] == "adr":
                        adr = item[3]
                        if isinstance(adr, list) and len(adr) >= 7:
                            registrant_country = adr[6] or None
                        break
            break

    # Name servers
    nameservers = []
    for ns in data.get("nameservers", []) or []:
        name = ns.get("ldhName") or ns.get("unicodeName")
        if name:
            nameservers.append(name.lower())

    # Status
    status = data.get("status") or []

    return {
        "registered": True,
        "domain": dom,
        "registrar": registrar,
        "registration_date": registration,
        "expiration_date": expiration,
        "last_updated": last_changed,
        "nameservers": sorted(set(nameservers)),
        "status": status,
        "registrant_country": registrant_country,
    }


# --------------------------------------------------------------------- DNS

def _dns_records_sync(domain: str, record_types: list[str]) -> dict[str, list[str]]:
    try:
        import dns.resolver  # type: ignore
        import dns.exception  # type: ignore
    except ImportError:
        return {"_error": ["dnspython not installed. Run: pip install dnspython"]}

    resolver = dns.resolver.Resolver()
    resolver.timeout = 5.0
    resolver.lifetime = 10.0

    out: dict[str, list[str]] = {}
    for rtype in record_types:
        try:
            answers = resolver.resolve(domain, rtype, raise_on_no_answer=False)
            values: list[str] = []
            for r in answers:
                try:
                    values.append(r.to_text())
                except Exception:
                    values.append(str(r))
            out[rtype] = values
        except dns.resolver.NXDOMAIN:
            out[rtype] = []
            out["_nxdomain"] = ["NXDOMAIN"]
            break
        except dns.resolver.NoAnswer:
            out[rtype] = []
        except dns.exception.DNSException as e:
            out[rtype] = []
            logger.debug("DNS %s %s error: %s", rtype, domain, e)
        except Exception as e:
            out[rtype] = []
            logger.debug("DNS %s %s unexpected error: %s", rtype, domain, e)
    return out


async def dns_records(
    domain: str,
    record_types: Optional[list[str]] = None,
) -> dict[str, list[str]]:
    dom = _normalize_domain(domain)
    if not dom:
        return {}
    types = record_types or DEFAULT_RECORD_TYPES
    return await asyncio.to_thread(_dns_records_sync, dom, types)


# --------------------------------------------------------------------- Subdomains

_WILDCARD_RE = re.compile(r"^\*\.", re.IGNORECASE)


async def subdomains_via_crtsh(domain: str) -> list[str]:
    """Query crt.sh Certificate Transparency database for subdomains."""
    dom = _normalize_domain(domain)
    if not dom:
        return []

    url = f"https://crt.sh/?q=%.{dom}&output=json"
    headers = {
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0 (PyScrapr Intel) DomainIntel/1.0",
    }
    async with build_client(timeout=30) as client:
        try:
            resp = await client.get(url, headers=headers)
            if resp.status_code != 200:
                logger.warning("crt.sh returned status %s for %s", resp.status_code, dom)
                return []
            data = resp.json()
        except httpx.HTTPError as e:
            logger.warning("crt.sh fetch failed for %s: %s", dom, e)
            return []
        except Exception as e:
            logger.warning("crt.sh parse failed for %s: %s", dom, e)
            return []

    subs: set[str] = set()
    suffix = f".{dom}"
    for entry in data if isinstance(data, list) else []:
        name_value = entry.get("name_value") or ""
        for line in name_value.splitlines():
            line = line.strip().lower()
            if not line:
                continue
            line = _WILDCARD_RE.sub("", line)
            if line == dom or line.endswith(suffix):
                subs.add(line)
    return sorted(subs)


# --------------------------------------------------------------------- Main entry

async def analyze(domain: str) -> dict[str, Any]:
    dom = _normalize_domain(domain)
    if not dom:
        raise ValueError("empty or invalid domain")

    whois_task = asyncio.create_task(whois_lookup(dom))
    dns_task = asyncio.create_task(dns_records(dom))
    subs_task = asyncio.create_task(subdomains_via_crtsh(dom))

    whois_res, dns_res, subs_res = await asyncio.gather(
        whois_task, dns_task, subs_task, return_exceptions=True
    )

    def _unwrap(r, fallback):
        if isinstance(r, Exception):
            logger.warning("intel sub-task failed: %s", r)
            return fallback
        return r

    whois_data = _unwrap(whois_res, {"registered": None, "error": "lookup failed"})
    dns_data = _unwrap(dns_res, {})
    subs_data = _unwrap(subs_res, [])

    return {
        "domain": dom,
        "whois": whois_data,
        "dns": dns_data,
        "subdomains": subs_data,
        "subdomain_count": len(subs_data),
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }
