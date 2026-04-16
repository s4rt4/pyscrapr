"""Auth & Session Vault — per-domain storage of cookies, headers, tokens.

Persists to data/auth_vault.json. Used by orchestrators to inject auth
into httpx requests when scraping login-protected pages.
"""
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from app.config import settings

_VAULT_FILE = settings.data_dir / "auth_vault.json"


def _load() -> dict[str, dict]:
    if _VAULT_FILE.exists():
        try:
            return json.loads(_VAULT_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _save(data: dict[str, dict]) -> None:
    _VAULT_FILE.parent.mkdir(parents=True, exist_ok=True)
    _VAULT_FILE.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")


def list_profiles() -> list[dict]:
    vault = _load()
    return [{"domain": k, **v} for k, v in sorted(vault.items())]


def get_profile(domain: str) -> Optional[dict]:
    vault = _load()
    return vault.get(domain)


def upsert_profile(domain: str, cookies: dict = None, headers: dict = None, notes: str = "") -> dict:
    vault = _load()
    existing = vault.get(domain, {})
    profile = {
        "cookies": cookies if cookies is not None else existing.get("cookies", {}),
        "headers": headers if headers is not None else existing.get("headers", {}),
        "notes": notes or existing.get("notes", ""),
        "updated_at": datetime.utcnow().isoformat(),
        "created_at": existing.get("created_at", datetime.utcnow().isoformat()),
    }
    vault[domain] = profile
    _save(vault)
    return {"domain": domain, **profile}


def delete_profile(domain: str) -> bool:
    vault = _load()
    if domain in vault:
        del vault[domain]
        _save(vault)
        return True
    return False


def get_httpx_args(url: str) -> dict[str, Any]:
    """Return cookies + headers dict for a URL's domain, ready for httpx."""
    from urllib.parse import urlparse
    host = urlparse(url).netloc.lower().replace("www.", "")
    vault = _load()

    # Check exact match first, then parent domain
    profile = vault.get(host)
    if not profile:
        for domain, prof in vault.items():
            if host.endswith(domain) or domain.endswith(host):
                profile = prof
                break

    if not profile:
        return {}

    result: dict[str, Any] = {}
    if profile.get("cookies"):
        result["cookies"] = profile["cookies"]
    if profile.get("headers"):
        result["headers"] = profile["headers"]
    return result


def import_browser_cookies(browser: str, domain_filter: str = "") -> dict[str, int]:
    """Import cookies from a browser, optionally filtered by domain. Returns count per domain."""
    import browser_cookie3

    loaders = {
        "chrome": browser_cookie3.chrome,
        "firefox": browser_cookie3.firefox,
        "edge": browser_cookie3.edge,
        "brave": browser_cookie3.brave,
    }
    loader = loaders.get(browser)
    if not loader:
        raise ValueError(f"Unknown browser: {browser}")

    try:
        cj = loader(domain_name=domain_filter or "")
    except Exception as e:
        raise RuntimeError(f"Failed to read {browser} cookies: {e}")

    vault = _load()
    counts: dict[str, int] = {}
    for cookie in cj:
        domain = cookie.domain.lstrip(".")
        if not domain:
            continue
        profile = vault.setdefault(domain, {
            "cookies": {},
            "headers": {},
            "notes": f"Imported from {browser}",
            "created_at": datetime.utcnow().isoformat(),
        })
        profile["cookies"][cookie.name] = cookie.value
        profile["updated_at"] = datetime.utcnow().isoformat()
        counts[domain] = counts.get(domain, 0) + 1

    _save(vault)
    return counts
