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

# DKIM selectors yang umum digunakan oleh provider populer
DKIM_SELECTORS = ["default", "google", "selector1", "selector2", "k1", "mandrill", "dkim", "mail"]


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


# --------------------------------------------------------------------- Email Security (SPF / DMARC / DKIM)


def _strip_txt_quotes(value: str) -> str:
    """dnspython renders TXT entries as quoted, possibly multi-string. Join + unquote."""
    parts = re.findall(r'"((?:[^"\\]|\\.)*)"', value)
    if parts:
        return "".join(parts)
    return value.strip().strip('"')


def _parse_spf(txt_records: list[str]) -> dict[str, Any]:
    spf_record: str | None = None
    for raw in txt_records:
        cleaned = _strip_txt_quotes(raw)
        if cleaned.lower().startswith("v=spf1"):
            spf_record = cleaned
            break

    if not spf_record:
        return {
            "found": False,
            "raw": None,
            "policy": "unknown",
            "all_directive": None,
            "includes": [],
            "mechanisms": [],
            "warnings": ["Record SPF tidak ditemukan"],
        }

    tokens = spf_record.split()
    mechanisms = tokens[1:]
    includes: list[str] = []
    all_directive: str | None = None
    for tok in mechanisms:
        low = tok.lower()
        if low.startswith("include:"):
            includes.append(tok.split(":", 1)[1])
        elif low in ("+all", "all"):
            all_directive = "+all"
        elif low in ("?all", "~all", "-all"):
            all_directive = low

    policy_map = {"+all": "pass", "?all": "neutral", "~all": "soft_fail", "-all": "fail"}
    policy = policy_map.get(all_directive or "", "unknown")

    warnings: list[str] = []
    if all_directive == "+all":
        warnings.append("Kebijakan +all meloloskan semua pengirim - rawan spoofing")
    if all_directive == "?all":
        warnings.append("Kebijakan ?all bersifat netral, tidak melindungi domain")
    if all_directive is None:
        warnings.append("Tidak ada direktif all - kebijakan SPF tidak jelas")
    if len(includes) > 10:
        warnings.append("Terlalu banyak include (>10), risiko melebihi 10 lookup DNS SPF")

    return {
        "found": True,
        "raw": spf_record,
        "policy": policy,
        "all_directive": all_directive,
        "includes": includes,
        "mechanisms": mechanisms,
        "warnings": warnings,
    }


def _parse_dmarc(txt_records: list[str]) -> dict[str, Any]:
    dmarc_record: str | None = None
    for raw in txt_records:
        cleaned = _strip_txt_quotes(raw)
        if cleaned.lower().startswith("v=dmarc1"):
            dmarc_record = cleaned
            break

    if not dmarc_record:
        return {
            "found": False,
            "raw": None,
            "policy": None,
            "subdomain_policy": None,
            "pct": None,
            "rua": [],
            "ruf": [],
            "warnings": ["Record DMARC tidak ditemukan di _dmarc subdomain"],
        }

    tags: dict[str, str] = {}
    for part in dmarc_record.split(";"):
        if "=" in part:
            k, v = part.split("=", 1)
            tags[k.strip().lower()] = v.strip()

    policy = tags.get("p")
    sp = tags.get("sp") or policy
    pct_raw = tags.get("pct")
    try:
        pct = int(pct_raw) if pct_raw else 100
    except ValueError:
        pct = None
    rua = [u.strip() for u in (tags.get("rua") or "").split(",") if u.strip()]
    ruf = [u.strip() for u in (tags.get("ruf") or "").split(",") if u.strip()]

    warnings: list[str] = []
    if policy == "none":
        warnings.append("Kebijakan p=none hanya monitor, tidak menolak email palsu")
    if policy not in ("none", "quarantine", "reject"):
        warnings.append("Nilai p tidak valid")
    if pct is not None and pct < 100:
        warnings.append(f"Hanya {pct}% email yang diberlakukan kebijakan DMARC")
    if not rua:
        warnings.append("Tidak ada alamat rua untuk laporan agregat")

    return {
        "found": True,
        "raw": dmarc_record,
        "policy": policy if policy in ("none", "quarantine", "reject") else None,
        "subdomain_policy": sp if sp in ("none", "quarantine", "reject") else None,
        "pct": pct,
        "rua": rua,
        "ruf": ruf,
        "warnings": warnings,
    }


