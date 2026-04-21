"""One-shot downloader for Wappalyzer fingerprints from tunetheweb/wappalyzer.

Run this script to populate backend/app/data/wappalyzer/ with the latest rules:

    python -m app.data.wappalyzer.fetch_rules

Uses urllib (no extra deps). Skips any 404 file and logs total counts.
"""
from __future__ import annotations

import json
import logging
import string
import sys
import urllib.error
import urllib.request
from pathlib import Path

logger = logging.getLogger("pyscrapr.wappalyzer.fetch")

BASE = "https://raw.githubusercontent.com/enthec/webappanalyzer/main/src"
HERE = Path(__file__).resolve().parent
TECH_DIR = HERE / "technologies"


def _download(url: str, dest: Path) -> bool:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "pyscrapr-wappalyzer-fetch/1.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = resp.read()
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        return True
    except urllib.error.HTTPError as e:
        if e.code == 404:
            logger.warning("404 skip: %s", url)
            return False
        logger.error("HTTP %s on %s", e.code, url)
        return False
    except Exception as e:
        logger.error("Failed %s: %s", url, e)
        return False


def fetch_all() -> tuple[int, int]:
    TECH_DIR.mkdir(parents=True, exist_ok=True)

    # categories + groups
    _download(f"{BASE}/categories.json", HERE / "categories.json")
    _download(f"{BASE}/groups.json", HERE / "groups.json")

    # technologies/a.json .. z.json + _.json
    letters = list(string.ascii_lowercase) + ["_"]
    tech_total = 0
    for letter in letters:
        dest = TECH_DIR / f"{letter}.json"
        if _download(f"{BASE}/technologies/{letter}.json", dest):
            try:
                data = json.loads(dest.read_text(encoding="utf-8"))
                tech_total += len(data)
            except Exception:
                pass

    # category count
    cat_count = 0
    cat_file = HERE / "categories.json"
    if cat_file.exists():
        try:
            cat_count = len(json.loads(cat_file.read_text(encoding="utf-8")))
        except Exception:
            pass

    return tech_total, cat_count


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    techs, cats = fetch_all()
    logger.info("Wappalyzer rules fetched: technologies=%d categories=%d", techs, cats)
    print(f"technologies={techs} categories={cats}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
