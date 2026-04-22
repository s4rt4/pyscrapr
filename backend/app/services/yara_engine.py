"""YARA rules engine - bundled rules + user rules dir.

Graceful fallback when yara-python missing.
"""
from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any

from app.services import settings_store

logger = logging.getLogger("pyscrapr.threat.yara")

BUNDLED_DIR = Path(__file__).resolve().parent.parent / "data" / "yara-rules-bundled"
USER_DIR = Path(__file__).resolve().parent.parent / "data" / "yara-rules"

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
        self.rule_files: list[dict[str, str]] = []  # {name, path, namespace}
        self.load_rules()

    def load_rules(self) -> None:
        if not _check_yara():
            return
        import yara  # type: ignore

        filepaths: dict[str, str] = {}
        self.rule_files = []

        for source_dir, ns_prefix in ((BUNDLED_DIR, "bundled"), (USER_DIR, "user")):
            if not source_dir.exists():
                continue
            for p in sorted(source_dir.iterdir()):
                if p.suffix.lower() not in (".yar", ".yara"):
                    continue
                ns = f"{ns_prefix}_{p.stem}"
                filepaths[ns] = str(p)
                self.rule_files.append(
                    {"name": p.name, "path": str(p), "namespace": ns, "source": ns_prefix}
                )

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

    def list_rules(self) -> list[dict[str, str]]:
        return list(self.rule_files)

    async def ensure_rules_downloaded(self) -> dict[str, Any]:
        """Placeholder for runtime fetch. MVP ships bundled rules; user runs
        data/yara-rules-bundled/fetch_yara_rules.py manually for extras.
        """
        last = settings_store.get("threat_yara_rules_last_updated", 0) or 0
        if last:
            return {"status": "already_present", "last_updated": last}
        settings_store.update({"threat_yara_rules_last_updated": int(time.time())})
        return {
            "status": "bundled_only",
            "message": "Aturan bundled digunakan. Untuk tambahan, jalankan fetch_yara_rules.py secara manual.",
        }

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
