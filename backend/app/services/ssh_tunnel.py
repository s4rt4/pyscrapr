"""SSH tunnel with SOCKS5 dynamic forwarding for Media Downloader bypass.

Use case: user has an SSH account at a SG/JP/HK server (premium service like
SSHKit, FastSSH, BestVPN.cc). Establish SSH connection, expose local SOCKS5
listener that forwards via tunnel. Same pattern as Bitvise SOCKS forwarding
or `ssh -D 1080`.

Defeats ISP DPI completely because SSH traffic is opaque to the network
middleman - they only see encrypted SSH packets to the SG endpoint, never
the target site's SNI.

Implementation uses asyncssh:
- Pure Python, no GUI install needed
- Supports password + key auth natively
- Built-in SOCKS5 server via forward_socks()
- Background asyncio task keeps connection alive

Singleton pattern: only one tunnel at a time across the backend. Start/stop
via the API. Status query for UI badge.
"""
from __future__ import annotations

import asyncio
import logging
import time
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger("pyscrapr.ssh_tunnel")


class SSHTunnel:
    """Singleton SSH tunnel manager."""

    def __init__(self) -> None:
        self._connection: Any = None  # asyncssh.SSHClientConnection
        self._listener: Any = None  # asyncssh.SSHListener
        self._host: str = ""
        self._port: int = 22
        self._username: str = ""
        self._local_port: int = 1080
        self._started_at: Optional[float] = None
        self._lock = asyncio.Lock()

    @property
    def is_connected(self) -> bool:
        return self._connection is not None and not self._connection.is_closed()

    async def start(
        self,
        host: str,
        port: int,
        username: str,
        auth_method: str,  # "password" | "key"
        password: str = "",
        key_path: str = "",
        local_port: int = 1080,
        connect_timeout: int = 15,
    ) -> dict[str, Any]:
        """Establish SSH tunnel and bind SOCKS5 listener on local_port.

        Returns dict {ok, host, local_port, started_at, error?}.
        Never raises - errors returned in dict so callers can decide UX.
        """
        async with self._lock:
            # Tear down any existing tunnel first
            if self._connection is not None:
                await self._stop_internal()

            try:
                import asyncssh  # lazy import so missing dep doesn't break boot
            except ImportError:
                return {
                    "ok": False,
                    "error": "asyncssh tidak terpasang. Jalankan: pip install asyncssh",
                }

            host = (host or "").strip()
            username = (username or "").strip()
            if not host or not username:
                return {"ok": False, "error": "Host dan username wajib diisi"}
            if auth_method not in ("password", "key"):
                return {"ok": False, "error": "auth_method harus 'password' atau 'key'"}

            connect_kwargs: dict[str, Any] = {
                "host": host,
                "port": int(port or 22),
                "username": username,
                "known_hosts": None,  # skip strict host key check for user-managed servers
                "client_keys": [],
                "connect_timeout": connect_timeout,
            }
            if auth_method == "password":
                if not password:
                    return {"ok": False, "error": "Password kosong"}
                connect_kwargs["password"] = password
            else:
                key_path = (key_path or "").strip()
                if not key_path:
                    return {"ok": False, "error": "Path private key kosong"}
                key_file = Path(key_path)
                if not key_file.exists():
                    return {"ok": False, "error": f"Private key tidak ditemukan: {key_path}"}
                connect_kwargs["client_keys"] = [str(key_file)]

            try:
                self._connection = await asyncssh.connect(**connect_kwargs)
            except Exception as exc:
                self._connection = None
                err_type = type(exc).__name__
                msg = str(exc) or repr(exc)
                logger.warning("SSH connect gagal: %s: %s", err_type, msg)
                # Sanitize common error messages for end users
                low = msg.lower()
                if "authentication" in low or "permission denied" in low:
                    return {"ok": False, "error": "Autentikasi gagal. Cek username/password/key."}
                if "timeout" in low or "timed out" in low:
                    return {"ok": False, "error": f"Connect timeout ke {host}:{port}"}
                if "name or service" in low or "no address associated" in low:
                    return {"ok": False, "error": f"Host tidak ditemukan: {host}"}
                if "connection refused" in low:
                    return {"ok": False, "error": f"Connection refused ke {host}:{port}"}
                return {"ok": False, "error": f"{err_type}: {msg[:200]}"}

            # Bind SOCKS5 dynamic forwarding listener
            local_port = int(local_port or 1080)
            try:
                self._listener = await self._connection.forward_socks(
                    listen_host="127.0.0.1", listen_port=local_port
                )
            except Exception as exc:
                logger.warning("forward_socks gagal: %s", exc)
                try:
                    self._connection.close()
                except Exception:
                    pass
                self._connection = None
                return {
                    "ok": False,
                    "error": f"Bind SOCKS5 port {local_port} gagal: {exc}",
                }

            self._host = host
            self._port = int(port or 22)
            self._username = username
            self._local_port = local_port
            self._started_at = time.time()

            logger.info(
                "SSH tunnel started: %s@%s:%s, SOCKS5 listening on 127.0.0.1:%s",
                username, host, port, local_port,
            )
            return {
                "ok": True,
                "host": host,
                "port": self._port,
                "username": username,
                "local_port": local_port,
                "started_at": self._started_at,
            }

    async def _stop_internal(self) -> None:
        """Inner stop (caller holds lock)."""
        if self._listener is not None:
            try:
                self._listener.close()
                await self._listener.wait_closed()
            except Exception as exc:
                logger.debug("Listener close err (non-fatal): %s", exc)
            self._listener = None
        if self._connection is not None:
            try:
                self._connection.close()
                await self._connection.wait_closed()
            except Exception as exc:
                logger.debug("Connection close err (non-fatal): %s", exc)
            self._connection = None
        self._started_at = None

    async def stop(self) -> dict[str, Any]:
        async with self._lock:
            if self._connection is None:
                return {"ok": True, "connected": False, "message": "Tidak ada tunnel aktif"}
            await self._stop_internal()
            return {"ok": True, "connected": False, "message": "Tunnel ditutup"}

    def status(self) -> dict[str, Any]:
        connected = self.is_connected
        return {
            "ok": True,
            "connected": connected,
            "host": self._host if connected else "",
            "port": self._port if connected else 22,
            "username": self._username if connected else "",
            "local_port": self._local_port if connected else 0,
            "started_at": self._started_at if connected else None,
            "uptime_seconds": int(time.time() - self._started_at) if (connected and self._started_at) else 0,
        }


# Singleton instance
_tunnel: Optional[SSHTunnel] = None


def get_tunnel() -> SSHTunnel:
    global _tunnel
    if _tunnel is None:
        _tunnel = SSHTunnel()
    return _tunnel
