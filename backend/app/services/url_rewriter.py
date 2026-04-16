"""Rewrite HTML + CSS so all absolute URLs point to local mirror files.

Input:
  - source HTML (string)
  - current page's URL (for resolving relatives)
  - url_map: dict mapping normalized URL → local file PurePosixPath (relative to mirror root)
  - current_file: PurePosixPath of the current page

Output: rewritten string.
"""
import re
from pathlib import PurePosixPath
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from app.services.mirror_path_mapper import compute_relative

_CSS_URL_RE = re.compile(r"""url\(\s*(['"]?)([^'")]+?)\1\s*\)""", re.IGNORECASE)
_CSS_IMPORT_RE = re.compile(
    r"""(@import\s+)(url\(\s*(['"]?)([^'")]+?)\3\s*\)|(['"])([^'"]+?)\5)""",
    re.IGNORECASE,
)


def _resolve(url: str, base: str, url_map: dict[str, PurePosixPath]) -> str | None:
    full = urljoin(base, url.strip())
    return str(url_map.get(full)) if full in url_map else None


def rewrite_html(
    html: str,
    page_url: str,
    current_file: PurePosixPath,
    url_map: dict[str, PurePosixPath],
) -> str:
    soup = BeautifulSoup(html, "lxml")

    def rewrite_attr(el, attr: str) -> None:
        val = el.get(attr)
        if not val:
            return
        full = urljoin(page_url, val.strip())
        target = url_map.get(full)
        if target is not None:
            el[attr] = compute_relative(current_file, target)

    def rewrite_srcset(el, attr: str = "srcset") -> None:
        val = el.get(attr)
        if not val:
            return
        parts_out = []
        for item in val.split(","):
            item = item.strip()
            if not item:
                continue
            bits = item.split(None, 1)
            url = bits[0]
            desc = bits[1] if len(bits) > 1 else ""
            full = urljoin(page_url, url)
            target = url_map.get(full)
            if target is not None:
                url = compute_relative(current_file, target)
            parts_out.append(f"{url} {desc}".strip())
        el[attr] = ", ".join(parts_out)

    for link in soup.find_all("link", href=True):
        rewrite_attr(link, "href")
    for script in soup.find_all("script", src=True):
        rewrite_attr(script, "src")
    for img in soup.find_all("img"):
        rewrite_attr(img, "src")
        rewrite_attr(img, "data-src")
        rewrite_srcset(img, "srcset")
        rewrite_srcset(img, "data-srcset")
    for src in soup.find_all("source"):
        rewrite_srcset(src, "srcset")
        rewrite_attr(src, "src")
    for video in soup.find_all("video"):
        rewrite_attr(video, "src")
        rewrite_attr(video, "poster")
    for audio in soup.find_all("audio"):
        rewrite_attr(audio, "src")
    for frame in soup.find_all("iframe", src=True):
        rewrite_attr(frame, "src")
    for a in soup.find_all("a", href=True):
        rewrite_attr(a, "href")

    # Inline style attributes
    for el in soup.find_all(style=True):
        style = el.get("style", "")
        el["style"] = _rewrite_css_urls(style, page_url, current_file, url_map)

    # <style> blocks
    for style in soup.find_all("style"):
        if style.string:
            style.string = _rewrite_css_urls(style.string, page_url, current_file, url_map)

    return str(soup)


def rewrite_css(
    css: str,
    css_url: str,
    current_file: PurePosixPath,
    url_map: dict[str, PurePosixPath],
) -> str:
    return _rewrite_css_urls(css, css_url, current_file, url_map)


def _rewrite_css_urls(
    css: str,
    base_url: str,
    current_file: PurePosixPath,
    url_map: dict[str, PurePosixPath],
) -> str:
    def replace_url(match: re.Match) -> str:
        quote = match.group(1)
        url = match.group(2)
        if url.startswith(("data:", "#")):
            return match.group(0)
        full = urljoin(base_url, url.strip())
        target = url_map.get(full)
        if target is None:
            return match.group(0)
        new_url = compute_relative(current_file, target)
        return f"url({quote}{new_url}{quote})"

    css = _CSS_URL_RE.sub(replace_url, css)

    def replace_import(match: re.Match) -> str:
        prefix = match.group(1)
        raw_url = match.group(4) or match.group(6)
        if not raw_url or raw_url.startswith(("data:", "#")):
            return match.group(0)
        full = urljoin(base_url, raw_url.strip())
        target = url_map.get(full)
        if target is None:
            return match.group(0)
        new_url = compute_relative(current_file, target)
        return f'{prefix}"{new_url}"'

    css = _CSS_IMPORT_RE.sub(replace_import, css)
    return css
