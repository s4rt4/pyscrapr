"""Entry point - run with: python run.py

Environment variables:
    PYSCRAPR_RELOAD=1   Enable uvicorn --reload (dev only, Windows users:
                        disables Playwright due to SelectorEventLoop subprocess
                        limitation in reload child processes).
    PYSCRAPR_PORT=8000  Override listen port.
"""
import asyncio
import os
import sys
from pathlib import Path

# Ensure backend/ is on sys.path and cwd, regardless of where we're launched from
BACKEND_DIR = Path(__file__).resolve().parent
os.chdir(BACKEND_DIR)
sys.path.insert(0, str(BACKEND_DIR))

# Windows + asyncio subprocess fix. Must run before any event loop is created.
# Even with this, uvicorn's reload mode spawns children that end up on
# SelectorEventLoop, which breaks Playwright. For that reason reload defaults
# to OFF on Windows. Set PYSCRAPR_RELOAD=1 to opt-in (and accept the tradeoff).
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

import uvicorn  # noqa: E402

if __name__ == "__main__":
    reload_enabled = os.environ.get("PYSCRAPR_RELOAD", "0") == "1"
    port = int(os.environ.get("PYSCRAPR_PORT", "8000"))

    if reload_enabled and sys.platform == "win32":
        print(
            "[WARN] PYSCRAPR_RELOAD=1 on Windows: Playwright features "
            "(Screenshot, Render with browser) will fail with NotImplementedError. "
            "Disable reload or restart backend manually after code changes.",
            file=sys.stderr,
        )

    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=port,
        reload=reload_enabled,
        reload_dirs=[str(BACKEND_DIR / "app")] if reload_enabled else None,
        log_level="info",
        loop="asyncio",
    )
