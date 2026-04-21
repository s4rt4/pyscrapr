"""Website technology stack detector using Wappalyzer fingerprints.

Rule bundle is sourced from enthec/webappanalyzer (MIT), the actively maintained
fork that replaced the now-closed-source original Wappalyzer. Rules live under
``backend/app/data/wappalyzer/`` and are loaded once at instantiation.

Implemented rule fields:
    url, headers, cookies, html, meta, scriptSrc, scripts (inline HTML scripts),
    implies (with confidence), requires, requiresCategory, excludes.

Skipped rule fields (single HTTP GET cannot evaluate them):
    dom  - needs rendered DOM (Playwright would help but selectors can be
           arbitrarily deep; skipped for perf and scope),
    js   - needs JS runtime (requires evaluating expressions in page context),
    dns  - needs DNS queries,
    css  - needs parsed CSSOM,
    certIssuer - needs TLS chain inspection beyond our httpx flow.
"""
from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import httpx
from bs4 import BeautifulSoup

from app.services.http_factory import build_client

logger = logging.getLogger("pyscrapr.tech_detector")

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "wappalyzer"
TECH_DIR = DATA_DIR / "technologies"


# ─────────────────────────── pattern parsing ───────────────────────────


class _Pattern:
    """Compiled Wappalyzer pattern (regex + optional version/confidence tags)."""

    __slots__ = ("raw", "regex", "version", "confidence")

    def __init__(self, raw: str) -> None:
        self.raw = raw
        parts = raw.split("\\;") if raw else [""]
        body = parts[0]
        version: Optional[str] = None
        confidence: int = 100
        for ext in parts[1:]:
            if ext.startswith("version:"):
                version = ext[len("version:"):]
            elif ext.startswith("confidence:"):
                try:
                    confidence = int(ext[len("confidence:"):])
                except ValueError:
                    pass
        try:
            self.regex: Optional[re.Pattern[str]] = re.compile(body, re.IGNORECASE) if body else None
        except re.error:
            # Some Wappalyzer patterns contain JS regex features we can't use.
            self.regex = None
        self.version = version
        self.confidence = confidence

    def search(self, text: str) -> Optional[re.Match[str]]:
        if self.regex is None or text is None:
            return None
        try:
            return self.regex.search(text)
        except Exception:
            return None

    def extract_version(self, match: re.Match[str]) -> Optional[str]:
        if not self.version or not match:
            return None
        tpl = self.version
        # Wappalyzer version templates:  \1  or  \1?X:Y  (ternary if group matched).
        ternary = re.match(r"^\\(\d+)\?([^:]*):(.*)$", tpl)
        if ternary:
            idx = int(ternary.group(1))
            if_matched = ternary.group(2)
            if_not = ternary.group(3)
            try:
                return if_matched if match.group(idx) else if_not
            except IndexError:
                return if_not
        # Simple \N substitution.
        out = tpl
        for i in range(9, 0, -1):
            token = f"\\{i}"
            if token in out:
                try:
                    grp = match.group(i) or ""
                except IndexError:
                    grp = ""
                out = out.replace(token, grp)
        out = out.strip()
        return out or None


def _as_pattern_list(value: Any) -> list[_Pattern]:
    if value is None:
        return []
    if isinstance(value, str):
        return [_Pattern(value)]
    if isinstance(value, list):
        return [_Pattern(str(v)) for v in value if v is not None]
    # dict or other - caller handles dicts separately
    return []


def _as_pattern_dict(value: Any) -> dict[str, list[_Pattern]]:
    if not isinstance(value, dict):
        return {}
    out: dict[str, list[_Pattern]] = {}
    for k, v in value.items():
        out[str(k).lower()] = _as_pattern_list(v)
    return out


def _as_str_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [str(v) for v in value]
    return []


# ─────────────────────────── detector ───────────────────────────


