"""Cross-platform path helpers."""
import re
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

_SAFE_RE = re.compile(r"[^A-Za-z0-9._-]+")


def domain_folder(base: Path, domain: str, kind: str) -> Path:
    """`downloads/example.com/2026-04-14_images/originals/`"""
    today = date.today().isoformat()
    safe_domain = _SAFE_RE.sub("_", domain).strip("_") or "unknown"
    return base / safe_domain / f"{today}_{kind}" / "originals"


def safe_filename(url: str, index: int = 0, default_ext: str = "bin") -> str:
    """Produce a safe filename from a URL. Keeps the extension when reasonable."""
    parsed = urlparse(url)
    name = Path(parsed.path).name or f"asset_{index}"
    # split extension
    stem, _, ext = name.rpartition(".")
    if not stem:
        stem, ext = name, default_ext
    stem = _SAFE_RE.sub("_", stem).strip("_")[:80] or f"asset_{index}"
    ext = _SAFE_RE.sub("", ext).lower()[:5] or default_ext
    return f"{index:04d}_{stem}.{ext}"
