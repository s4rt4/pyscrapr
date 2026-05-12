"""API Sniffer (P12) — reverse engineer REST/GraphQL endpoints from a SPA target.

Launches Playwright Chromium with stealth applied, intercepts every fetch/XHR
request during page lifecycle, then groups them into endpoint summaries plus
GraphQL operation list. Generates OpenAPI 3.0 and Postman v2.1 collection.

Lazy import Playwright so the module imports cleanly without it installed.
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

logger = logging.getLogger("pyscrapr.api_sniffer")

_INSTALL_HINT = (
    "Playwright belum terpasang. Jalankan dua perintah berurutan: "
    "pip install playwright ; lalu: python -m playwright install chromium"
)

_BODY_SAMPLE_MAX = 10 * 1024  # 10 KB
_SENSITIVE_HEADERS = {
    "cookie",
    "authorization",
    "x-api-key",
    "x-auth-token",
    "x-csrf-token",
    "proxy-authorization",
}
_STATIC_EXTENSIONS = (
    ".js", ".css", ".png", ".jpg", ".jpeg", ".gif", ".svg",
    ".woff", ".woff2", ".ttf", ".eot", ".ico", ".webp", ".bmp",
    ".mp4", ".mp3", ".wav", ".ogg", ".webm", ".map",
)
_STATIC_RESOURCE_TYPES = {
    "image", "stylesheet", "font", "media", "manifest", "other",
}


def _sanitize_headers(headers: dict[str, str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for k, v in (headers or {}).items():
        if k.lower() in _SENSITIVE_HEADERS:
            out[k] = "***"
        else:
            out[k] = v
    return out


def _truncate(body: str | bytes | None) -> tuple[str | None, Any]:
    """Return (truncated_text, parsed_json_or_None)."""
    if body is None:
        return None, None
    if isinstance(body, bytes):
        try:
            text = body.decode("utf-8", errors="replace")
        except Exception:
            return f"<binary {len(body)} bytes>", None
    else:
        text = body
    if not text:
        return "", None
    parsed: Any = None
    stripped = text.lstrip()
    if stripped.startswith("{") or stripped.startswith("["):
        try:
            parsed = json.loads(text)
        except Exception:
            parsed = None
    if len(text) > _BODY_SAMPLE_MAX:
        text = text[:_BODY_SAMPLE_MAX] + f"\n...[truncated, original {len(text)} bytes]"
    return text, parsed


def _is_static_asset(url: str, resource_type: str | None) -> bool:
    if resource_type and resource_type.lower() in _STATIC_RESOURCE_TYPES:
        return True
    path = urlparse(url).path.lower()
    return any(path.endswith(ext) for ext in _STATIC_EXTENSIONS)


def _is_graphql(url: str, body_json: Any) -> tuple[bool, str | None]:
    """Return (is_graphql, operation_name)."""
    path = urlparse(url).path.lower()
    by_path = path.endswith("/graphql") or "/graphql" in path
    op: str | None = None
    has_query = False
    if isinstance(body_json, dict):
        if "query" in body_json and isinstance(body_json.get("query"), str):
            has_query = True
        if isinstance(body_json.get("operationName"), str):
            op = body_json["operationName"]
    elif isinstance(body_json, list) and body_json:
        # GraphQL batch
        first = body_json[0]
        if isinstance(first, dict) and "query" in first:
            has_query = True
            if isinstance(first.get("operationName"), str):
                op = first["operationName"]
    return (by_path or has_query), op


async def _launch_browser(use_stealth: bool):
    try:
        from playwright.async_api import async_playwright  # type: ignore
    except ImportError as exc:
        logger.error("Playwright import gagal: %s", exc)
        raise RuntimeError(_INSTALL_HINT) from exc

    args: list[str] = []
    if use_stealth:
        try:
            from app.services.playwright_stealth_helper import stealth_launch_args
            args = stealth_launch_args()
        except Exception as exc:
            logger.debug("stealth_launch_args gagal: %s", exc)

    pw = await async_playwright().start()
    try:
        browser = await pw.chromium.launch(headless=True, args=args)
    except Exception as exc:
        msg = str(exc).lower()
        if "executable doesn't exist" in msg or "playwright install" in msg:
            await pw.stop()
            raise RuntimeError(_INSTALL_HINT) from exc
        await pw.stop()
        raise
    return pw, browser


async def sniff(
    url: str,
    *,
    wait_seconds: int = 15,
    max_requests: int = 200,
    filter_static: bool = True,
    use_stealth: bool = True,
) -> dict[str, Any]:
    """Intercept network traffic of a SPA target. Returns SniffReport-like dict."""
    started_wall = datetime.now(timezone.utc)
    started_perf = time.perf_counter()

    pw, browser = await _launch_browser(use_stealth)

    # Tracking state
    requests_by_id: dict[str, dict[str, Any]] = {}
    captured: list[dict[str, Any]] = []
    last_activity = time.monotonic()
    idle_threshold = 2.0  # seconds of network silence to call it done

    try:
        context = await browser.new_context()
        page = await context.new_page()

        if use_stealth:
            try:
                from app.services.playwright_stealth_helper import apply_stealth_to_page
                await apply_stealth_to_page(page)
            except Exception as exc:
                logger.debug("apply_stealth_to_page gagal: %s", exc)

        def on_request(req: Any) -> None:
            nonlocal last_activity
            try:
                if len(captured) >= max_requests:
                    return
                r_url = req.url
                if r_url.startswith("data:") or r_url.startswith("blob:"):
                    return
                r_type = getattr(req, "resource_type", None) or ""
                if filter_static and _is_static_asset(r_url, r_type):
                    return

                parsed = urlparse(r_url)
                req_body_raw: str | None = None
                try:
                    pd = req.post_data
                    if pd is not None:
                        req_body_raw = pd
                except Exception:
                    req_body_raw = None

                req_body_text, req_body_json = _truncate(req_body_raw)
                is_gql, op_name = _is_graphql(r_url, req_body_json)

                req_headers: dict[str, str] = {}
                try:
                    req_headers = dict(req.headers) if req.headers else {}
                except Exception:
                    req_headers = {}

                entry: dict[str, Any] = {
                    "request_id": str(uuid.uuid4()),
                    "method": req.method.upper(),
                    "url": f"{parsed.scheme}://{parsed.netloc}{parsed.path}",
                    "full_url": r_url,
                    "host": parsed.netloc,
                    "path": parsed.path or "/",
                    "resource_type": r_type or None,
                    "request_headers": req_headers,
                    "request_body": req_body_text,
                    "request_body_json": req_body_json,
                    "status": None,
                    "response_content_type": None,
                    "response_body": None,
                    "response_body_json": None,
                    "response_size_bytes": 0,
                    "started_at": time.time(),
                    "duration_ms": None,
                    "is_graphql": is_gql,
                    "graphql_operation": op_name,
                    "_perf_start": time.perf_counter(),
                }
                requests_by_id[id(req)] = entry
                captured.append(entry)
                last_activity = time.monotonic()
            except Exception as exc:
                logger.debug("on_request handler gagal: %s", exc)

        async def on_response(resp: Any) -> None:
            nonlocal last_activity
            try:
                req = resp.request
                entry = requests_by_id.get(id(req))
                if entry is None:
                    return
                entry["status"] = resp.status
                try:
                    headers = dict(resp.headers) if resp.headers else {}
                    entry["response_content_type"] = headers.get("content-type")
                except Exception:
                    pass
                try:
                    body = await resp.body()
                    entry["response_size_bytes"] = len(body)
                    text, parsed_json = _truncate(body)
                    entry["response_body"] = text
                    entry["response_body_json"] = parsed_json
                except Exception as exc:
                    logger.debug("read response body gagal: %s", exc)
                entry["duration_ms"] = (time.perf_counter() - entry["_perf_start"]) * 1000.0
                last_activity = time.monotonic()
            except Exception as exc:
                logger.debug("on_response handler gagal: %s", exc)

        page.on("request", on_request)
        page.on("response", lambda r: asyncio.create_task(on_response(r)))

        # Navigate. Use a relatively short timeout for goto but allow long idle wait.
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        except Exception as exc:
            logger.warning("page.goto gagal (lanjut tetap menangkap traffic): %s", exc)

        # Idle / hard timeout loop
        hard_deadline = time.monotonic() + wait_seconds
        last_activity = time.monotonic()
        while True:
            now = time.monotonic()
            if now >= hard_deadline:
                break
            if (now - last_activity) >= idle_threshold and len(captured) > 0:
                break
            if len(captured) >= max_requests:
                break
            await asyncio.sleep(0.25)

        final_url = page.url

    finally:
        try:
            await browser.close()
        except Exception as exc:
            logger.warning("Close browser error: %s", exc)
        try:
            await pw.stop()
        except Exception as exc:
            logger.warning("Stop playwright error: %s", exc)

    # Clean private fields
    for e in captured:
        e.pop("_perf_start", None)

    finished_wall = datetime.now(timezone.utc)
    duration_seconds = time.perf_counter() - started_perf

    endpoints = _group_endpoints(captured)
    graphql_ops = _group_graphql(captured)
    stats = _compute_stats(captured, endpoints, graphql_ops)

    # Sanitize headers for display copies (keep raw for export-only path
    # by stashing originals separately if needed; here we sanitize in place since
    # the export builder reads from the same list — Postman export keeps the value
    # because we never overwrite the request_headers during the loop above… but
    # to honor "sanitize for display, keep for export", we expose both).
    display_requests = []
    for e in captured:
        d = dict(e)
        d["request_headers"] = _sanitize_headers(d.get("request_headers") or {})
        display_requests.append(d)

    report = {
        "url": url,
        "final_url": final_url,
        "started_at": started_wall.isoformat(),
        "finished_at": finished_wall.isoformat(),
        "duration_seconds": round(duration_seconds, 3),
        "stats": stats,
        "endpoints": endpoints,
        "graphql_ops": graphql_ops,
        "requests": display_requests,
        # raw kept for export-only use (not exposed in API responses directly)
        "_raw_requests": captured,
    }
    return report


def _group_endpoints(captured: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str, str], dict[str, Any]] = {}
    for e in captured:
        key = (e["host"], e["method"], e["path"])
        g = groups.get(key)
        if g is None:
            g = {
                "host": e["host"],
                "method": e["method"],
                "path": e["path"],
                "count": 0,
                "statuses": {},
                "content_types": {},
                "sample_request": None,
                "is_graphql": False,
            }
            groups[key] = g
        g["count"] += 1
        if e.get("status") is not None:
            sk = str(e["status"])
            g["statuses"][sk] = g["statuses"].get(sk, 0) + 1
        ct = e.get("response_content_type") or "unknown"
        # Normalize content-type to base only
        base_ct = ct.split(";")[0].strip().lower() if ct else "unknown"
        g["content_types"][base_ct] = g["content_types"].get(base_ct, 0) + 1
        if g["sample_request"] is None:
            sample = dict(e)
            sample["request_headers"] = _sanitize_headers(sample.get("request_headers") or {})
            g["sample_request"] = sample
        if e.get("is_graphql"):
            g["is_graphql"] = True
    return list(groups.values())


def _group_graphql(captured: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ops: dict[str, dict[str, Any]] = {}
    for e in captured:
        if not e.get("is_graphql"):
            continue
        body = e.get("request_body_json")
        bodies = body if isinstance(body, list) else [body]
        for b in bodies:
            if not isinstance(b, dict):
                continue
            op_name = b.get("operationName") or "anonymous"
            query = b.get("query") if isinstance(b.get("query"), str) else None
            variables = b.get("variables")
            op_type = None
            if query:
                stripped = query.lstrip()
                first_word = stripped.split(maxsplit=1)[0].lower() if stripped else ""
                if first_word in ("query", "mutation", "subscription"):
                    op_type = first_word
                else:
                    op_type = "query"
            g = ops.get(op_name)
            if g is None:
                g = {
                    "operation_name": op_name,
                    "operation_type": op_type,
                    "query": query,
                    "variables": variables,
                    "response_sample": e.get("response_body_json") or e.get("response_body"),
                    "count": 0,
                    "host": e["host"],
                    "path": e["path"],
                }
                ops[op_name] = g
            g["count"] += 1
    return list(ops.values())


def _compute_stats(
    captured: list[dict[str, Any]],
    endpoints: list[dict[str, Any]],
    graphql_ops: list[dict[str, Any]],
) -> dict[str, Any]:
    ct_breakdown: dict[str, int] = {}
    status_breakdown: dict[str, int] = {}
    total_bytes = 0
    for e in captured:
        ct = e.get("response_content_type") or "unknown"
        base_ct = ct.split(";")[0].strip().lower() if ct else "unknown"
        ct_breakdown[base_ct] = ct_breakdown.get(base_ct, 0) + 1
        if e.get("status") is not None:
            sk = str(e["status"])
            status_breakdown[sk] = status_breakdown.get(sk, 0) + 1
        total_bytes += int(e.get("response_size_bytes") or 0)
    return {
        "total_requests": len(captured),
        "unique_endpoints": len(endpoints),
        "graphql_ops": len(graphql_ops),
        "content_type_breakdown": ct_breakdown,
        "status_breakdown": status_breakdown,
        "total_response_bytes": total_bytes,
    }


# --- Export builders ---

def build_openapi(report: dict[str, Any]) -> dict[str, Any]:
    """Best-effort OpenAPI 3.0 spec from captured endpoints.

    No deep schema inference. Each path gets one operation per method, with the
    sample response body as `example`. Path parameters are NOT inferred.
    """
    parsed = urlparse(report.get("final_url") or report.get("url") or "")
    base_url = f"{parsed.scheme}://{parsed.netloc}" if parsed.scheme else ""
    spec: dict[str, Any] = {
        "openapi": "3.0.3",
        "info": {
            "title": f"API discovered from {parsed.netloc or 'target'}",
            "description": "Auto-generated by PyScrapr API Sniffer. Refine manually.",
            "version": "0.1.0",
        },
        "servers": [{"url": base_url}] if base_url else [],
        "paths": {},
    }
    by_host_path: dict[tuple[str, str], dict[str, dict[str, Any]]] = {}
    for ep in report.get("endpoints", []):
        host = ep["host"]
        path = ep["path"] or "/"
        method = ep["method"].lower()
        if method not in ("get", "post", "put", "patch", "delete", "head", "options"):
            continue
        key = (host, path)
        if key not in by_host_path:
            by_host_path[key] = {}
        sample = ep.get("sample_request") or {}
        op: dict[str, Any] = {
            "summary": f"{method.upper()} {path}",
            "tags": [host],
            "responses": {},
        }
        # Request body
        if sample.get("request_body_json") is not None:
            op["requestBody"] = {
                "content": {
                    "application/json": {
                        "example": sample["request_body_json"],
                    }
                }
            }
        elif sample.get("request_body"):
            op["requestBody"] = {
                "content": {
                    "text/plain": {"example": sample["request_body"]}
                }
            }
        # Response
        status = str(sample.get("status") or "200")
        ct = (sample.get("response_content_type") or "application/json").split(";")[0].strip()
        resp_example: Any
        if sample.get("response_body_json") is not None:
            resp_example = sample["response_body_json"]
        else:
            resp_example = sample.get("response_body") or ""
        op["responses"][status] = {
            "description": f"Sample {status} response",
            "content": {
                ct or "application/json": {"example": resp_example}
            },
        }
        by_host_path[key][method] = op

    for (host, path), methods in by_host_path.items():
        spec["paths"][path] = methods
    return spec


def build_postman(report: dict[str, Any]) -> dict[str, Any]:
    """Postman Collection v2.1 JSON.

    Uses the raw (un-sanitized) headers when available so the user can replay
    requests including their auth headers.
    """
    parsed = urlparse(report.get("final_url") or report.get("url") or "")
    raw_requests = report.get("_raw_requests") or report.get("requests") or []
    collection: dict[str, Any] = {
        "info": {
            "name": f"PyScrapr Sniff: {parsed.netloc or 'target'}",
            "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
            "description": "Auto-generated by PyScrapr API Sniffer.",
        },
        "item": [],
    }
    folders: dict[str, dict[str, Any]] = {}
    for e in raw_requests:
        host = e.get("host") or "unknown"
        folder = folders.get(host)
        if folder is None:
            folder = {"name": host, "item": []}
            folders[host] = folder
            collection["item"].append(folder)
        u = urlparse(e.get("full_url") or e.get("url") or "")
        headers_list = []
        for k, v in (e.get("request_headers") or {}).items():
            headers_list.append({"key": k, "value": str(v)})
        body_def: dict[str, Any] | None = None
        if e.get("request_body"):
            body_def = {
                "mode": "raw",
                "raw": e["request_body"],
                "options": {"raw": {"language": "json"}}
                if e.get("request_body_json") is not None
                else {"raw": {"language": "text"}},
            }
        path_parts = [p for p in (u.path or "/").split("/") if p]
        item: dict[str, Any] = {
            "name": f"{e.get('method', 'GET')} {u.path or '/'}",
            "request": {
                "method": e.get("method", "GET"),
                "header": headers_list,
                "url": {
                    "raw": e.get("full_url"),
                    "protocol": u.scheme,
                    "host": u.netloc.split(".") if u.netloc else [],
                    "path": path_parts,
                    "query": [
                        {"key": k, "value": v}
                        for k, v in _parse_query(u.query)
                    ],
                },
            },
        }
        if body_def:
            item["request"]["body"] = body_def
        if e.get("response_body") is not None:
            item["response"] = [
                {
                    "name": "Captured",
                    "status": "OK",
                    "code": e.get("status") or 0,
                    "_postman_previewlanguage": (
                        "json" if e.get("response_body_json") is not None else "text"
                    ),
                    "header": [
                        {"key": "Content-Type", "value": e.get("response_content_type") or ""},
                    ],
                    "body": e.get("response_body") or "",
                }
            ]
        folder["item"].append(item)
    return collection


def _parse_query(qs: str) -> list[tuple[str, str]]:
    if not qs:
        return []
    pairs: list[tuple[str, str]] = []
    for part in qs.split("&"):
        if not part:
            continue
        if "=" in part:
            k, v = part.split("=", 1)
        else:
            k, v = part, ""
        pairs.append((k, v))
    return pairs


def strip_raw_for_storage(report: dict[str, Any]) -> dict[str, Any]:
    """Return a copy without `_raw_requests` (for DB stats blob)."""
    out = dict(report)
    out.pop("_raw_requests", None)
    return out
