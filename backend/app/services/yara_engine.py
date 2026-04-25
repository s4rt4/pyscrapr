"""YARA rules engine - bundled rules + user rules dir.

Graceful fallback when yara-python missing.
"""
from __future__ import annotations

import io
import logging
import re
import time
import zipfile
from pathlib import Path
from typing import Any

from app.services import settings_store
from app.services.http_factory import build_client

logger = logging.getLogger("pyscrapr.threat.yara")

BUNDLED_DIR = Path(__file__).resolve().parent.parent / "data" / "yara-rules-bundled"
USER_DIR = Path(__file__).resolve().parent.parent / "data" / "yara-rules"
FETCHED_DIR = Path(__file__).resolve().parent.parent / "data" / "yara-rules-fetched"

_RULE_RE = re.compile(r"\brule\s+(\w+)(?:\s*:\s*([\w\s]+?))?\s*\{", re.MULTILINE)


def parse_yara_file_tags(filepath: Path) -> dict[str, list[str]]:
    """Parse a .yar/.yara file and return {rule_name: [tags]}."""
    out: dict[str, list[str]] = {}
    try:
        text = filepath.read_text(encoding="utf-8", errors="ignore")
    except Exception as e:
        logger.debug("baca yara file gagal %s: %s", filepath, e)
        return out
    for m in _RULE_RE.finditer(text):
        name = m.group(1)
        tags_raw = (m.group(2) or "").strip()
        tags = [t.strip() for t in tags_raw.split() if t.strip()] if tags_raw else []
        out[name] = tags
    return out

_yara_available: bool | None = None


def _check_yara() -> bool:
    global _yara_available
    if _yara_available is not None:
        return _yara_available
    try:
        import yara  # type: ignore  # noqa
        _yara_available = True
    except Exception as e:
        logger.warning("yara-python tidak tersedia: %s", e)
        _yara_available = False
    return _yara_available


