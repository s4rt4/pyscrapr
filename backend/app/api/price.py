"""Price Watcher API endpoints — track, monitor, alert on product price changes."""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.models.price_product import PriceProduct
from app.repositories.price_repository import PriceRepository
from app.schemas.price import (
    PriceCheckNowResponse,
    PriceExtractPreviewResponse,
    PriceHistoryDTO,
    PriceProductDTO,
    PriceProductInput,
    PriceProductUpdate,
)
from app.services.price_watcher import extract_preview, run_check

logger = logging.getLogger("pyscrapr.price_watcher")

router = APIRouter()


@router.get("/products", response_model=list[PriceProductDTO])
async def list_products(session: AsyncSession = Depends(get_session)) -> list[PriceProductDTO]:
    repo = PriceRepository(session)
    products = await repo.list_products()
    return [PriceProductDTO.model_validate(p) for p in products]


@router.post("/products", response_model=PriceProductDTO)
async def create_product(
    req: PriceProductInput,
    session: AsyncSession = Depends(get_session),
) -> PriceProductDTO:
    url = req.url.strip()
    if not url:
        raise HTTPException(status_code=400, detail="URL wajib diisi")

    product = PriceProduct(
        id=str(uuid.uuid4()),
        url=url,
        title=req.title or "",
        selector=req.selector or "",
        selector_type=req.selector_type,
        interval_minutes=req.interval_minutes,
        enabled=req.enabled,
        alert_below=req.alert_below,
        alert_above=req.alert_above,
        currency=req.currency,
        last_status="pending",
    )
    repo = PriceRepository(session)
    await repo.create_product(product)
    return PriceProductDTO.model_validate(product)


@router.get("/products/{product_id}", response_model=PriceProductDTO)
async def get_product(
    product_id: str,
    session: AsyncSession = Depends(get_session),
) -> PriceProductDTO:
    repo = PriceRepository(session)
    product = await repo.get_product(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Produk tidak ditemukan")
    return PriceProductDTO.model_validate(product)


@router.put("/products/{product_id}", response_model=PriceProductDTO)
async def update_product(
    product_id: str,
    req: PriceProductUpdate,
    session: AsyncSession = Depends(get_session),
) -> PriceProductDTO:
    repo = PriceRepository(session)
    product = await repo.get_product(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Produk tidak ditemukan")
    updates = {k: v for k, v in req.model_dump(exclude_unset=True).items() if v is not None or k in (
        "alert_below", "alert_above"
    )}
    await repo.update_product(product, **updates)
    return PriceProductDTO.model_validate(product)


@router.delete("/products/{product_id}")
async def delete_product(
    product_id: str,
    session: AsyncSession = Depends(get_session),
) -> dict:
    repo = PriceRepository(session)
    ok = await repo.delete_product(product_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Produk tidak ditemukan")
    return {"ok": True}


@router.post("/products/{product_id}/check-now", response_model=PriceCheckNowResponse)
async def check_now(product_id: str) -> PriceCheckNowResponse:
    """Force an immediate check, bypassing the schedule."""
    try:
        result = await run_check(product_id)
    except Exception as e:
        logger.exception("Manual price check failed for %s: %s", product_id, e)
        raise HTTPException(status_code=500, detail=str(e))
    if not result.get("ok"):
        raise HTTPException(status_code=404, detail=result.get("error", "produk tidak ditemukan"))
    return PriceCheckNowResponse(**result)


@router.get("/products/{product_id}/history", response_model=list[PriceHistoryDTO])
async def get_history(
    product_id: str,
    days: int = Query(default=30, ge=1, le=365),
    session: AsyncSession = Depends(get_session),
) -> list[PriceHistoryDTO]:
    repo = PriceRepository(session)
    product = await repo.get_product(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Produk tidak ditemukan")
    since = datetime.utcnow() - timedelta(days=days)
    history = await repo.list_history(product_id=product_id, since=since, limit=5000)
    return [PriceHistoryDTO.model_validate(h) for h in history]


@router.get("/products/{product_id}/extract-preview", response_model=PriceExtractPreviewResponse)
async def preview_existing(
    product_id: str,
    selector: str | None = Query(default=None),
    selector_type: str | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
) -> PriceExtractPreviewResponse:
    repo = PriceRepository(session)
    product = await repo.get_product(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Produk tidak ditemukan")
    sel = selector if selector is not None else product.selector
    sel_type = selector_type or product.selector_type or "auto"
    result = await extract_preview(product.url, sel, sel_type)
    return PriceExtractPreviewResponse(**result)


@router.get("/extract-preview", response_model=PriceExtractPreviewResponse)
async def preview_url(
    url: str = Query(...),
    selector: str = Query(default=""),
    selector_type: str = Query(default="auto", pattern="^(auto|css|xpath)$"),
) -> PriceExtractPreviewResponse:
    """Test extraction on any URL without creating a product."""
    if not url.strip():
        raise HTTPException(status_code=400, detail="URL wajib diisi")
    result = await extract_preview(url.strip(), selector, selector_type)
    return PriceExtractPreviewResponse(**result)
