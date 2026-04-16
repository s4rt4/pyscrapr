"""URL → local path mapper for Site Ripper.

Rules:
- https://example.com/         → <root>/index.html
- https://example.com/about    → <root>/about/index.html
- https://example.com/about/   → <root>/about/index.html
- https://example.com/x.css    → <root>/x.css
- https://example.com/img/a.png → <root>/img/a.png
- query params → appended to filename as _q<shorthash>
- missing extension (for html) → append .html
"""
import hashlib
import re
from pathlib import Path, PurePosixPath
from urllib.parse import urlparse, unquote

_SAFE_SEG = re.compile(r"[^A-Za-z0-9._-]+")
_HTML_EXTS = {".html", ".htm", ".xhtml"}
_ASSET_EXTS = {
    ".css", ".js", ".mjs", ".json",
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".avif", ".ico", ".bmp",
    ".woff", ".woff2", ".ttf", ".otf", ".eot",
    ".mp4", ".webm", ".mp3", ".ogg", ".wav",
    ".pdf", ".txt", ".xml",
}


def _sanitize(seg: str) -> str:
    seg = unquote(seg)
    seg = _SAFE_SEG.sub("_", seg).strip("_")
    return seg or "_"


def url_to_relpath(url: str, default_html: bool = False) -> PurePosixPath:
    """Return relative POSIX path inside the mirror root.

    *default_html*: when True and no extension can be inferred, append .html
    (used for HTML pages being saved).
    """
    parsed = urlparse(url)
    path = parsed.path or "/"

    segments = [_sanitize(s) for s in path.split("/") if s]
    last = segments[-1] if segments else ""

    has_ext = "." in last and ("." + last.rsplit(".", 1)[-1].lower()) in (_HTML_EXTS | _ASSET_EXTS)

    # Query → hash suffix so different ?v= versions don't clobber
    query_suffix = ""
    if parsed.query:
        qh = hashlib.sha1(parsed.query.encode()).hexdigest()[:8]
        query_suffix = f"_q{qh}"

    if path.endswith("/") or not segments:
        # Directory URL → index.html
        segments.append("index.html")
    elif not has_ext:
        if default_html:
            segments[-1] = segments[-1] + query_suffix + ".html"
            query_suffix = ""
        else:
            # Unknown asset, keep as-is but append suffix
            segments[-1] = segments[-1] + query_suffix
            query_suffix = ""
    else:
        # Has a known extension — inject query suffix before extension
        stem, ext = segments[-1].rsplit(".", 1)
        segments[-1] = f"{stem}{query_suffix}.{ext}"
        query_suffix = ""

    return PurePosixPath(*segments)


def to_local_path(root: Path, rel: PurePosixPath) -> Path:
    """Join rel (posix) onto OS-native root, ensuring it stays inside root."""
    candidate = (root / Path(*rel.parts)).resolve()
    root_resolved = root.resolve()
    try:
        candidate.relative_to(root_resolved)
    except ValueError:
        # Path traversal attempt — fall back to a hashed name
        h = hashlib.sha1(str(rel).encode()).hexdigest()[:12]
        candidate = root_resolved / f"_escaped_{h}"
    return candidate


def compute_relative(from_file: PurePosixPath, to_file: PurePosixPath) -> str:
    """Return a relative URL from one local file to another, suitable for href=."""
    from_dir = from_file.parent
    # Count how many ".." to climb out
    climb = []
    common = 0
    f_parts = from_dir.parts
    t_parts = to_file.parts
    for a, b in zip(f_parts, t_parts):
        if a == b:
            common += 1
        else:
            break
    climb = [".."] * (len(f_parts) - common)
    tail = list(t_parts[common:])
    parts = climb + tail
    if not parts:
        return to_file.name
    return "/".join(parts)