def _dkim_lookup_sync(domain: str, selectors: list[str]) -> list[str]:
    try:
        import dns.resolver  # type: ignore
        import dns.exception  # type: ignore
    except ImportError:
        return []
    resolver = dns.resolver.Resolver()
    resolver.timeout = 3.0
    resolver.lifetime = 5.0
    found: list[str] = []
    for sel in selectors:
        name = f"{sel}._domainkey.{domain}"
        try:
            answers = resolver.resolve(name, "TXT", raise_on_no_answer=False)
            for r in answers:
                txt = _strip_txt_quotes(r.to_text())
                if "v=DKIM1" in txt or "k=" in txt or "p=" in txt:
                    found.append(sel)
                    break
        except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer):
            continue
        except dns.exception.DNSException as e:
            logger.debug("DKIM lookup %s error: %s", name, e)
        except Exception as e:
            logger.debug("DKIM lookup %s unexpected: %s", name, e)
    return found


def _dmarc_txt_sync(domain: str) -> list[str]:
    try:
        import dns.resolver  # type: ignore
        import dns.exception  # type: ignore
    except ImportError:
        return []
    resolver = dns.resolver.Resolver()
    resolver.timeout = 5.0
    resolver.lifetime = 10.0
    out: list[str] = []
    try:
        answers = resolver.resolve(f"_dmarc.{domain}", "TXT", raise_on_no_answer=False)
        for r in answers:
            try:
                out.append(r.to_text())
            except Exception:
                out.append(str(r))
    except dns.resolver.NXDOMAIN:
        pass
    except dns.resolver.NoAnswer:
        pass
    except dns.exception.DNSException as e:
        logger.debug("DMARC DNS error: %s", e)
    except Exception as e:
        logger.debug("DMARC DNS unexpected: %s", e)
    return out


def _grade_email_security(spf: dict, dmarc: dict, dkim_found: list[str]) -> str:
    spf_found = spf.get("found")
    spf_all = spf.get("all_directive")
    dmarc_found = dmarc.get("found")
    dmarc_policy = dmarc.get("policy")
    has_dkim = bool(dkim_found)

    # F: nothing or wide-open SPF
    if not spf_found and not dmarc_found:
        return "F"
    if spf_all == "+all":
        return "F"
    # A: SPF -all + DMARC reject + DKIM
    if spf_found and spf_all == "-all" and dmarc_policy == "reject" and has_dkim:
        return "A"
    # B: SPF ~all/-all + DMARC quarantine/reject
    if spf_found and spf_all in ("~all", "-all") and dmarc_policy in ("quarantine", "reject"):
        return "B"
    # C: SPF + DMARC none
    if spf_found and dmarc_policy == "none":
        return "C"
    # D: SPF, no DMARC
    if spf_found and not dmarc_found:
        return "D"
    return "F"


async def email_security(domain: str, dns_data: dict[str, list[str]]) -> dict[str, Any]:
    """Build SPF/DMARC/DKIM email security record. Defensive against DNS failures."""
    dom = _normalize_domain(domain)
    if not dom:
        return {
            "spf": {"found": False, "raw": None, "policy": "unknown", "all_directive": None,
                    "includes": [], "mechanisms": [], "warnings": ["Domain tidak valid"]},
            "dmarc": {"found": False, "raw": None, "policy": None, "subdomain_policy": None,
                      "pct": None, "rua": [], "ruf": [], "warnings": []},
            "dkim": {"selectors_checked": [], "selectors_found": []},
            "grade": "F",
        }

    txt_records = dns_data.get("TXT", []) if isinstance(dns_data, dict) else []
    spf = _parse_spf(txt_records)

    try:
        dmarc_txt = await asyncio.to_thread(_dmarc_txt_sync, dom)
    except Exception as e:
        logger.warning("DMARC lookup failed for %s: %s", dom, e)
        dmarc_txt = []
    dmarc = _parse_dmarc(dmarc_txt)

    try:
        dkim_found = await asyncio.to_thread(_dkim_lookup_sync, dom, DKIM_SELECTORS)
    except Exception as e:
        logger.warning("DKIM lookup failed for %s: %s", dom, e)
        dkim_found = []

    grade = _grade_email_security(spf, dmarc, dkim_found)

    return {
        "spf": spf,
        "dmarc": dmarc,
        "dkim": {
            "selectors_checked": list(DKIM_SELECTORS),
            "selectors_found": dkim_found,
        },
        "grade": grade,
    }


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

    try:
        email_sec = await email_security(dom, dns_data)
    except Exception as e:
        logger.warning("email_security analysis failed for %s: %s", dom, e)
        email_sec = None

    return {
        "domain": dom,
        "whois": whois_data,
        "dns": dns_data,
        "subdomains": subs_data,
        "subdomain_count": len(subs_data),
        "email_security": email_sec,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }
