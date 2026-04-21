"""Entry point - run with: python run.py"""
import asyncio
import os
import sys
from pathlib import Path

# Ensure backend/ is on sys.path and cwd, regardless of where we're launched from
BACKEND_DIR = Path(__file__).resolve().parent
os.chdir(BACKEND_DIR)
sys.path.insert(0, str(BACKEND_DIR))

# Windows + asyncio subprocess fix.
# Uvicorn's reload mode uses SelectorEventLoop on Windows which does NOT
# support subprocess spawning. Playwright needs to spawn Chromium via
# subprocess, so we force ProactorEventLoopPolicy before uvicorn picks one.
# Without this, Playwright calls raise NotImplementedError on Windows.
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

import uvicorn  # noqa: E402

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        reload_dirs=[str(BACKEND_DIR / "app")],
        log_level="info",
        loop="asyncio",
    )
