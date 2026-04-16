"""Selector Sandbox — fetch a URL's HTML, then test CSS/XPath selectors live."""
import asyncio
from typing import Optional

import certifi
import httpx
from bs4 import BeautifulSoup
from fastapi import APIRouter, HTTPException
from lxml import etree
from pydantic import BaseModel

router = APIRouter()


class FetchRequest(BaseModel):
    url: str


class SelectorRequest(BaseModel):
    html: str
    selector: str
    mode: str = "css"  # "css" or "xpath"


class MatchedElement(BaseModel):
    tag: str
    text: str
    html: str
    attributes: dict[str, str]


@router.post("/fetch")
async def fetch_page(req: FetchRequest):
    """Fetch a URL and return its raw HTML."""
    try:
        async with httpx.AsyncClient(
            timeout=20,
            verify=certifi.where(),
            follow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
        ) as client:
            r = await client.get(req.url)
            r.raise_for_status()
            return {
                "html": r.text,
                "status_code": r.status_code,
                "content_type": r.headers.get("content-type", ""),
                "size": len(r.text),
            }
    except Exception as e:
        raise HTTPException(400, f"Fetch failed: {e}")


@router.post("/test-selector", response_model=list[MatchedElement])
async def test_selector(req: SelectorRequest):
    """Test a CSS or XPath selector against provided HTML."""

    def _run():
        results: list[MatchedElement] = []
        if req.mode == "css":
            soup = BeautifulSoup(req.html, "lxml")
            try:
                elements = soup.select(req.selector)
            except Exception as e:
                raise HTTPException(400, f"Invalid CSS selector: {e}")
            for el in elements[:200]:
                results.append(MatchedElement(
                    tag=el.name or "",
                    text=el.get_text(strip=True)[:300],
                    html=str(el)[:500],
                    attributes={k: str(v) for k, v in (el.attrs or {}).items()},
                ))
        elif req.mode == "xpath":
            try:
                tree = etree.HTML(req.html)
                elements = tree.xpath(req.selector)
            except Exception as e:
                raise HTTPException(400, f"Invalid XPath: {e}")
            for el in elements[:200]:
                if isinstance(el, etree._Element):
                    text = (el.text or "") + "".join(
                        etree.tostring(c, encoding="unicode", method="text") for c in el
                    )
                    results.append(MatchedElement(
                        tag=el.tag or "",
                        text=text.strip()[:300],
                        html=etree.tostring(el, encoding="unicode")[:500],
                        attributes=dict(el.attrib),
                    ))
                elif isinstance(el, str):
                    results.append(MatchedElement(
                        tag="text()",
                        text=el[:300],
                        html=el[:500],
                        attributes={},
                    ))
        else:
            raise HTTPException(400, f"Unknown mode: {req.mode}")
        return results

    return await asyncio.to_thread(_run)
