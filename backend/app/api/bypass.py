"""Link Bypass endpoints — resolve shortened URLs and ad-gateways."""
from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.services.link_bypass import bypass_batch, bypass_single

router = APIRouter()


class BypassSingleRequest(BaseModel):
    url: str


class BypassBatchRequest(BaseModel):
    urls: list[str] = Field(min_length=1, max_length=200)


@router.post("/single")
async def resolve_single(req: BypassSingleRequest):
    result = await bypass_single(req.url)
    return {
        "original": result.original,
        "final": result.final,
        "chain": result.chain,
        "method": result.method,
        "error": result.error,
    }


@router.post("/batch")
async def resolve_batch(req: BypassBatchRequest):
    results = await bypass_batch(req.urls)
    return [
        {
            "original": r.original,
            "final": r.final,
            "chain": r.chain,
            "method": r.method,
            "error": r.error,
        }
        for r in results
    ]
