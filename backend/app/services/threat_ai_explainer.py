"""ThreatAIExplainer — adds an AI narrative to suspicious threat-scan reports.

Calls a chat-completion provider (DeepSeek by default, with Ollama fallback)
only when a file's risk_score crosses a configurable threshold. Results are
cached by SHA256 in `ai_threat_cache` so re-scanning the same file is free.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Optional

from app.db.session import AsyncSessionLocal
from app.repositories.ai_threat_cache_repository import AIThreatCacheRepository
from app.services import llm_client
from app.services.settings_store import get as get_setting

logger = logging.getLogger("pyscrapr.threat.ai")


# Cost rates per token (USD). Estimates blend input + output rates.
_COST_RATES: dict[str, float] = {
    "deepseek-chat": 0.50e-6,
    "deepseek-reasoner": 1.50e-6,
    "gpt-4o-mini": 0.30e-6,
    "gpt-4o": 5.00e-6,
}


class ThreatAIExplainer:
    async def explain(
        self,
        file_hash: str,
        findings: dict,
        threshold: int = 50,
    ) -> Optional[dict]:
        """Return an AI explanation dict, or None if skipped/disabled.

        dict shape: {analysis, model_used, tokens_used, cost_usd, cached}
        """
        # Guard 1: master toggle
        if not get_setting("ai_explain_enabled", True):
            return None
        # Guard 2: threshold
        try:
            risk = int(findings.get("risk_score") or 0)
        except Exception:
            risk = 0
        if risk < threshold:
            return None
        # Guard 3: hash required for cache
        if not file_hash:
            return None

        # Cache lookup
        async with AsyncSessionLocal() as session:
            repo = AIThreatCacheRepository(session)
            cached = await repo.get_by_hash(file_hash)
            if cached:
                return {
                    "analysis": cached.analysis,
                    "model_used": cached.model_used,
                    "tokens_used": cached.tokens_used,
                    "cost_usd": cached.cost_usd,
                    "cached": True,
                }

        # Build prompt
        system_msg = self._system_prompt()
        user_msg = self._build_prompt(findings)
        messages = [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_msg},
        ]

        provider = (get_setting("ai_explain_provider", "deepseek") or "deepseek").lower()
        max_tokens = int(get_setting("ai_explain_max_tokens", 300) or 300)
        api_key = ""
        model = None
        if provider == "deepseek":
            api_key = get_setting("deepseek_api_key", "") or ""
            model = get_setting("ai_explain_model_deepseek", "deepseek-chat") or "deepseek-chat"
        elif provider == "openai":
            api_key = get_setting("openai_api_key", "") or ""
            model = get_setting("ai_explain_model_openai", "gpt-4o-mini") or "gpt-4o-mini"

        result: Optional[dict] = None
        try:
            result = await llm_client.chat_completion(
                provider=provider,
                messages=messages,
                api_key=api_key,
                model=model,
                max_tokens=max_tokens,
                temperature=0.1,
                timeout=30,
            )
        except Exception as e:
            logger.warning("AI explain provider %s gagal: %s", provider, e)
            if provider != "ollama":
                # Auto-fallback to local Ollama
                try:
                    result = await llm_client.chat_completion(
                        provider="ollama",
                        messages=messages,
                        max_tokens=max_tokens,
                        temperature=0.1,
                        timeout=60,
                    )
                except Exception as e2:
                    logger.warning("Fallback Ollama juga gagal: %s", e2)
                    raise
            else:
                raise

        if not result or not result.get("content"):
            return None

        cost = self._compute_cost(result.get("model", ""), int(result.get("tokens_used") or 0))

        # Persist
        try:
            async with AsyncSessionLocal() as session:
                repo = AIThreatCacheRepository(session)
                # Re-check cache to avoid race
                existing = await repo.get_by_hash(file_hash)
                if not existing:
                    fname = Path(findings.get("file_path") or "").name or None
                    await repo.create(
                        file_hash=file_hash,
                        risk_score=risk,
                        analysis=result["content"],
                        model_used=result.get("model", "") or "",
                        tokens_used=int(result.get("tokens_used") or 0),
                        cost_usd=cost,
                        filename=fname,
                    )
                    await session.commit()
        except Exception as e:
            logger.debug("Gagal menyimpan cache AI: %s", e)

        return {
            "analysis": result["content"],
            "model_used": result.get("model", "") or "",
            "tokens_used": int(result.get("tokens_used") or 0),
            "cost_usd": cost,
            "cached": False,
        }

    def _system_prompt(self) -> str:
        lang = get_setting("ai_explain_language", "id") or "id"
        if lang == "id":
            return (
                "Kamu analis malware. Jawab teknis dan ringkas dalam Bahasa Indonesia. "
                "Maksimal 3 kalimat. Hindari istilah marketing."
            )
        return (
            "You are a malware analyst. Be concise and technical. "
            "Maximum 3 sentences. Avoid marketing speak."
        )

    def _build_prompt(self, findings: dict) -> str:
        lang = get_setting("ai_explain_language", "id") or "id"
        filename = Path(findings.get("file_path") or "").name or "(tidak diketahui)"
        claimed = findings.get("claimed_type") or "-"
        detected = findings.get("detected_type") or "-"
        risk = findings.get("risk_score", 0)
        entropy = findings.get("entropy", 0.0)

        # Group findings by severity
        sev_order = ["critical", "high", "medium", "low", "info"]
        groups: dict[str, list[dict]] = {s: [] for s in sev_order}
        for f in findings.get("findings", []) or []:
            sev = (f.get("severity") or "info").lower()
            if sev not in groups:
                sev = "info"
            groups[sev].append(f)

        lines: list[str] = []
        lines.append(f"File: {filename}")
        lines.append(f"Type: {claimed} -> {detected}")
        lines.append(f"Risk: {risk}/100")
        lines.append(f"Entropy: {entropy:.2f}" if isinstance(entropy, (int, float)) else f"Entropy: {entropy}")

        total = 0
        for sev in sev_order:
            for f in groups[sev][:3]:
                if total >= 8:
                    break
                title = (f.get("title") or "").strip()
                desc = (f.get("description") or "").strip()
                if len(desc) > 200:
                    desc = desc[:200] + "..."
                lines.append(f"[{sev.upper()}] {title}: {desc}")
                total += 1
            if total >= 8:
                break

        # Suspicious strings (if PE module included them)
        modules = findings.get("modules") or {}
        pe = modules.get("pe") or {}
        sus_strings = pe.get("suspicious_strings") or pe.get("strings") or []
        if sus_strings:
            top = []
            for s in sus_strings[:5]:
                s_str = str(s)
                if len(s_str) > 80:
                    s_str = s_str[:80] + "..."
                top.append(s_str)
            lines.append("Strings: " + " | ".join(top))

        if lang == "id":
            lines.append("")
            lines.append("Jelaskan ancaman ini, dampaknya, dan apakah harus dihapus.")
        else:
            lines.append("")
            lines.append("Explain the threat, its impact, and whether it should be removed.")
        return "\n".join(lines)

    def _compute_cost(self, model: str, total_tokens: int) -> float:
        if not model or not total_tokens:
            return 0.0
        rate = _COST_RATES.get(model, 0.0)
        return float(total_tokens) * rate


_explainer: Optional[ThreatAIExplainer] = None


def get_explainer() -> ThreatAIExplainer:
    global _explainer
    if _explainer is None:
        _explainer = ThreatAIExplainer()
    return _explainer
