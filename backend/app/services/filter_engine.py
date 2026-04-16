"""Filter engine — decides whether an image candidate should be downloaded."""
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlparse

from app.schemas.job import ImageFilterConfig


@dataclass
class ImageCandidate:
    url: str
    alt: Optional[str] = None
    hint_width: Optional[int] = None
    hint_height: Optional[int] = None
    source_tag: str = "img"  # img | srcset | picture | css-bg | meta-og


class FilterEngine:
    def __init__(self, config: ImageFilterConfig):
        self.config = config

    def accept_url(self, candidate: ImageCandidate) -> tuple[bool, str]:
        """First-pass check (by URL / hints only). Returns (ok, reason)."""
        url = candidate.url.lower()
        path = urlparse(url).path

        # Extension check
        ext = path.rsplit(".", 1)[-1] if "." in path else ""
        if ext and ext not in self.config.allowed_types:
            return False, f"extension '{ext}' not allowed"

        # Exclude patterns
        for pattern in self.config.exclude_patterns:
            if pattern.lower() in url:
                return False, f"matched exclude pattern '{pattern}'"

        # Hint-based dimension check
        if candidate.hint_width and candidate.hint_width < self.config.min_width:
            return False, f"hint width {candidate.hint_width} < {self.config.min_width}"
        if candidate.hint_height and candidate.hint_height < self.config.min_height:
            return False, f"hint height {candidate.hint_height} < {self.config.min_height}"

        return True, "ok"

    def accept_bytes(self, size: int) -> tuple[bool, str]:
        if size < self.config.min_bytes:
            return False, f"size {size} < {self.config.min_bytes}"
        return True, "ok"

    def accept_dimensions(self, width: int, height: int) -> tuple[bool, str]:
        if width < self.config.min_width:
            return False, f"width {width} < {self.config.min_width}"
        if height < self.config.min_height:
            return False, f"height {height} < {self.config.min_height}"
        return True, "ok"
