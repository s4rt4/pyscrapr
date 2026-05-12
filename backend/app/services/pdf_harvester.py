"""PDF Harvester service.

Crawls a target site BFS, discovers PDF links, downloads them, extracts
metadata + first-page preview + truncated full text for searching.

In-memory BFS (no crawl_node persistence) — analog to OSINTHarvester.
"""
from __future__ import annotations

import asyncio
import datetime as _dt
import hashlib
import logging
import os
import re
from pathlib import Path
from typing import Optional
from urllib.parse import unquote, urlparse

from app.services.event_bus import event_bus
from app.services.http_factory import build_client
from app.services.link_extractor import extract as extract_metadata
from app.services.pdf_search_index import get_index
from app.services.url_normalizer import normalize_url, same_domain

logger = logging.getLogger("pyscrapr.pdf_harvester")

_PDF_HREF_RE = re.compile(r"\.pdf(\?|#|$)", re.IGNORECASE)
_SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9._-]+")
_PREVIEW_CHARS = 500
_TEXT_INDEX_CHARS = 5000

DATA_DIR = Path(os.environ.get("PYSCRAPR_DATA_DIR", "data")) / "pdf_harvester"


def _now_iso() -> str:
    return _dt.datetime.now(tz=_dt.timezone.utc).isoformat()


def _sanitize_filename(url: str) -> str:
    try:
        parsed = urlparse(url)
        name = os.path.basename(unquote(parsed.path)) or "document.pdf"
    except Exception:
        name = "document.pdf"
    name = _SAFE_NAME_RE.sub("_", name)
    if not name.lower().endswith(".pdf"):
        name += ".pdf"
    if len(name) > 120:
        name = name[:100] + "_" + hashlib.md5(url.encode()).hexdigest()[:8] + ".pdf"
    return name


def _pdf_id(url: str) -> str:
    return hashlib.sha1(url.encode("utf-8")).hexdigest()[:16]


def _looks_like_pdf_url(url: str) -> bool:
    return bool(_PDF_HREF_RE.search(url))


async def _is_pdf_via_head(client, url: str) -> bool:
    try:
        r = await client.head(url, follow_redirects=True)
        ctype = (r.headers.get("content-type") or "").lower()
        return "application/pdf" in ctype
    except Exception:
        return False


def _extract_pdf_metadata(path: Path, *, extract_text: bool) -> dict:
    """Open PDF via PyMuPDF, extract metadata + previews. Closes doc."""
    try:
        import fitz  # type: ignore
    except Exception as e:
        logger.warning("pymupdf not available: %s", e)
        return {"error": "pymupdf not available"}

    out: dict = {}
    try:
        doc = fitz.open(path)
    except Exception as e:
        return {"error": f"open failed: {e}"}
    try:
        meta = dict(doc.metadata or {})
        out.update({
            "title": (meta.get("title") or None),
            "author": (meta.get("author") or None),
            "subject": (meta.get("subject") or None),
            "keywords": (meta.get("keywords") or None),
            "creator": (meta.get("creator") or None),
            "producer": (meta.get("producer") or None),
            "creation_date": (meta.get("creationDate") or None),
            "mod_date": (meta.get("modDate") or None),
            "page_count": doc.page_count,
        })
        if extract_text and doc.page_count > 0:
            try:
                first_text = doc.load_page(0).get_text("text") or ""
                out["preview_text"] = first_text.strip()[:_PREVIEW_CHARS]
            except Exception as e:
                logger.debug("preview text failed: %s", e)
            try:
                buf = []
                acc = 0
                for i in range(min(doc.page_count, 20)):
                    try:
                        t = doc.load_page(i).get_text("text") or ""
                    except Exception:
                        continue
                    buf.append(t)
                    acc += len(t)
                    if acc >= _TEXT_INDEX_CHARS:
                        break
                full = "\n".join(buf)
                out["text_content"] = full[:_TEXT_INDEX_CHARS]
            except Exception as e:
                logger.debug("full text failed: %s", e)
    finally:
        try:
            doc.close()
        except Exception:
            pass
    # Strip None values for cleanliness
    return {k: v for k, v in out.items() if v is not None}


