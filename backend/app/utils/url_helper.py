"""URL utilities — pure functions."""
from urllib.parse import urlparse


def extract_domain(url: str) -> str:
    parsed = urlparse(url)
    host = parsed.netloc or parsed.path
    return host.replace(":", "_") or "unknown"