class YaraEngine:
    def __init__(self) -> None:
        self.rules = None
        self.rule_files: list[dict[str, Any]] = []  # {name, path, namespace, source, tags}
        self.load_rules()

    def load_rules(self) -> None:
        if not _check_yara():
            return
        import yara  # type: ignore

        filepaths: dict[str, str] = {}
        self.rule_files = []

        sources = (
            (BUNDLED_DIR, "bundled"),
            (USER_DIR, "user"),
            (FETCHED_DIR, "fetched"),
        )
        for source_dir, ns_prefix in sources:
            if not source_dir.exists():
                continue
            for p in sorted(source_dir.iterdir()):
                if p.suffix.lower() not in (".yar", ".yara"):
                    continue
                ns = f"{ns_prefix}_{p.stem}"
                filepaths[ns] = str(p)
                tags_map = parse_yara_file_tags(p)
                # Aggregate unique tags across rules in file
                all_tags: list[str] = []
                seen: set[str] = set()
                for rule_tags in tags_map.values():
                    for t in rule_tags:
                        if t not in seen:
                            seen.add(t)
                            all_tags.append(t)
                self.rule_files.append({
                    "name": p.name,
                    "path": str(p),
                    "namespace": ns,
                    "source": ns_prefix,
                    "tags": all_tags,
                    "rules": list(tags_map.keys()),
                })

        if not filepaths:
            logger.info("YARA: tidak ada rules untuk dikompilasi")
            self.rules = None
            return

        try:
            self.rules = yara.compile(filepaths=filepaths)
            logger.info("YARA: kompilasi %d file rule sukses", len(filepaths))
        except Exception as e:
            logger.warning("YARA compile gagal: %s", e)
            self.rules = None

    def reload(self) -> int:
        self.load_rules()
        return len(self.rule_files)

    def list_rules(self) -> list[dict[str, Any]]:
        return list(self.rule_files)

    async def ensure_rules_downloaded(self, force: bool = False) -> dict[str, Any]:
        """Download YARAForge curated rules zip if stale or missing.

        Strategy: hit GitHub releases API for YARAHQ/yara-forge, pick the core
        zip asset, extract .yar/.yara into FETCHED_DIR, then reload.
        """
        marker = FETCHED_DIR / "_fetched.marker"
        last = int(settings_store.get("threat_yara_rules_last_updated", 0) or 0)
        age_days = (time.time() - last) / 86400 if last else 9999
        if not force and age_days < 7 and marker.exists():
            return {"status": "fresh", "last_updated": last, "age_days": round(age_days, 2)}

        FETCHED_DIR.mkdir(parents=True, exist_ok=True)
        try:
            async with build_client(timeout=60) as client:
                r = await client.get(
                    "https://api.github.com/repos/YARAHQ/yara-forge/releases/latest"
                )
                r.raise_for_status()
                data = r.json()
                asset_url = None
                asset_name = None
                for a in data.get("assets", []):
                    name = (a.get("name") or "").lower()
                    if "core" in name and name.endswith(".zip"):
                        asset_url = a.get("browser_download_url")
                        asset_name = a.get("name")
                        break
                if not asset_url:
                    # Fallback: any .zip
                    for a in data.get("assets", []):
                        name = (a.get("name") or "").lower()
                        if name.endswith(".zip"):
                            asset_url = a.get("browser_download_url")
                            asset_name = a.get("name")
                            break
                if not asset_url:
                    logger.warning("YARAForge: tidak ada zip asset di release")
                    return {"status": "no_asset"}

                r2 = await client.get(asset_url, follow_redirects=True)
                r2.raise_for_status()
                count = 0
                with zipfile.ZipFile(io.BytesIO(r2.content)) as zf:
                    for name in zf.namelist():
                        lname = name.lower()
                        if lname.endswith("/"):
                            continue
                        if not (lname.endswith(".yar") or lname.endswith(".yara")):
                            continue
                        target = FETCHED_DIR / Path(name).name
                        try:
                            target.write_bytes(zf.read(name))
                            count += 1
                        except Exception as e:
                            logger.debug("ekstrak %s gagal: %s", name, e)
                logger.info("YARA: %d rules diunduh dari %s ke %s", count, asset_name, FETCHED_DIR)

                ts = int(time.time())
                settings_store.update({"threat_yara_rules_last_updated": ts})
                marker.write_text(str(ts), encoding="utf-8")
                self.load_rules()
                return {
                    "status": "fetched",
                    "count": count,
                    "asset": asset_name,
                    "last_updated": ts,
                }
        except Exception as e:
            logger.warning("YARA rules auto-fetch gagal: %s", e)
            return {"status": "error", "error": str(e)}

    def scan_bytes(self, data: bytes) -> list[dict[str, Any]]:
        if not self.rules or not data:
            return []
        try:
            matches = self.rules.match(data=data, timeout=15)
        except Exception as e:
            logger.debug("YARA scan_bytes error: %s", e)
            return []
        out = []
        for m in matches:
            try:
                meta = dict(getattr(m, "meta", {}) or {})
                out.append({
                    "rule": m.rule,
                    "namespace": getattr(m, "namespace", ""),
                    "tags": list(getattr(m, "tags", []) or []),
                    "meta": meta,
                    "severity": str(meta.get("severity", "medium")),
                    "strings_count": len(getattr(m, "strings", []) or []),
                })
            except Exception:
                continue
        return out

    def scan_file(self, path: Path, max_bytes: int = 10 * 1024 * 1024) -> list[dict[str, Any]]:
        try:
            with path.open("rb") as f:
                data = f.read(max_bytes)
        except Exception as e:
            logger.debug("YARA scan_file baca gagal: %s", e)
            return []
        return self.scan_bytes(data)


_engine: YaraEngine | None = None


def get_engine() -> YaraEngine:
    global _engine
    if _engine is None:
        _engine = YaraEngine()
    return _engine
