"""HTML → list of outbound links + page metadata."""
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup


@dataclass
class PageMetadata:
    title: Optional[str]
    word_count: int
    links: list[str]


def extract(html: str, base_url: str) -> PageMetadata:
    soup = BeautifulSoup(html, "lxml")

    title_tag = soup.find("title")
    title = title_tag.get_text(strip=True) if title_tag else None

    # Rough word count from body text
    body = soup.find("body")
    text = body.get_text(" ", strip=True) if body else ""
    word_count = len(text.split())

    # Links
    links: list[str] = []
    seen: set[str] = set()
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not href or href.startswith(("javascript:", "mailto:", "tel:", "#")):
            continue
        resolved = urljoin(base_url, href)
        if resolved in seen:
            continue
        seen.add(resolved)
        links.append(resolved)

    return PageMetadata(title=title, word_count=word_count, links=links)
