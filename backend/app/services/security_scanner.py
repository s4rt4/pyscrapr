"""Security headers scanner - cek HTTP security headers + cookie flags."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from http.cookies import SimpleCookie
from typing import Any

import httpx

from app.services.http_factory import build_client

logger = logging.getLogger("pyscrapr.security_scanner")


# (header_name, severity, description_id, weight)
_CHECKS: list[tuple[str, str, str, int]] = [
    ("Strict-Transport-Security", "error", "Wajib untuk memaksa HTTPS dan mencegah downgrade attack", 20),
    ("Content-Security-Policy", "error", "Kebijakan konten untuk mitigasi XSS dan injection", 20),
    ("X-Frame-Options", "warning", "Mencegah clickjacking lewat iframe", 10),
    ("X-Content-Type-Options", "warning", "Mencegah MIME sniffing (nilai nosniff)", 8),
    ("Referrer-Policy", "warning", "Kontrol informasi referrer saat navigasi", 6),
    ("Permissions-Policy", "info", "Kontrol akses fitur browser seperti kamera atau mikrofon", 5),
    ("Cross-Origin-Opener-Policy", "info", "Isolasi browsing context lintas origin", 5),
    ("Cross-Origin-Embedder-Policy", "info", "Kontrol embed resource lintas origin", 5),
    ("Cross-Origin-Resource-Policy", "info", "Kontrol resource yang boleh di-embed", 5),
]


def _grade(score: int) -> str:
    if score >= 90:
        return "A"
    if score >= 75:
        return "B"
    if score >= 60:
        return "C"
    if score >= 45:
        return "D"
    if score >= 30:
        return "E"
    return "F"


class SecurityScanner:
    async def scan(self, url: str, timeout: int = 20) -> dict[str, Any]:
        async with build_client(timeout=timeout, target_url=url) as client:
            try:
                resp = await client.get(url)
            except httpx.HTTPError as e:
                logger.warning("security fetch failed: %s", e)
                raise
            headers = {k: v for k, v in resp.headers.items()}
            final_url = str(resp.url)
            status_code = resp.status_code
            raw_set_cookies: list[str] = []
            try:
                raw_set_cookies = resp.headers.get_list("set-cookie") if hasattr(resp.headers, "get_list") else []
            except Exception:
                raw_set_cookies = []
            if not raw_set_cookies and "set-cookie" in resp.headers:
                raw_set_cookies = [resp.headers["set-cookie"]]

        headers_lc = {k.lower(): v for k, v in headers.items()}

        headers_found: dict[str, str] = {}
        headers_missing: list[str] = []
        issues: list[dict[str, str]] = []
        total_weight = sum(w for _, _, _, w in _CHECKS)
        earned = 0

        for name, severity, desc, weight in _CHECKS:
            val = headers_lc.get(name.lower())
            if val:
                headers_found[name] = val
                earned += weight
                # Value-strength checks
                if name == "Strict-Transport-Security":
                    if "max-age" not in val.lower() or "max-age=0" in val.lower():
                        issues.append({"severity": "warning", "header": name, "message": "HSTS max-age lemah atau tidak ada"})
                        earned -= weight // 2
                if name == "X-Content-Type-Options" and "nosniff" not in val.lower():
                    issues.append({"severity": "warning", "header": name, "message": "Nilai sebaiknya nosniff"})
                if name == "X-Frame-Options" and val.lower() not in ("deny", "sameorigin"):
                    issues.append({"severity": "info", "header": name, "message": "Nilai di luar DENY atau SAMEORIGIN"})
            else:
                headers_missing.append(name)
                issues.append({"severity": severity, "header": name, "message": f"Header {name} hilang - {desc}"})

        score = max(0, min(100, int(earned * 100 / total_weight))) if total_weight else 0
        grade = _grade(score)

        cookies: list[dict[str, Any]] = []
        for raw in raw_set_cookies:
            try:
                sc = SimpleCookie()
                sc.load(raw)
                for cname, morsel in sc.items():
                    cookies.append(
                        {
                            "name": cname,
                            "httponly": bool(morsel["httponly"]) if morsel["httponly"] else False,
                            "secure": bool(morsel["secure"]) if morsel["secure"] else False,
                            "samesite": morsel["samesite"] or None,
                            "path": morsel["path"] or "/",
                        }
                    )
                    if not morsel["secure"]:
                        issues.append({"severity": "warning", "header": f"Cookie:{cname}", "message": f"Cookie {cname} tidak punya flag Secure"})
                    if not morsel["httponly"]:
                        issues.append({"severity": "info", "header": f"Cookie:{cname}", "message": f"Cookie {cname} tidak punya flag HttpOnly"})
                    if not morsel["samesite"]:
                        issues.append({"severity": "info", "header": f"Cookie:{cname}", "message": f"Cookie {cname} tidak punya atribut SameSite"})
            except Exception as e:
                logger.debug("cookie parse fail: %s", e)

        return {
            "url": url,
            "final_url": final_url,
            "status_code": status_code,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "score": score,
            "grade": grade,
            "headers_found": headers_found,
            "headers_missing": headers_missing,
            "all_response_headers": headers,
            "cookies": cookies,
            "issues": issues,
        }


_singleton: SecurityScanner | None = None


def get_scanner() -> SecurityScanner:
    global _singleton
    if _singleton is None:
        _singleton = SecurityScanner()
    return _singleton
