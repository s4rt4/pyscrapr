"""SVG static analysis - detects script tags, on* handlers, javascript: URIs.

SVG files are XML and can embed active content (script, event handlers, foreign
HTML, external references). This module parses defensively via stdlib
xml.etree.ElementTree and flags common XSS / malware-delivery patterns.
"""
from __future__ import annotations

import gzip
import logging
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

logger = logging.getLogger("pyscrapr.threat.svg")

_MAX_BYTES = 5 * 1024 * 1024  # 5 MB cap for parsing

# Namespace-stripping helper: ElementTree returns tags like
# "{http://www.w3.org/2000/svg}script" - we just want "script".
_NS_RE = re.compile(r"^\{[^}]+\}")


def _localname(tag: str) -> str:
    return _NS_RE.sub("", tag or "").lower()


def _localattr(attr: str) -> str:
    return _NS_RE.sub("", attr or "").lower()


def _read_svg_bytes(path: Path) -> bytes:
    try:
        if path.suffix.lower() == ".svgz":
            with gzip.open(str(path), "rb") as g:
                return g.read(_MAX_BYTES)
        with path.open("rb") as f:
            return f.read(_MAX_BYTES)
    except Exception as e:
        logger.debug("baca SVG gagal: %s", e)
        return b""


async def analyze_svg(path: Path) -> dict[str, Any]:
    """Parse an SVG file and report active-content findings.

    Returns dict with:
      - findings: list of {kind, severity, title, description}
      - script_count, onattr_count, jsuri_count, foreign_object_count, external_image_count
      - available: True if parse succeeded
      - error: str on failure (parser must NEVER crash the caller)
    """
    out: dict[str, Any] = {
        "available": False,
        "error": None,
        "findings": [],
        "script_count": 0,
        "onattr_count": 0,
        "jsuri_count": 0,
        "foreign_object_count": 0,
        "external_image_count": 0,
    }

    raw = _read_svg_bytes(path)
    if not raw:
        out["error"] = "berkas SVG kosong atau tidak terbaca"
        return out

    # Defensive parse - malformed SVG must not crash the scan
    try:
        # iterparse handles large/streaming docs; but a plain fromstring is fine
        # for our 5 MB cap.
        root = ET.fromstring(raw)
        out["available"] = True
    except ET.ParseError as e:
        out["error"] = f"SVG tidak valid XML: {e}"
        # Fall back to regex-based detection on raw bytes (best-effort)
        return _regex_fallback(raw, out)
    except Exception as e:
        out["error"] = f"parse SVG gagal: {e}"
        return _regex_fallback(raw, out)

    findings: list[dict[str, Any]] = out["findings"]

    for el in root.iter():
        tag = _localname(el.tag)

        if tag == "script":
            out["script_count"] += 1
            findings.append({
                "kind": "script_tag",
                "severity": "high",
                "title": "SVG berisi tag <script>",
                "description": "SVG mengandung script aktif yang akan dieksekusi browser saat di-render.",
            })

        if tag == "foreignobject":
            out["foreign_object_count"] += 1
            findings.append({
                "kind": "foreign_object",
                "severity": "medium",
                "title": "SVG memiliki <foreignObject>",
                "description": "foreignObject memungkinkan embed HTML/XHTML asing di dalam SVG, bisa jadi vektor XSS.",
            })

        # image href external (SSRF / tracking pixel)
        if tag == "image":
            for k, v in (el.attrib or {}).items():
                ak = _localattr(k)
                if ak in ("href", "xlink:href"):
                    val = (v or "").strip().lower()
                    if val.startswith("http://") or val.startswith("https://") or val.startswith("//"):
                        out["external_image_count"] += 1
                        findings.append({
                            "kind": "external_image",
                            "severity": "low",
                            "title": "SVG memuat gambar eksternal",
                            "description": f"Referensi href ke {v[:120]} - potensi SSRF / tracking.",
                        })
                        break

        # Attribute-level checks: on* handlers + javascript: URIs
        for k, v in (el.attrib or {}).items():
            ak = _localattr(k)
            av = (v or "").strip()

            if ak.startswith("on") and len(ak) > 2:
                out["onattr_count"] += 1
                findings.append({
                    "kind": "on_attr",
                    "severity": "high",
                    "title": f"SVG memiliki event handler {ak}",
                    "description": f"Atribut {ak} pada <{tag}> akan menjalankan kode saat event terjadi.",
                })

            # javascript: URI in any attribute value
            if av.lower().startswith("javascript:"):
                out["jsuri_count"] += 1
                findings.append({
                    "kind": "javascript_uri",
                    "severity": "critical",
                    "title": "SVG memuat URI javascript:",
                    "description": f"Atribut {ak} pada <{tag}> berisi javascript: URI - XSS payload.",
                })

    return out


def _regex_fallback(raw: bytes, out: dict[str, Any]) -> dict[str, Any]:
    """Best-effort detection when XML parse fails (malformed SVG)."""
    try:
        text = raw.decode("utf-8", errors="ignore")
    except Exception:
        return out

    findings: list[dict[str, Any]] = out["findings"]

    if re.search(r"<\s*script\b", text, re.IGNORECASE):
        out["script_count"] += 1
        findings.append({
            "kind": "script_tag",
            "severity": "high",
            "title": "SVG berisi tag <script> (regex fallback)",
            "description": "Parser XML gagal, namun pola <script> terdeteksi via regex.",
        })

    on_matches = re.findall(r"\son[a-zA-Z]+\s*=", text)
    if on_matches:
        out["onattr_count"] += len(on_matches)
        findings.append({
            "kind": "on_attr",
            "severity": "high",
            "title": f"SVG memiliki {len(on_matches)} event handler on*",
            "description": "Pola on*= terdeteksi via regex fallback.",
        })

    if re.search(r"=\s*[\"']javascript:", text, re.IGNORECASE):
        out["jsuri_count"] += 1
        findings.append({
            "kind": "javascript_uri",
            "severity": "critical",
            "title": "SVG memuat URI javascript: (regex fallback)",
            "description": "Pola javascript: URI terdeteksi via regex fallback.",
        })

    return out
