"""URL normalization — canonicalize so equivalent URLs dedupe correctly."""
import re
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

# Tracking params stripped when strip_tracking_params=True
_TRACKING_PREFIXES = ("utm_",)
_TRACKING_KEYS = {
    "fbclid",
    "gclid",
    "dclid",
    "msclkid",
    "yclid",
    "igshid",
    "mc_cid",
    "mc_eid",
    "ref",
    "ref_",
    "ref_src",
    "ref_url",
    "_hsenc",
    "_hsmi",
}

_MULTI_SLASH = re.compile(r"/{2,}")


def normalize_url(url: str, strip_tracking: bool = True) -> str:
    """Return a canonical form of *url*.

    - lowercase scheme + host
    - strip fragment
    - collapse multi-slash in path
    - optionally strip tracking query params
    - sort remaining query params for stable comparison
    - ensure path is at least "/"
    """
    parsed = urlparse(url.strip())
    scheme = (parsed.scheme or "http").lower()
    netloc = parsed.netloc.lower()

    # Strip default ports
    if netloc.endswith(":80") and scheme == "http":
        netloc = netloc[:-3]
    elif netloc.endswith(":443") and scheme == "https":
        netloc = netloc[:-4]

    path = _MULTI_SLASH.sub("/", parsed.path or "/")
    if not path:
        path = "/"

    # Query params
    params = parse_qsl(parsed.query, keep_blank_values=True)
    if strip_tracking:
        params = [
            (k, v)
            for k, v in params
            if not k.startswith(_TRACKING_PREFIXES) and k.lower() not in _TRACKING_KEYS
        ]
    params.sort()
    query = urlencode(params, doseq=True)

    # Drop fragment entirely
    return urlunparse((scheme, netloc, path, parsed.params, query, ""))


def same_domain(url_a: str, url_b: str) -> bool:
    a = urlparse(url_a).netloc.lower().lstrip("www.")
    b = urlparse(url_b).netloc.lower().lstrip("www.")
    return a == b or a.endswith("." + b) or b.endswith("." + a)


def get_host(url: str) -> str:
    return urlparse(url).netloc.lower()
