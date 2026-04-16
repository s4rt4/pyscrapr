"""Extract every asset URL from HTML / CSS.

HTML targets:
  - <link rel="stylesheet" href>
  - <link rel~="icon" href>
  - <script src>
  - <img src | srcset | data-src>
  - <source src | srcset>  (picture/video/audio)
  - <video/audio src>
  - <iframe src>
  - Inline style="url(...)"
  - Inline <style>...</style>

CSS targets:
  - url(...)
  - @import "..." / @import url(...)
"""
import re
from dataclasses import dataclass
from typing import Iterable
from urllib.parse import urljoin

from bs4 import BeautifulSoup


_CSS_URL_RE = re.compile(r"""url\(\s*['"]?([^'")]+?)['"]?\s*\)""", re.IGNORECASE)
_CSS_IMPORT_RE = re.compile(
    r"""@import\s+(?:url\(\s*['"]?([^'")]+?)['"]?\s*\)|['"]([^'"]+?)['"])""",
    re.IGNORECASE,
)


@dataclass
class AssetRef:
    url: str
    kind: str  # css | js | image | font | video | audio | favicon | html | iframe | other


def _pick_best_srcset(srcset: str) -> str | None:
    best, best_score = None, -1.0
    for item in srcset.split(","):
        item = item.strip()
        if not item:
            continue
        parts = item.split()
        if not parts:
            continue
        url = parts[0]
        score = 1.0
        if len(parts) > 1:
            d = parts[1]
            if d.endswith("x"):
                try:
                    score = float(d[:-1])
                except ValueError:
                    pass
            elif d.endswith("w"):
                try:
                    score = float(d[:-1]) / 100.0
                except ValueError:
                    pass
        if score > best_score:
            best, best_score = url, score
    return best


def _guess_kind_from_url(url: str) -> str:
    low = url.lower().split("?")[0]
    if low.endswith((".css",)):
        return "css"
    if low.endswith((".js", ".mjs")):
        return "js"
    if low.endswith((".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".avif", ".bmp")):
        return "image"
    if low.endswith((".ico",)):
        return "favicon"
    if low.endswith((".woff", ".woff2", ".ttf", ".otf", ".eot")):
        return "font"
    if low.endswith((".mp4", ".webm", ".ogv")):
        return "video"
    if low.endswith((".mp3", ".ogg", ".wav", ".flac", ".m4a")):
        return "audio"
    return "other"


def extract_html_assets(html: str, base_url: str) -> tuple[list[AssetRef], list[str]]:
    """Return (assets, page_links).

    *page_links* are same-site <a href> candidates the ripper may want to crawl.
    Assets are de-duplicated by URL within one call.
    """
    soup = BeautifulSoup(html, "lxml")
    assets: dict[str, AssetRef] = {}
    links: list[str] = []
    seen_links: set[str] = set()

    def add(u: str | None, kind: str):
        if not u:
            return
        u = u.strip()
        if not u or u.startswith(("data:", "javascript:", "mailto:", "tel:")):
            return
        full = urljoin(base_url, u)
        if full not in assets:
            assets[full] = AssetRef(url=full, kind=kind)

    # <link>
    for link in soup.find_all("link"):
        rels = [r.lower() for r in (link.get("rel") or [])]
        href = link.get("href")
        if not href:
            continue
        if "stylesheet" in rels:
            add(href, "css")
        elif any("icon" in r for r in rels):
            add(href, "favicon")
        elif any(r in ("preload", "prefetch") for r in rels):
            as_type = (link.get("as") or "").lower()
            kind = {
                "style": "css",
                "script": "js",
                "font": "font",
                "image": "image",
            }.get(as_type, _guess_kind_from_url(href))
            add(href, kind)

    # <script src>
    for script in soup.find_all("script", src=True):
        add(script.get("src"), "js")

    # <img>, <source>, <video>, <audio>
    for img in soup.find_all("img"):
        src = img.get("src") or img.get("data-src") or img.get("data-lazy-src")
        add(src, "image")
        srcset = img.get("srcset") or img.get("data-srcset")
        if srcset:
            add(_pick_best_srcset(srcset), "image")

    for src in soup.find_all("source"):
        ss = src.get("srcset")
        if ss:
            add(_pick_best_srcset(ss), "image")
        add(src.get("src"), _guess_kind_from_url(src.get("src") or ""))

    for video in soup.find_all("video"):
        add(video.get("poster"), "image")
        add(video.get("src"), "video")
    for audio in soup.find_all("audio"):
        add(audio.get("src"), "audio")

    # <iframe>
    for frame in soup.find_all("iframe", src=True):
        add(frame.get("src"), "iframe")

    # Inline style
    for el in soup.find_all(style=True):
        for m in _CSS_URL_RE.finditer(el.get("style", "")):
            u = m.group(1)
            add(u, _guess_kind_from_url(u))

    # <style>
    for style in soup.find_all("style"):
        if style.string:
            for u in extract_css_urls(style.string):
                add(u, _guess_kind_from_url(u))

    # <a href> for same-site page crawling
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not href or href.startswith(("javascript:", "mailto:", "tel:", "#")):
            continue
        full = urljoin(base_url, href)
        if full not in seen_links:
            seen_links.add(full)
            links.append(full)

    return list(assets.values()), links


def extract_css_urls(css: str) -> list[str]:
    """Return every url(...) and @import target in a CSS string."""
    out: list[str] = []
    for m in _CSS_IMPORT_RE.finditer(css):
        out.append(m.group(1) or m.group(2))
    for m in _CSS_URL_RE.finditer(css):
        out.append(m.group(1))
    return [u for u in out if u and not u.startswith(("data:", "#"))]
