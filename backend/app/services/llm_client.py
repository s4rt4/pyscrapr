"""Multi-provider LLM client.

Originally Ollama-only. Extended with a unified `chat_completion()` that
supports DeepSeek, OpenAI, and Ollama. Existing `generate()` /
`extract_structured()` functions are kept intact for backward compatibility
with callers like the AI Extract feature.
"""
import json
import logging
from typing import Any, AsyncIterator, Optional

import httpx

from app.services.settings_store import get as get_setting

logger = logging.getLogger("pyscrapr.llm")

DEFAULT_OLLAMA_URL = "http://localhost:11434"

DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions"
OPENAI_URL = "https://api.openai.com/v1/chat/completions"

_DEFAULT_MODELS = {
    "deepseek": "deepseek-chat",
    "openai": "gpt-4o-mini",
    "ollama": "llama3.2",
}


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


# ─────────────────────────────────────────────────────────────
# Unified multi-provider chat_completion API
# ─────────────────────────────────────────────────────────────


def _resolve_model(provider: str, model: Optional[str]) -> str:
    if model:
        return model
    if provider == "ollama":
        return _get_default_model()
    return _DEFAULT_MODELS.get(provider, "deepseek-chat")


async def _chat_openai_compat(
    endpoint: str,
    api_key: str,
    model: str,
    messages: list[dict],
    max_tokens: int,
    temperature: float,
    timeout: int,
) -> dict[str, Any]:
    """Call an OpenAI-compatible /chat/completions endpoint (DeepSeek + OpenAI)."""
    if not api_key:
        raise RuntimeError("API key kosong untuk provider berbasis cloud.")
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "stream": False,
    }
    async with httpx.AsyncClient(timeout=timeout) as client:
        r = await client.post(endpoint, headers=headers, json=payload)
        if r.status_code != 200:
            raise RuntimeError(f"HTTP {r.status_code}: {r.text[:300]}")
        data = r.json()
    choice = (data.get("choices") or [{}])[0]
    msg = choice.get("message") or {}
    usage = data.get("usage") or {}
    return {
        "content": msg.get("content", ""),
        "tokens_used": int(usage.get("total_tokens") or 0),
        "model": data.get("model") or model,
    }


async def _chat_ollama(
    model: str,
    messages: list[dict],
    max_tokens: int,
    temperature: float,
    timeout: int,
) -> dict[str, Any]:
    """Call Ollama /api/chat."""
    url = _get_ollama_url()
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "options": {"temperature": temperature, "num_predict": max_tokens},
    }
    async with httpx.AsyncClient(timeout=timeout) as client:
        r = await client.post(f"{url}/api/chat", json=payload)
        if r.status_code != 200:
            raise RuntimeError(f"Ollama HTTP {r.status_code}: {r.text[:300]}")
        data = r.json()
    msg = data.get("message") or {}
    return {
        "content": msg.get("content", ""),
        "tokens_used": int(data.get("eval_count") or 0) + int(data.get("prompt_eval_count") or 0),
        "model": model,
    }


async def _chat_openai_compat_stream(
    endpoint: str,
    api_key: str,
    model: str,
    messages: list[dict],
    max_tokens: int,
    temperature: float,
    timeout: int,
) -> AsyncIterator[str]:
    if not api_key:
        raise RuntimeError("API key kosong untuk provider berbasis cloud.")
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "text/event-stream",
    }
    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "stream": True,
    }
    async with httpx.AsyncClient(timeout=timeout) as client:
        async with client.stream("POST", endpoint, headers=headers, json=payload) as r:
            if r.status_code != 200:
                body = await r.aread()
                raise RuntimeError(f"HTTP {r.status_code}: {body.decode('utf-8', 'ignore')[:300]}")
            async for line in r.aiter_lines():
                if not line or not line.startswith("data:"):
                    continue
                chunk = line[5:].strip()
                if chunk == "[DONE]":
                    break
                try:
                    obj = json.loads(chunk)
                    delta = (((obj.get("choices") or [{}])[0]).get("delta") or {}).get("content")
                    if delta:
                        yield delta
                except Exception:
                    continue


async def _chat_ollama_stream(
    model: str,
    messages: list[dict],
    max_tokens: int,
    temperature: float,
    timeout: int,
) -> AsyncIterator[str]:
    url = _get_ollama_url()
    payload = {
        "model": model,
        "messages": messages,
        "stream": True,
        "options": {"temperature": temperature, "num_predict": max_tokens},
    }
    async with httpx.AsyncClient(timeout=timeout) as client:
        async with client.stream("POST", f"{url}/api/chat", json=payload) as r:
            if r.status_code != 200:
                body = await r.aread()
                raise RuntimeError(f"Ollama HTTP {r.status_code}: {body.decode('utf-8', 'ignore')[:300]}")
            async for line in r.aiter_lines():
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                    chunk = (obj.get("message") or {}).get("content", "")
                    if chunk:
                        yield chunk
                    if obj.get("done"):
                        break
                except Exception:
                    continue


async def chat_completion(
    provider: str,
    messages: list[dict],
    *,
    api_key: str = "",
    model: Optional[str] = None,
    max_tokens: int = 300,
    temperature: float = 0.1,
    stream: bool = False,
    timeout: int = 30,
):
    """Unified chat completion across providers.

    provider: "deepseek" | "ollama" | "openai"
    Returns dict {content, tokens_used, model} when stream=False,
    or async iterator yielding str chunks when stream=True.
    """
    provider = (provider or "deepseek").lower()
    resolved_model = _resolve_model(provider, model)

    if stream:
        if provider == "deepseek":
            return _chat_openai_compat_stream(
                DEEPSEEK_URL, api_key, resolved_model, messages, max_tokens, temperature, timeout
            )
        if provider == "openai":
            return _chat_openai_compat_stream(
                OPENAI_URL, api_key, resolved_model, messages, max_tokens, temperature, timeout
            )
        if provider == "ollama":
            return _chat_ollama_stream(resolved_model, messages, max_tokens, temperature, timeout)
        raise ValueError(f"Provider tidak dikenal: {provider}")

    if provider == "deepseek":
        return await _chat_openai_compat(
            DEEPSEEK_URL, api_key, resolved_model, messages, max_tokens, temperature, timeout
        )
    if provider == "openai":
        return await _chat_openai_compat(
            OPENAI_URL, api_key, resolved_model, messages, max_tokens, temperature, timeout
        )
    if provider == "ollama":
        return await _chat_ollama(resolved_model, messages, max_tokens, temperature, timeout)
    raise ValueError(f"Provider tidak dikenal: {provider}")
