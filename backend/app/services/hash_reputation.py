"""Hash reputation lookups: VirusTotal + MalwareBazaar."""
from __future__ import annotations

import logging
from typing import Any

from app.services.http_factory import build_client

logger = logging.getLogger("pyscrapr.threat.rep")

VT_URL = "https://www.virustotal.com/api/v3/files/{}"
MB_URL = "https://mb-api.abuse.ch/api/v1/"


async def virustotal_lookup(sha256: str, api_key: str) -> dict[str, Any]:
    out: dict[str, Any] = {
        "found": False,
        "malicious_count": 0,
        "suspicious_count": 0,
        "harmless_count": 0,
        "total_engines": 0,
        "threat_names": [],
        "reputation_score": 0,
        "scan_date": None,
        "rate_limited": False,
        "error": None,
    }
    if not api_key:
        out["error"] = "api_key kosong"
        return out

    try:
        async with build_client(timeout=10) as client:
            r = await client.get(
                VT_URL.format(sha256),
                headers={"x-apikey": api_key, "Accept": "application/json"},
            )
            if r.status_code == 404:
                return out
            if r.status_code == 429:
                out["rate_limited"] = True
                out["error"] = "rate limited"
                return out
            if r.status_code != 200:
                out["error"] = f"HTTP {r.status_code}"
                return out
            data = r.json()
    except Exception as e:
        out["error"] = f"{type(e).__name__}: {e}"
        return out

    try:
        attrs = (data.get("data", {}) or {}).get("attributes", {}) or {}
        stats = attrs.get("last_analysis_stats", {}) or {}
        out["found"] = True
        out["malicious_count"] = int(stats.get("malicious", 0))
        out["suspicious_count"] = int(stats.get("suspicious", 0))
        out["harmless_count"] = int(stats.get("harmless", 0))
        total = sum(int(v or 0) for v in stats.values())
        out["total_engines"] = total
        out["reputation_score"] = int(attrs.get("reputation", 0) or 0)

        ts = attrs.get("last_analysis_date")
        if ts:
            import datetime as _dt
            try:
                out["scan_date"] = _dt.datetime.fromtimestamp(int(ts), tz=_dt.timezone.utc).isoformat()
            except Exception:
                pass

        # threat names - top unique
        names: set[str] = set()
        results = attrs.get("last_analysis_results", {}) or {}
        for _engine, res in results.items():
            if not isinstance(res, dict):
                continue
            if res.get("category") in ("malicious", "suspicious"):
                n = res.get("result")
                if n:
                    names.add(str(n))
            if len(names) >= 20:
                break
        out["threat_names"] = sorted(names)[:5]
    except Exception as e:
        out["error"] = f"parse: {e}"
    return out


_MB_AUTH_FAIL_STATUSES = {"auth_failed", "illegal_auth", "no_auth"}


async def _mb_request(sha256: str, auth_key: str | None) -> tuple[int, dict[str, Any] | None, str | None]:
    """Single POST to MalwareBazaar. Returns (status_code, json_or_None, error_str_or_None).

    Never raises. If auth_key is provided, sends as `Auth-Key` header.
    """
    headers: dict[str, str] = {}
    if auth_key:
        headers["Auth-Key"] = auth_key
    try:
        async with build_client(timeout=10) as client:
            r = await client.post(
                MB_URL,
                data={"query": "get_info", "hash": sha256},
                headers=headers or None,
            )
            try:
                data = r.json()
            except Exception:
                data = None
            return r.status_code, data, None
    except Exception as e:
        return 0, None, f"{type(e).__name__}: {e}"


async def malwarebazaar_lookup(sha256: str, auth_key: str = "") -> dict[str, Any]:
    """Lookup file hash on MalwareBazaar.

    If `auth_key` is provided and the API rejects it (401/403 or query_status
    in {auth_failed, illegal_auth, no_auth}), silently retry once anonymously.
    Final fallback returns the standard not-found shape with `error` populated
    only if the network itself failed - auth failures are NOT surfaced as
    errors to the user.
    """
    out: dict[str, Any] = {
        "found": False,
        "signature": None,
        "tags": [],
        "first_seen": None,
        "error": None,
        "auth_used": False,
    }

    # Attempt 1: with auth key if provided
    status, data, net_err = await _mb_request(sha256, auth_key or None)
    auth_failed = (
        status in (401, 403)
        or (data is not None and data.get("query_status") in _MB_AUTH_FAIL_STATUSES)
    )

    # Attempt 2: anonymous retry if auth failed (silent fallback)
    if auth_key and auth_failed:
        status, data, net_err = await _mb_request(sha256, None)

    # Network error path (not auth) - return with error populated
    if net_err is not None:
        out["error"] = net_err
        return out
    if status != 200 or data is None:
        # Treat non-200 silently for auth-related codes; populate error only for
        # genuinely weird responses so threat scan can continue without noise.
        if status not in (401, 403):
            out["error"] = f"HTTP {status}"
        return out

    out["auth_used"] = bool(auth_key) and not auth_failed
    try:
        if data.get("query_status") != "ok":
            return out
        rows = data.get("data") or []
        if not rows:
            return out
        first = rows[0]
        out["found"] = True
        out["signature"] = first.get("signature")
        out["tags"] = list(first.get("tags") or [])[:20]
        out["first_seen"] = first.get("first_seen")
    except Exception as e:
        out["error"] = f"parse: {e}"
    return out
