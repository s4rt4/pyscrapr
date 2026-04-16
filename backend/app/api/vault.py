"""Auth Vault + Proxy + CAPTCHA management endpoints."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.auth_vault import (
    delete_profile,
    import_browser_cookies,
    list_profiles,
    upsert_profile,
)
from app.services.captcha_solver import CaptchaSolver
from app.services.settings_store import get as get_setting

router = APIRouter()


# ─── Auth Vault ───

class VaultProfileRequest(BaseModel):
    domain: str
    cookies: dict = Field(default_factory=dict)
    headers: dict = Field(default_factory=dict)
    notes: str = ""


class ImportCookiesRequest(BaseModel):
    browser: str  # chrome, firefox, edge, brave
    domain_filter: str = ""


@router.get("/profiles")
async def list_vault_profiles():
    return list_profiles()


@router.put("/profiles")
async def upsert_vault_profile(req: VaultProfileRequest):
    return upsert_profile(req.domain, req.cookies, req.headers, req.notes)


@router.delete("/profiles/{domain}")
async def delete_vault_profile(domain: str):
    if not delete_profile(domain):
        raise HTTPException(404, "Profile not found")
    return {"ok": True}


@router.post("/import-cookies")
async def import_cookies(req: ImportCookiesRequest):
    try:
        counts = import_browser_cookies(req.browser, req.domain_filter)
        total = sum(counts.values())
        return {"total_cookies": total, "domains": len(counts), "per_domain": counts}
    except Exception as e:
        raise HTTPException(400, str(e))


# ─── CAPTCHA ───

@router.get("/captcha/balance")
async def captcha_balance():
    provider = get_setting("captcha_provider", "")
    api_key = get_setting("captcha_api_key", "")
    if not provider or not api_key:
        return {"enabled": False, "balance": None}
    solver = CaptchaSolver(provider=provider, api_key=api_key)
    balance = await solver.get_balance()
    return {"enabled": True, "provider": provider, "balance": balance}
