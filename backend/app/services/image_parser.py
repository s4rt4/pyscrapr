"""HTML → list of ImageCandidate. Pure function, no I/O."""
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from app.services.filter_engine import ImageCandidate


_CSS_URL_RE = re.compile(r"url\(\s*['\"]?([^'\")]+)['\"]?\s*\)", re.IGNORECASE)


def _pick_largest_from_srcset(srcset: str) -> str | None:
    """srcset='url1 1x, url2 2x, url3 800w' → pick the largest."""
    best_url, best_score = None, -1.0
    for entry in srcset.split(","):
        entry = entry.strip()
        if not entry:
            continue
        parts = entry.split()
        if not parts:
            continue
        url = parts[0]
        score = 1.0
        if len(parts) > 1:
            desc = parts[1]
            if desc.endswith("x"):
                try:
                    score = float(desc[:-1])
                except ValueError:
                    pass
            elif desc.endswith("w"):
                try:
                    score = float(desc[:-1]) / 100.0
                except ValueError:
                    pass
        if score > best_score:
            best_score, best_url = score, url
    return best_url


def parse_images(html: str, base_url: str, include_css_bg: bool = False) -> list[ImageCandidate]:
    soup = BeautifulSoup(html, "lxml")
    seen: set[str] = set()
    out: list[ImageCandidate] = []

    def add(url: str | None, alt: str | None, source: str, w=None, h=None):
        if not url:
            return
        resolved = urljoin(base_url, url.strip())
        if resolved in seen:
            return
        seen.add(resolved)
        out.append(ImageCandidate(
            url=resolved, alt=alt, hint_width=w, hint_height=h, source_tag=source
        ))

    # <img>
    for img in soup.find_all("img"):
        src = img.get("src") or img.get("data-src") or img.get("data-lazy-src")
        alt = img.get("alt")
        w = _int_or_none(img.get("width"))
        h = _int_or_none(img.get("height"))
        add(src, alt, "img", w, h)

        srcset = img.get("srcset") or img.get("data-srcset")
        if srcset:
            add(_pick_largest_from_srcset(srcset), alt, "srcset", w, h)

    # <picture><source srcset>
    for source in soup.find_all("source"):
        srcset = source.get("srcset")
        if srcset:
            add(_pick_largest_from_srcset(srcset), None, "picture")

    # <meta property="og:image">
    for meta in soup.find_all("meta", attrs={"property": "og:image"}):
        add(meta.get("content"), None, "meta-og")

    # CSS background-image (inline style + optional full stylesheet scan)
    if include_css_bg:
        for el in soup.find_all(style=True):
            for match in _CSS_URL_RE.finditer(el.get("style", "")):
                add(match.group(1), None, "css-bg")
        for style in soup.find_all("style"):
            if style.string:
                for match in _CSS_URL_RE.finditer(style.string):
                    add(match.group(1), None, "css-bg")

    return out


def _int_or_none(val) -> int | None:
    if val is None:
        return None
    try:
        return int(str(val).strip())
    except (ValueError, TypeError):
        return None
