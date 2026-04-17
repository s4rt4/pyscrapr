"""Documentation server — reads markdown files from project docs/ folder."""
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import PlainTextResponse

from app.config import settings as app_config

router = APIRouter()

DOCS_ROOT = app_config.base_dir / "docs"


def _safe_resolve(rel_path: str) -> Path:
    """Resolve rel_path within DOCS_ROOT, prevent path traversal."""
    if not DOCS_ROOT.exists():
        raise HTTPException(404, "Docs folder not initialized")
    rel = (rel_path or "").strip().lstrip("/")
    if ".." in rel or rel.startswith("/") or "\\" in rel:
        raise HTTPException(400, "Invalid path")
    target = (DOCS_ROOT / rel).resolve()
    try:
        target.relative_to(DOCS_ROOT.resolve())
    except ValueError:
        raise HTTPException(400, "Path escapes docs root")
    return target


def _build_tree(root: Path, rel: str = "") -> list[dict[str, Any]]:
    """Recursively build doc tree, skipping non-markdown files."""
    out = []
    if not root.exists() or not root.is_dir():
        return out
    for entry in sorted(root.iterdir(), key=lambda e: (not e.is_dir(), e.name.lower())):
        if entry.name.startswith(".") or entry.name == "images":
            continue
        rel_entry = f"{rel}/{entry.name}" if rel else entry.name
        if entry.is_dir():
            children = _build_tree(entry, rel_entry)
            if children:
                out.append({
                    "type": "folder",
                    "name": entry.name,
                    "path": rel_entry,
                    "children": children,
                })
        elif entry.suffix.lower() == ".md":
            # Extract title from first H1
            title = entry.stem.replace("-", " ").replace("_", " ").title()
            try:
                with entry.open("r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith("# "):
                            title = line[2:].strip()
                            break
                        if line:
                            break
            except Exception:
                pass
            out.append({
                "type": "file",
                "name": entry.stem,
                "title": title,
                "path": rel_entry,
            })
    return out


@router.get("/tree")
async def docs_tree():
    """Return the full tree of docs for navigation."""
    return {"root": str(DOCS_ROOT), "tree": _build_tree(DOCS_ROOT)}


@router.get("/content", response_class=PlainTextResponse)
async def docs_content(path: str = Query(description="relative path under docs/")):
    """Return raw markdown content."""
    target = _safe_resolve(path)
    if not target.exists() or not target.is_file():
        raise HTTPException(404, f"Not found: {path}")
    if target.suffix.lower() != ".md":
        raise HTTPException(400, "Only .md files served via this endpoint")
    return target.read_text(encoding="utf-8")


@router.get("/search")
async def docs_search(q: str = Query(min_length=2)):
    """Simple full-text search across all markdown files."""
    results = []
    query_low = q.lower()
    if not DOCS_ROOT.exists():
        return {"results": []}
    for md in DOCS_ROOT.rglob("*.md"):
        try:
            text = md.read_text(encoding="utf-8")
            if query_low in text.lower():
                rel = md.relative_to(DOCS_ROOT).as_posix()
                # First line = title
                title = rel
                for line in text.splitlines():
                    line = line.strip()
                    if line.startswith("# "):
                        title = line[2:].strip()
                        break
                # Extract 200-char context around first match
                idx = text.lower().find(query_low)
                start = max(0, idx - 80)
                end = min(len(text), idx + 120)
                snippet = text[start:end].replace("\n", " ").strip()
                results.append({"path": rel, "title": title, "snippet": snippet})
        except Exception:
            pass
    return {"results": results[:30]}


@router.get("/image/{path:path}")
async def docs_image(path: str):
    """Serve image files from docs/images/."""
    from fastapi.responses import FileResponse
    target = _safe_resolve(f"images/{path}") if not path.startswith("images/") else _safe_resolve(path)
    if not target.exists() or not target.is_file():
        raise HTTPException(404, "Image not found")
    return FileResponse(str(target))
