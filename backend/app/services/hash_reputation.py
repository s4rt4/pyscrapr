"""Hash reputation lookups: VirusTotal + MalwareBazaar.

Both lookups are wrapped with a SQLite-backed cache keyed on
(sha256, source). Positive hits are cached forever; negative hits
expire after 7 days so a sample that later appears in feeds will
be re-checked.
"""
from __future__ import annotations

import logging
from typing import Any

from app.repositories.hash_reputation_cache_repository import HashRepCacheRepo
from app.services.http_factory import build_client

logger = logging.getLogger("pyscrapr.hash_reputation")

VT_URL = "https://www.virustotal.com/api/v3/files/{}"
MB_URL = "https://mb-api.abuse.ch/api/v1/"


async def virustotal_lookup(sha256: str, api_key: str) -> dict[str, Any]:
    # Cache check - skip API call entirely on hit
    if sha256:
        try:
            cached = await HashRepCacheRepo().get(sha256, "vt")
            if cached is not None:
                return {**cached, "cached": True}
        except Exception as e:
            logger.debug("vt cache lookup gagal: %s", e)

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

    data: Any = None
    try:
        async with build_client(timeout=10) as client:
            r = await client.get(
                VT_URL.format(sha256),
                headers={"x-apikey": api_key, "Accept": "application/json"},
            )
            if r.status_code == 404:
                # Negative result - cache it (TTL'd)
                if sha256:
                    try:
                        await HashRepCacheRepo().save(sha256, "vt", out, False)
                    except Exception as e:
                        logger.debug("vt cache save (404) gagal: %s", e)
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

    # Cache result (only if no transient/network error and not rate-limited)
    if sha256 and not out.get("rate_limited") and not out.get("error"):
        found = bool(out.get("malicious_count", 0)) or bool(out.get("suspicious_count", 0))
        # Also cache "found but clean" (file is known to VT) as a positive cache
        # so we never re-query. Use out["found"] OR detection counts.
        cache_positive = bool(out.get("found")) and (found or int(out.get("total_engines", 0)) > 0)
        try:
            await HashRepCacheRepo().save(sha256, "vt", out, cache_positive)
        except Exception as e:
            logger.debug("vt cache save gagal: %s", e)
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
    # Cache check first
    if sha256:
        try:
            cached = await HashRepCacheRepo().get(sha256, "mb")
            if cached is not None:
                return {**cached, "cached": True}
        except Exception as e:
            logger.debug("mb cache lookup gagal: %s", e)

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
            # Negative: query_status="hash_not_found" or similar
            if sha256 and not out.get("error"):
                try:
                    await HashRepCacheRepo().save(sha256, "mb", out, False)
                except Exception as e:
                    logger.debug("mb cache save (not-ok) gagal: %s", e)
            return out
        rows = data.get("data") or []
        if not rows:
            if sha256:
                try:
                    await HashRepCacheRepo().save(sha256, "mb", out, False)
                except Exception as e:
                    logger.debug("mb cache save (empty) gagal: %s", e)
            return out
        first = rows[0]
        out["found"] = True
        out["signature"] = first.get("signature")
        out["tags"] = list(first.get("tags") or [])[:20]
        out["first_seen"] = first.get("first_seen")
    except Exception as e:
        out["error"] = f"parse: {e}"

    # Cache final result
    if sha256 and not out.get("error"):
        try:
            await HashRepCacheRepo().save(sha256, "mb", out, bool(out.get("found")))
        except Exception as e:
            logger.debug("mb cache save gagal: %s", e)
    return out
