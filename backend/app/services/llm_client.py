"""Ollama LLM client — connects to local Ollama instance for text structuring.

Ollama runs separately (user installs from ollama.com). This client talks to
the local API at http://localhost:11434 (or custom URL via settings).
"""
import json
import logging
from typing import Any, Optional

import httpx

from app.services.settings_store import get as get_setting

logger = logging.getLogger("pyscrapr.llm")

DEFAULT_OLLAMA_URL = "http://localhost:11434"


def _get_ollama_url() -> str:
    return get_setting("ollama_url", DEFAULT_OLLAMA_URL) or DEFAULT_OLLAMA_URL


def _get_default_model() -> str:
    return get_setting("ollama_default_model", "llama3.2") or "llama3.2"


async def health_check() -> dict[str, Any]:
    """Check if Ollama is running and list available models."""
    url = _get_ollama_url()
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get(f"{url}/api/tags")
            if r.status_code != 200:
                return {"running": False, "url": url, "error": f"HTTP {r.status_code}"}
            data = r.json()
            models = [m.get("name", "") for m in data.get("models", [])]
            return {"running": True, "url": url, "models": models}
    except httpx.ConnectError:
        return {"running": False, "url": url, "error": "Connection refused — is Ollama running?"}
    except Exception as e:
        return {"running": False, "url": url, "error": str(e)}


async def generate(
    prompt: str,
    model: Optional[str] = None,
    system: Optional[str] = None,
    json_mode: bool = False,
    temperature: float = 0.3,
    timeout: int = 120,
) -> dict[str, Any]:
    """Call Ollama /api/generate. Returns {success, output, error, model}."""
    url = _get_ollama_url()
    model = model or _get_default_model()

    payload: dict[str, Any] = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": temperature},
    }
    if system:
        payload["system"] = system
    if json_mode:
        payload["format"] = "json"

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            r = await client.post(f"{url}/api/generate", json=payload)
            if r.status_code != 200:
                return {
                    "success": False,
                    "error": f"Ollama HTTP {r.status_code}: {r.text[:300]}",
                    "model": model,
                }
            data = r.json()
            return {
                "success": True,
                "output": data.get("response", ""),
                "model": model,
                "eval_count": data.get("eval_count"),
                "eval_duration_ms": (data.get("eval_duration") or 0) // 1_000_000,
            }
    except httpx.ConnectError:
        return {
            "success": False,
            "error": "Cannot connect to Ollama. Install from https://ollama.com and run `ollama serve`.",
            "model": model,
        }
    except httpx.TimeoutException:
        return {"success": False, "error": f"Request timed out after {timeout}s", "model": model}
    except Exception as e:
        return {"success": False, "error": f"{type(e).__name__}: {e}", "model": model}


async def extract_structured(
    text: str,
    schema_description: str,
    model: Optional[str] = None,
) -> dict[str, Any]:
    """Extract structured JSON from raw text using an LLM.

    Returns {success, data (dict/list), raw (str), error, model}
    """
    system = (
        "You are a precise data extraction assistant. "
        "Extract the requested information from the given text. "
        "Return ONLY valid JSON. No markdown, no explanations, no preamble. "
        "If a field cannot be found, use null."
    )
    prompt = (
        f"Schema to extract:\n{schema_description}\n\n"
        f"Text to analyze:\n---\n{text[:8000]}\n---\n\n"
        f"Return the JSON now:"
    )

    result = await generate(prompt, model=model, system=system, json_mode=True, temperature=0.1)
    if not result["success"]:
        return {**result, "data": None, "raw": ""}

    raw = result["output"].strip()
    # Strip markdown fences if LLM added them despite instructions
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1] if "\n" in raw else raw
        if raw.endswith("```"):
            raw = raw[:-3]
        raw = raw.strip()
        if raw.startswith("json"):
            raw = raw[4:].strip()

    try:
        data = json.loads(raw)
        return {"success": True, "data": data, "raw": raw, "model": result["model"]}
    except json.JSONDecodeError as e:
        return {
            "success": False,
            "error": f"LLM returned invalid JSON: {e}",
            "data": None,
            "raw": raw,
            "model": result["model"],
        }