class TechDetector:
    def __init__(self) -> None:
        self.techs: dict[str, dict[str, Any]] = {}
        self.categories: dict[int, dict[str, Any]] = {}
        self.groups: dict[int, dict[str, Any]] = {}
        self._load_rules()

    # ---- loading ----

    def _load_rules(self) -> None:
        cat_file = DATA_DIR / "categories.json"
        if cat_file.exists():
            try:
                raw = json.loads(cat_file.read_text(encoding="utf-8"))
                for k, v in raw.items():
                    try:
                        self.categories[int(k)] = v
                    except ValueError:
                        continue
            except Exception as e:
                logger.error("Failed to load categories.json: %s", e)

        grp_file = DATA_DIR / "groups.json"
        if grp_file.exists():
            try:
                raw = json.loads(grp_file.read_text(encoding="utf-8"))
                for k, v in raw.items():
                    try:
                        self.groups[int(k)] = v
                    except ValueError:
                        continue
            except Exception as e:
                logger.debug("groups.json not loaded: %s", e)

        if not TECH_DIR.exists():
            logger.warning("Wappalyzer technologies dir missing: %s", TECH_DIR)
            return

        for f in sorted(TECH_DIR.glob("*.json")):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
            except Exception as e:
                logger.warning("Failed to parse %s: %s", f.name, e)
                continue
            for name, rule in data.items():
                if not isinstance(rule, dict):
                    continue
                self.techs[name] = self._compile_rule(rule)

        logger.info(
            "TechDetector loaded: technologies=%d categories=%d",
            len(self.techs),
            len(self.categories),
        )

    def _compile_rule(self, rule: dict[str, Any]) -> dict[str, Any]:
        return {
            "cats": rule.get("cats", []) or [],
            "cpe": rule.get("cpe"),
            "icon": rule.get("icon"),
            "website": rule.get("website"),
            "description": rule.get("description"),
            "url": _as_pattern_list(rule.get("url")),
            "headers": _as_pattern_dict(rule.get("headers")),
            "cookies": _as_pattern_dict(rule.get("cookies")),
            "html": _as_pattern_list(rule.get("html")),
            "meta": _as_pattern_dict(rule.get("meta")),
            "scriptSrc": _as_pattern_list(rule.get("scriptSrc") or rule.get("script")),
            "scripts": _as_pattern_list(rule.get("scripts")),
            "implies": _as_str_list(rule.get("implies")),
            "requires": _as_str_list(rule.get("requires")),
            "requiresCategory": rule.get("requiresCategory") or [],
            "excludes": _as_str_list(rule.get("excludes")),
        }

    # ---- fetch ----

    async def _fetch(
        self,
        url: str,
        timeout: int,
        use_playwright: bool,
    ) -> dict[str, Any]:
        final_url = url
        status_code = 0
        html = ""
        headers: dict[str, str] = {}
        cookies: dict[str, str] = {}

        async with build_client(timeout=timeout, target_url=url) as client:
            try:
                resp = await client.get(url)
                final_url = str(resp.url)
                status_code = resp.status_code
                headers = {k: v for k, v in resp.headers.items()}
                cookies = {c.name: c.value for c in resp.cookies.jar}
                html = resp.text
            except httpx.HTTPError as e:
                logger.warning("httpx fetch failed for %s: %s", url, e)
                raise

        if use_playwright:
            try:
                from app.services.playwright_renderer import get_renderer

                renderer = await get_renderer()
                rendered = await renderer.fetch_html(url)
                if rendered:
                    html = rendered
                    logger.info("Playwright rendered HTML used for %s", url)
            except Exception as e:
                logger.warning("Playwright fallback failed, using httpx HTML: %s", e)

        return {
            "final_url": final_url,
            "status_code": status_code,
            "headers": headers,
            "cookies": cookies,
            "html": html,
        }

    # ---- matching ----

    def _extract_doc_features(self, html: str) -> dict[str, Any]:
        meta: dict[str, str] = {}
        script_srcs: list[str] = []
        inline_scripts: list[str] = []
        try:
            soup = BeautifulSoup(html, "html.parser")
        except Exception:
            return {"meta": meta, "script_srcs": script_srcs, "inline_scripts": inline_scripts}

        for tag in soup.find_all("meta"):
            name = (tag.get("name") or tag.get("property") or tag.get("http-equiv") or "").strip().lower()
            if not name:
                continue
            content = tag.get("content") or ""
            meta[name] = content

        for tag in soup.find_all("script"):
            src = tag.get("src")
            if src:
                script_srcs.append(src)
            elif tag.string:
                inline_scripts.append(tag.string)

        return {"meta": meta, "script_srcs": script_srcs, "inline_scripts": inline_scripts}

    def _match_tech(
        self,
        name: str,
        rule: dict[str, Any],
        ctx: dict[str, Any],
    ) -> Optional[dict[str, Any]]:
        hits: list[str] = []
        best_version: Optional[str] = None
        confidence_sum = 0

        def _apply(pat: _Pattern, target: str, label: str) -> None:
            nonlocal best_version, confidence_sum
            m = pat.search(target)
            if not m:
                return
            hits.append(label)
            confidence_sum += pat.confidence
            v = pat.extract_version(m)
            if v and not best_version:
                best_version = v

        # url
        for pat in rule["url"]:
            _apply(pat, ctx["final_url"], "url")

        # headers (case-insensitive name match; value regex)
        headers_lc = ctx["headers_lc"]
        for hname, pats in rule["headers"].items():
            val = headers_lc.get(hname)
            if val is None:
                continue
            for pat in pats:
                _apply(pat, val, f"header {hname}")
                if pat.regex is None:
                    # empty regex = presence-only
                    hits.append(f"header {hname} present")
                    confidence_sum += pat.confidence

        # cookies
        cookies = ctx["cookies"]
        for cname, pats in rule["cookies"].items():
            # exact cookie name (lower) OR regex-match any cookie name
            matched_val: Optional[str] = None
            for existing_name, existing_val in cookies.items():
                if existing_name.lower() == cname:
                    matched_val = existing_val
                    break
            if matched_val is None:
                # try regex on names
                try:
                    name_rx = re.compile(cname, re.IGNORECASE)
                except re.error:
                    name_rx = None
                if name_rx:
                    for existing_name, existing_val in cookies.items():
                        if name_rx.search(existing_name):
                            matched_val = existing_val
                            break
            if matched_val is None:
                continue
            for pat in pats:
                if pat.regex is None:
                    hits.append(f"cookie {cname}")
                    confidence_sum += pat.confidence
                else:
                    _apply(pat, matched_val, f"cookie {cname}")

        # html body
        html = ctx["html"]
        for pat in rule["html"]:
            _apply(pat, html, "html")

        # meta
        for mname, pats in rule["meta"].items():
            val = ctx["meta"].get(mname)
            if val is None:
                continue
            for pat in pats:
                if pat.regex is None:
                    hits.append(f"meta {mname}")
                    confidence_sum += pat.confidence
                else:
                    _apply(pat, val, f"meta {mname}")

        # scriptSrc
        for pat in rule["scriptSrc"]:
            for src in ctx["script_srcs"]:
                m = pat.search(src)
                if m:
                    hits.append(f"scriptSrc {src[:80]}")
                    confidence_sum += pat.confidence
                    v = pat.extract_version(m)
                    if v and not best_version:
                        best_version = v
                    break

        # inline scripts
        for pat in rule["scripts"]:
            for body in ctx["inline_scripts"]:
                m = pat.search(body)
                if m:
                    hits.append("script inline")
                    confidence_sum += pat.confidence
                    v = pat.extract_version(m)
                    if v and not best_version:
                        best_version = v
                    break

        if not hits:
            return None

        confidence = min(100, confidence_sum)
        return {
            "name": name,
            "version": best_version,
            "confidence": confidence,
            "matched_on": hits,
            "rule": rule,
        }

    # ---- public API ----

    async def detect(
        self,
        url: str,
        timeout: int = 20,
        use_playwright: bool = False,
    ) -> dict[str, Any]:
        fetched = await self._fetch(url, timeout=timeout, use_playwright=use_playwright)

        features = self._extract_doc_features(fetched["html"])
        ctx = {
            "final_url": fetched["final_url"],
            "headers": fetched["headers"],
            "headers_lc": {k.lower(): v for k, v in fetched["headers"].items()},
            "cookies": fetched["cookies"],
            "html": fetched["html"],
            "meta": features["meta"],
            "script_srcs": features["script_srcs"],
            "inline_scripts": features["inline_scripts"],
        }

        matches: dict[str, dict[str, Any]] = {}

        # Pass 1: direct matching
        for tname, rule in self.techs.items():
            hit = self._match_tech(tname, rule, ctx)
            if hit:
                matches[tname] = hit

        # Pass 2: resolve implies (with optional confidence tag)
        def _add_implied(name: str, raw_impl: str, from_name: str) -> None:
            target, conf = raw_impl, 100
            if "\\;" in raw_impl:
                parts = raw_impl.split("\\;")
                target = parts[0]
                for ext in parts[1:]:
                    if ext.startswith("confidence:"):
                        try:
                            conf = int(ext[len("confidence:"):])
                        except ValueError:
                            pass
            rule = self.techs.get(target)
            if rule is None:
                return
            if target in matches:
                matches[target]["confidence"] = min(100, matches[target]["confidence"] + conf // 2)
                matches[target]["matched_on"].append(f"implied by {from_name}")
                return
            matches[target] = {
                "name": target,
                "version": None,
                "confidence": conf,
                "matched_on": [f"implied by {from_name}"],
                "rule": rule,
            }

        # Iterate until no new implied techs
        for _ in range(5):
            before = len(matches)
            for tname in list(matches.keys()):
                rule = matches[tname]["rule"]
                for impl in rule.get("implies", []):
                    _add_implied(tname, impl, tname)
            if len(matches) == before:
                break

        # Pass 3: requires / requiresCategory
        def _matches_category(cat_id: Any) -> bool:
            try:
                cid = int(cat_id)
            except (TypeError, ValueError):
                return False
            for m in matches.values():
                if cid in (m["rule"].get("cats") or []):
                    return True
            return False

        to_drop: list[str] = []
        for tname, m in matches.items():
            rule = m["rule"]
            reqs = rule.get("requires") or []
            if reqs and not all(r in matches for r in reqs):
                to_drop.append(tname)
                continue
            req_cats = rule.get("requiresCategory") or []
            if isinstance(req_cats, (str, int)):
                req_cats = [req_cats]
            if req_cats and not any(_matches_category(c) for c in req_cats):
                to_drop.append(tname)
        for tname in to_drop:
            matches.pop(tname, None)

        # Pass 4: excludes
        to_drop = []
        for tname, m in matches.items():
            for ex in m["rule"].get("excludes", []):
                if ex in matches:
                    to_drop.append(ex)
        for tname in to_drop:
            matches.pop(tname, None)

        # Build response
        tech_list: list[dict[str, Any]] = []
        by_category: dict[str, list[dict[str, Any]]] = {}
        for tname, m in sorted(matches.items(), key=lambda kv: (-kv[1]["confidence"], kv[0])):
            rule = m["rule"]
            cat_names = [
                self.categories.get(int(c), {}).get("name", f"cat_{c}")
                for c in rule.get("cats", []) or []
            ]
            entry = {
                "name": tname,
                "version": m["version"],
                "confidence": m["confidence"],
                "categories": cat_names,
                "icon": rule.get("icon"),
                "website": rule.get("website"),
                "cpe": rule.get("cpe"),
                "matched_on": m["matched_on"][:10],
            }
            tech_list.append(entry)
            for cname in cat_names:
                by_category.setdefault(cname, []).append(entry)

        return {
            "url": url,
            "final_url": fetched["final_url"],
            "status_code": fetched["status_code"],
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "technologies": tech_list,
            "by_category": by_category,
        }


# Process-wide singleton (rules are ~10MB of compiled regex - load once)
_detector: Optional[TechDetector] = None


def get_detector() -> TechDetector:
    global _detector
    if _detector is None:
        _detector = TechDetector()
    return _detector
