"""LLM endpoints — Ollama integration for text structuring."""
from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.services.llm_client import extract_structured, generate, health_check

router = APIRouter()


class GenerateRequest(BaseModel):
    prompt: str
    model: str | None = None
    system: str | None = None
    temperature: float = 0.3
    json_mode: bool = False


class ExtractRequest(BaseModel):
    text: str = Field(description="Raw text to extract from")
    schema_description: str = Field(
        description="Plain-language schema: e.g. 'Extract title (string), price (number), in_stock (boolean)'"
    )
    model: str | None = None


@router.get("/health")
async def llm_health():
    """Check if Ollama is running and list models."""
    return await health_check()


@router.post("/generate")
async def llm_generate(req: GenerateRequest):
    """Raw LLM generation — return text response."""
    return await generate(
        prompt=req.prompt,
        model=req.model,
        system=req.system,
        json_mode=req.json_mode,
        temperature=req.temperature,
    )


@router.post("/extract")
async def llm_extract(req: ExtractRequest):
    """Extract structured JSON from raw text."""
    return await extract_structured(
        text=req.text,
        schema_description=req.schema_description,
        model=req.model,
    )
