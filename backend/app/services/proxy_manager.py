"""Proxy rotation manager — round-robin or random proxy from a list.

Supports HTTP, HTTPS, SOCKS5 proxy URLs.
Integrates with httpx via transport/proxy parameter.
"""
import random
from typing import Optional


class ProxyManager:
    def __init__(self, proxies: list[str] | None = None, mode: str = "round_robin"):
        """
        proxies: list of proxy URLs, e.g. ["http://user:pass@host:port", "socks5://host:port"]
        mode: "round_robin", "random", or "none"
        """
        self.proxies = [p.strip() for p in (proxies or []) if p.strip()]
        self.mode = mode if self.proxies else "none"
        self._index = 0

    def get_proxy(self) -> Optional[str]:
        if not self.proxies or self.mode == "none":
            return None
        if self.mode == "random":
            return random.choice(self.proxies)
        # round_robin
        proxy = self.proxies[self._index % len(self.proxies)]
        self._index += 1
        return proxy

    def get_httpx_proxy_arg(self) -> Optional[str]:
        """Return a proxy URL suitable for httpx.AsyncClient(proxy=...)."""
        return self.get_proxy()

    @property
    def count(self) -> int:
        return len(self.proxies)

    @property
    def enabled(self) -> bool:
        return len(self.proxies) > 0 and self.mode != "none"
