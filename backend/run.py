"""Entry point — run with: python run.py"""
import os
import sys
from pathlib import Path

# Ensure backend/ is on sys.path and cwd, regardless of where we're launched from
BACKEND_DIR = Path(__file__).resolve().parent
os.chdir(BACKEND_DIR)
sys.path.insert(0, str(BACKEND_DIR))

import uvicorn  # noqa: E402

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        reload_dirs=[str(BACKEND_DIR / "app")],
        log_level="info",
    )