class PdfHarvester:
    async def harvest(
        self,
        url: str,
        *,
        job_id: Optional[str] = None,
        max_depth: int = 2,
        max_pages: int = 50,
        max_pdfs: int = 100,
        download: bool = True,
        extract_text: bool = True,
    ) -> dict:
        jid = job_id or "ad-hoc"
        start_url = normalize_url(url, strip_tracking=True)
        started_at = _now_iso()
        seen_pages: set[str] = set()
        seen_pdfs: dict[str, dict] = {}  # url -> doc dict
        pages_crawled = 0

        await event_bus.publish(jid, {"type": "status", "status": "running"})

        job_dir = DATA_DIR / jid
        if download:
            job_dir.mkdir(parents=True, exist_ok=True)

        host_rate_lock = asyncio.Lock()
        last_request_ts: dict[str, float] = {}

        async def throttle(target_url: str) -> None:
            host = urlparse(target_url).netloc
            async with host_rate_lock:
                loop = asyncio.get_event_loop()
                now = loop.time()
                prev = last_request_ts.get(host, 0.0)
                wait = 1.0 - (now - prev)
                if wait > 0:
                    await asyncio.sleep(wait)
                last_request_ts[host] = asyncio.get_event_loop().time()

        try:
            async with build_client(target_url=start_url, timeout=30) as client:
                # Phase 1: BFS crawl
                frontier: list[tuple[str, int, Optional[str]]] = [(start_url, 0, None)]
                while frontier and pages_crawled < max_pages and len(seen_pdfs) < max_pdfs:
                    cur_url, depth, parent = frontier.pop(0)
                    if cur_url in seen_pages:
                        continue
                    seen_pages.add(cur_url)
                    if not same_domain(cur_url, start_url):
                        continue

                    await throttle(cur_url)
                    await event_bus.publish(jid, {
                        "type": "log", "message": f"Crawl: {cur_url}",
                    })

                    html = ""
                    try:
                        r = await client.get(cur_url, follow_redirects=True)
                        ctype = (r.headers.get("content-type") or "").lower()
                        if "html" in ctype and 200 <= r.status_code < 300:
                            html = r.text
                        elif "application/pdf" in ctype and 200 <= r.status_code < 300:
                            # The seed itself is a PDF.
                            if cur_url not in seen_pdfs and len(seen_pdfs) < max_pdfs:
                                seen_pdfs[cur_url] = {
                                    "pdf_id": _pdf_id(cur_url),
                                    "url": cur_url,
                                    "filename": _sanitize_filename(cur_url),
                                    "discovered_from": parent,
                                }
                            continue
                    except Exception as e:
                        await event_bus.publish(jid, {
                            "type": "log", "message": f"Fetch error {cur_url}: {e}",
                        })
                        continue

                    pages_crawled += 1
                    if not html:
                        continue

                    # Extract links
                    try:
                        meta = extract_metadata(html, cur_url)
                        child_links = meta.links
                    except Exception:
                        child_links = []

                    pdf_candidates: list[str] = []
                    non_pdf_links: list[str] = []
                    for raw in child_links:
                        norm = normalize_url(raw, strip_tracking=True)
                        if not norm:
                            continue
                        if _looks_like_pdf_url(norm):
                            pdf_candidates.append(norm)
                        else:
                            non_pdf_links.append(norm)

                    # Register PDF candidates by extension
                    for purl in pdf_candidates:
                        if purl in seen_pdfs:
                            continue
                        if len(seen_pdfs) >= max_pdfs:
                            break
                        if not same_domain(purl, start_url):
                            # We still allow off-domain PDFs (common pattern), but skip to keep tight
                            continue
                        seen_pdfs[purl] = {
                            "pdf_id": _pdf_id(purl),
                            "url": purl,
                            "filename": _sanitize_filename(purl),
                            "discovered_from": cur_url,
                        }

                    await event_bus.publish(jid, {
                        "type": "progress",
                        "pages_crawled": pages_crawled,
                        "pdfs_found": len(seen_pdfs),
                        "pdfs_downloaded": 0,
                    })

                    # Enqueue children up to depth
                    if depth + 1 <= max_depth:
                        for nurl in non_pdf_links:
                            if nurl in seen_pages:
                                continue
                            if not same_domain(nurl, start_url):
                                continue
                            frontier.append((nurl, depth + 1, cur_url))

                # Phase 2: download + analyze
                pdfs_downloaded = 0
                total_size = 0
                sem = asyncio.Semaphore(3)
                index = get_index()

                async def process_pdf(doc: dict) -> None:
                    nonlocal pdfs_downloaded, total_size
                    async with sem:
                        purl = doc["url"]
                        await throttle(purl)
                        if not download:
                            return
                        try:
                            r = await client.get(purl, follow_redirects=True)
                            ctype = (r.headers.get("content-type") or "").lower()
                            if r.status_code >= 400:
                                doc["error"] = f"HTTP {r.status_code}"
                                return
                            if "application/pdf" not in ctype and not _looks_like_pdf_url(purl):
                                # Final verification: peek at magic
                                if not r.content.startswith(b"%PDF"):
                                    doc["error"] = f"Not a PDF (ctype={ctype})"
                                    return
                            local_path = job_dir / doc["filename"]
                            # Ensure uniqueness
                            if local_path.exists():
                                local_path = job_dir / f"{doc['pdf_id']}_{doc['filename']}"
                            local_path.write_bytes(r.content)
                            doc["local_path"] = str(local_path)
                            doc["file_size"] = local_path.stat().st_size
                            doc["downloaded"] = True
                            pdfs_downloaded += 1
                            total_size += doc["file_size"]
                            if extract_text:
                                meta = _extract_pdf_metadata(local_path, extract_text=True)
                                if "error" in meta:
                                    doc["error"] = meta["error"]
                                else:
                                    for k, v in meta.items():
                                        doc[k] = v
                                    # Add to search index
                                    if doc.get("text_content"):
                                        index.add(jid, doc["pdf_id"], doc["text_content"])
                            await event_bus.publish(jid, {
                                "type": "progress",
                                "pages_crawled": pages_crawled,
                                "pdfs_found": len(seen_pdfs),
                                "pdfs_downloaded": pdfs_downloaded,
                            })
                        except Exception as e:
                            doc["error"] = f"download failed: {e}"
                            logger.debug("download failed for %s: %s", purl, e)

                if download and seen_pdfs:
                    await asyncio.gather(*(process_pdf(d) for d in seen_pdfs.values()))

        except Exception as e:
            logger.exception("PDF harvest failed: %s", e)
            await event_bus.publish(jid, {"type": "error", "message": str(e)})
            raise

        # Stats
        documents = list(seen_pdfs.values())
        unique_authors = len({d.get("author") for d in documents if d.get("author")})
        stats = {
            "pages_crawled": pages_crawled,
            "pdfs_found": len(documents),
            "pdfs_downloaded": sum(1 for d in documents if d.get("downloaded")),
            "total_size": sum(int(d.get("file_size") or 0) for d in documents),
            "unique_authors": unique_authors,
        }
        report = {
            "job_id": jid,
            "url": start_url,
            "started_at": started_at,
            "finished_at": _now_iso(),
            "pages_crawled": pages_crawled,
            "pdfs_found": stats["pdfs_found"],
            "pdfs_downloaded": stats["pdfs_downloaded"],
            "total_size": stats["total_size"],
            "documents": documents,
            "stats": stats,
        }
        await event_bus.publish(jid, {"type": "done", "stats": stats})
        return report


_harvester: Optional[PdfHarvester] = None


def get_harvester() -> PdfHarvester:
    global _harvester
    if _harvester is None:
        _harvester = PdfHarvester()
    return _harvester


async def harvest(
    url: str,
    *,
    job_id: Optional[str] = None,
    max_depth: int = 2,
    max_pages: int = 50,
    max_pdfs: int = 100,
    download: bool = True,
    extract_text: bool = True,
) -> dict:
    """Module-level convenience wrapper used by verification + ad-hoc callers."""
    return await get_harvester().harvest(
        url,
        job_id=job_id,
        max_depth=max_depth,
        max_pages=max_pages,
        max_pdfs=max_pdfs,
        download=download,
        extract_text=extract_text,
    )
