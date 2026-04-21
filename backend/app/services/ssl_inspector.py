"""SSL certificate inspector - pakai stdlib ssl + socket."""
from __future__ import annotations

import asyncio
import logging
import socket
import ssl
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

logger = logging.getLogger("pyscrapr.ssl_inspector")


def _parse_host(hostname: str) -> str:
    hostname = hostname.strip()
    if "://" in hostname:
        return urlparse(hostname).netloc.split(":")[0]
    return hostname.split("/")[0].split(":")[0]


def _parse_cert_date(s: str) -> datetime | None:
    try:
        dt = datetime.strptime(s, "%b %d %H:%M:%S %Y %Z")
        return dt.replace(tzinfo=timezone.utc)
    except Exception:
        return None


def _flatten_name(seq) -> dict[str, str]:
    out: dict[str, str] = {}
    if not seq:
        return out
    for rdn in seq:
        for k, v in rdn:
            out[str(k)] = str(v)
    return out


def _blocking_inspect(host: str, port: int, timeout: int) -> dict[str, Any]:
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    with socket.create_connection((host, port), timeout=timeout) as sock:
        with ctx.wrap_socket(sock, server_hostname=host) as ssock:
            cert = ssock.getpeercert()
            tls_version = ssock.version()
            cipher = ssock.cipher()
            der = ssock.getpeercert(binary_form=True)

    subject = _flatten_name(cert.get("subject"))
    issuer = _flatten_name(cert.get("issuer"))
    not_before = cert.get("notBefore")
    not_after = cert.get("notAfter")
    nb_dt = _parse_cert_date(not_before) if not_before else None
    na_dt = _parse_cert_date(not_after) if not_after else None

    san: list[str] = []
    for typ, val in cert.get("subjectAltName", []) or []:
        if typ.lower() == "dns":
            san.append(val)

    now = datetime.now(timezone.utc)
    days_until_expiry = int((na_dt - now).total_seconds() // 86400) if na_dt else None
    is_expired = bool(na_dt and na_dt < now)
    is_self_signed = subject == issuer

    cn = subject.get("commonName", "")
    hostname_match = False
    target_lc = host.lower()
    if cn and cn.lower() == target_lc:
        hostname_match = True
    for name in san:
        if name.lower() == target_lc:
            hostname_match = True
            break
        if name.startswith("*.") and target_lc.endswith(name[1:].lower()):
            hostname_match = True
            break

    issues: list[dict[str, str]] = []
    if is_expired:
        issues.append({"severity": "error", "message": "Sertifikat sudah kedaluwarsa"})
    elif days_until_expiry is not None and days_until_expiry < 7:
        issues.append({"severity": "error", "message": f"Sertifikat akan kedaluwarsa dalam {days_until_expiry} hari"})
    elif days_until_expiry is not None and days_until_expiry < 30:
        issues.append({"severity": "warning", "message": f"Sertifikat akan kedaluwarsa dalam {days_until_expiry} hari"})
    if is_self_signed:
        issues.append({"severity": "warning", "message": "Sertifikat self-signed terdeteksi"})
    if not hostname_match:
        issues.append({"severity": "error", "message": f"Hostname {host} tidak cocok dengan CN atau SAN"})

    return {
        "hostname": host,
        "port": port,
        "fetched_at": now.isoformat(),
        "subject": subject,
        "issuer": issuer,
        "valid_from": not_before,
        "valid_to": not_after,
        "valid_from_iso": nb_dt.isoformat() if nb_dt else None,
        "valid_to_iso": na_dt.isoformat() if na_dt else None,
        "serial_number": cert.get("serialNumber"),
        "version": cert.get("version"),
        "san": san,
        "days_until_expiry": days_until_expiry,
        "is_expired": is_expired,
        "is_self_signed": is_self_signed,
        "hostname_match": hostname_match,
        "tls_version": tls_version,
        "cipher": {"name": cipher[0], "protocol": cipher[1], "bits": cipher[2]} if cipher else None,
        "cert_size_bytes": len(der) if der else 0,
        "issues": issues,
    }


class SslInspector:
    async def inspect(self, hostname: str, port: int = 443, timeout: int = 15) -> dict[str, Any]:
        host = _parse_host(hostname)
        if not host:
            raise ValueError("Hostname kosong")
        return await asyncio.to_thread(_blocking_inspect, host, port, timeout)


_singleton: SslInspector | None = None


def get_inspector() -> SslInspector:
    global _singleton
    if _singleton is None:
        _singleton = SslInspector()
    return _singleton
