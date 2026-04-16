"""CAPTCHA solver integration — supports 2Captcha and Anti-Captcha.

Detects CAPTCHA presence in HTML, submits to solver service, returns solution.
Used as middleware in orchestrators: if response contains CAPTCHA, solve + retry.
"""
import asyncio
import re
import time
from typing import Optional

import httpx

# Detection patterns for common CAPTCHAs
_RECAPTCHA_RE = re.compile(r'(?:data-sitekey|g-recaptcha|grecaptcha)["\s=]+(["\']?)([0-9a-zA-Z_-]{20,})', re.IGNORECASE)
_HCAPTCHA_RE = re.compile(r'(?:data-sitekey|h-captcha)["\s=]+(["\']?)([0-9a-f-]{36,})', re.IGNORECASE)
_CLOUDFLARE_RE = re.compile(r'(?:cf-challenge|cf_clearance|challenge-platform|Just a moment)', re.IGNORECASE)


def detect_captcha(html: str) -> Optional[dict]:
    """Detect if HTML contains a CAPTCHA challenge.

    Returns: {"type": "recaptcha"|"hcaptcha"|"cloudflare", "sitekey": "..."} or None
    """
    m = _RECAPTCHA_RE.search(html)
    if m:
        return {"type": "recaptcha", "sitekey": m.group(2)}
    m = _HCAPTCHA_RE.search(html)
    if m:
        return {"type": "hcaptcha", "sitekey": m.group(2)}
    if _CLOUDFLARE_RE.search(html):
        return {"type": "cloudflare", "sitekey": None}
    return None


class CaptchaSolver:
    """Abstract solver that delegates to 2Captcha or Anti-Captcha."""

    def __init__(self, provider: str = "2captcha", api_key: str = ""):
        self.provider = provider
        self.api_key = api_key
        self.enabled = bool(api_key)

    async def solve_recaptcha(self, sitekey: str, page_url: str) -> Optional[str]:
        """Submit reCAPTCHA v2 and return g-recaptcha-response token."""
        if not self.enabled:
            return None
        if self.provider == "2captcha":
            return await self._solve_2captcha(sitekey, page_url, "userrecaptcha")
        elif self.provider == "anticaptcha":
            return await self._solve_anticaptcha(sitekey, page_url, "RecaptchaV2TaskProxyless")
        return None

    async def solve_hcaptcha(self, sitekey: str, page_url: str) -> Optional[str]:
        if not self.enabled:
            return None
        if self.provider == "2captcha":
            return await self._solve_2captcha(sitekey, page_url, "hcaptcha")
        elif self.provider == "anticaptcha":
            return await self._solve_anticaptcha(sitekey, page_url, "HCaptchaTaskProxyless")
        return None

    async def get_balance(self) -> Optional[float]:
        if not self.enabled:
            return None
        try:
            if self.provider == "2captcha":
                async with httpx.AsyncClient(timeout=10) as c:
                    r = await c.get(f"https://2captcha.com/res.php?key={self.api_key}&action=getbalance&json=1")
                    d = r.json()
                    return float(d.get("request", 0))
            elif self.provider == "anticaptcha":
                async with httpx.AsyncClient(timeout=10) as c:
                    r = await c.post("https://api.anti-captcha.com/getBalance", json={"clientKey": self.api_key})
                    d = r.json()
                    return d.get("balance")
        except Exception:
            return None

    # ─── 2Captcha implementation ───

    async def _solve_2captcha(self, sitekey: str, page_url: str, method: str) -> Optional[str]:
        async with httpx.AsyncClient(timeout=30) as client:
            # Submit
            r = await client.post("https://2captcha.com/in.php", data={
                "key": self.api_key,
                "method": method,
                "googlekey": sitekey,
                "pageurl": page_url,
                "json": 1,
            })
            data = r.json()
            if data.get("status") != 1:
                return None
            task_id = data["request"]

            # Poll for result (max 120s)
            for _ in range(24):
                await asyncio.sleep(5)
                r = await client.get(f"https://2captcha.com/res.php?key={self.api_key}&action=get&id={task_id}&json=1")
                data = r.json()
                if data.get("status") == 1:
                    return data["request"]
                if "ERROR" in str(data.get("request", "")):
                    return None
        return None

    # ─── Anti-Captcha implementation ───

    async def _solve_anticaptcha(self, sitekey: str, page_url: str, task_type: str) -> Optional[str]:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post("https://api.anti-captcha.com/createTask", json={
                "clientKey": self.api_key,
                "task": {
                    "type": task_type,
                    "websiteURL": page_url,
                    "websiteKey": sitekey,
                },
            })
            data = r.json()
            task_id = data.get("taskId")
            if not task_id:
                return None

            for _ in range(24):
                await asyncio.sleep(5)
                r = await client.post("https://api.anti-captcha.com/getTaskResult", json={
                    "clientKey": self.api_key,
                    "taskId": task_id,
                })
                data = r.json()
                if data.get("status") == "ready":
                    return data.get("solution", {}).get("gRecaptchaResponse")
                if data.get("errorId", 0) > 0:
                    return None
        return None
