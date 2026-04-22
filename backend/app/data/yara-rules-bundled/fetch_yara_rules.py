"""Manual fetcher for extra YARA rules.

Run this script to download additional community YARA rules into
`backend/app/data/yara-rules/` (user dir, separate from bundled).

Sources (curated, small):
  1. Elastic protections-artifacts: a few high-signal rules only
  2. YARAHQ / yara-forge core releases

This is MVP-scope: we pull a tiny set, not the full 5000+ rule bundle.
"""
from __future__ import annotations

import io
import sys
import tarfile
import urllib.request
from pathlib import Path

TARGET = Path(__file__).resolve().parent.parent / "yara-rules"
TARGET.mkdir(parents=True, exist_ok=True)

# Small curated set - single-file downloads from Elastic public repo
ELASTIC_RAW_BASE = (
    "https://raw.githubusercontent.com/elastic/protections-artifacts/main/yara/rules"
)

PICKS = [
    "Windows_Trojan_CobaltStrike.yar",
    "Windows_Ransomware_Lockbit.yar",
    "Multi_Generic_Suspicious.yar",
]


def fetch_one(name: str) -> bool:
    url = f"{ELASTIC_RAW_BASE}/{name}"
    out = TARGET / name
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            data = resp.read()
        out.write_bytes(data)
        print(f"OK  {name} ({len(data)} bytes)")
        return True
    except Exception as e:
        print(f"FAIL {name}: {e}", file=sys.stderr)
        return False


def main() -> int:
    ok = 0
    for name in PICKS:
        if fetch_one(name):
            ok += 1
    print(f"\nDownloaded {ok}/{len(PICKS)} rule files into {TARGET}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
