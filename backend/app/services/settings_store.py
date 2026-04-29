"""Persistent user settings — stored as JSON on disk.

Settings are loaded once on import, modified via update(), and written back.
Services read from `get()` to pick up user overrides at runtime.
"""
import json
from pathlib import Path
from typing import Any

from app.config import settings as app_config

_SETTINGS_FILE = app_config.data_dir / "settings.json"

_DEFAULTS: dict[str, Any] = {
    # Download
    "download_dir": str(app_config.download_dir),

    # Scraping defaults
    "default_concurrency": 8,
    "default_rate_limit": 3.0,
    "default_timeout": 15,
    "max_retries": 3,
    "user_agent": "PyScrapr/1.0 (+https://github.com/local)",

    # Filter defaults
    "min_image_width": 100,
    "min_image_height": 100,
    "min_image_bytes": 5120,

    # Media downloader
    "default_quality": "1080p",
    "default_format": "mp4",
    "default_subtitles": "skip",
    "embed_thumbnail": True,
    "embed_metadata": True,
    "cookies_browser": "",

    # Proxy
    "proxy_list": "",  # one per line
    "proxy_mode": "round_robin",  # round_robin | random | none

    # CAPTCHA solver
    "captcha_provider": "",  # 2captcha | anticaptcha
    "captcha_api_key": "",

    # UA rotation
    "ua_mode": "random",  # random | round_robin | chrome_win | firefox_win | etc.

    # UI preferences
    "notification_sound": True,
    "auto_open_folder": False,

    # LLM (Ollama)
    "ollama_url": "http://localhost:11434",
    "ollama_default_model": "llama3.2",

    # Webhooks & notifications
    "webhook_discord_url": "",
    "webhook_telegram_token": "",
    "webhook_telegram_chat_id": "",
    "webhook_generic_url": "",
    "webhook_on_done": True,
    "webhook_on_error": True,
    "webhook_on_diff_only": False,  # only notify when Diff detects changes

    # Email (SMTP) notifications
    "smtp_enabled": False,
    "smtp_host": "",
    "smtp_port": 587,
    "smtp_user": "",
    "smtp_password": "",
    "smtp_use_tls": True,
    "smtp_from": "",  # defaults to smtp_user if empty
    "smtp_to": "",    # comma-separated recipient list
    "smtp_on_done": True,
    "smtp_on_error": True,

    # Mapper defaults
    "mapper_max_depth": 2,
    "mapper_max_pages": 500,
    "mapper_stay_on_domain": True,
    "mapper_respect_robots": True,

    # Ripper defaults
    "ripper_max_depth": 2,
    "ripper_max_pages": 50,
    "ripper_max_assets": 3000,
    "ripper_rewrite_links": True,
    "ripper_generate_report": True,

    # Playwright
    "playwright_enabled": False,
    "playwright_wait_until": "networkidle",  # load | domcontentloaded | networkidle
    "playwright_timeout_ms": 30000,
    "playwright_stealth_enabled": True,  # playwright-stealth + AutomationControlled flag

    # Worker node distribution
    "worker_mode": "master",  # "master" | "worker" | "standalone"
    "worker_pool": "",  # comma-separated worker URLs for master mode, e.g. "http://192.168.1.10:8000,http://192.168.1.11:8000"
    "worker_auth_token": "",  # shared secret, workers validate, master sends in header
    "worker_dispatch_strategy": "round_robin",  # round_robin | random | least_loaded
    "worker_enabled": False,  # master must enable to dispatch remotely; default false = local only

    # ThreatScanner
    "threat_scan_enabled": True,
    "threat_virustotal_api_key": "b8d4855abda17ee20fb57510930a37adb7c85ec8250bf2255a7fb9c39cef549f",
    "threat_virustotal_enabled": True,
    "threat_malwarebazaar_enabled": True,
    "threat_malwarebazaar_auth_key": "",  # optional; empty = anonymous mode
    "threat_auto_scan_downloads": False,
    "threat_quarantine_enabled": False,
    "threat_scan_depth": "standard",
    "threat_max_file_size_mb": 100,
    "threat_archive_max_depth": 5,
    "threat_archive_max_ratio": 100,
    "threat_yara_rules_last_updated": 0,

    # AI Threat Explainer
    "ai_explain_enabled": True,
    "ai_explain_provider": "deepseek",  # deepseek | ollama | openai
    "deepseek_api_key": "",
    "openai_api_key": "",
    "ai_explain_threshold": 50,
    "ai_explain_max_tokens": 300,
    "ai_explain_language": "id",  # id | en
    "ai_explain_model_deepseek": "deepseek-chat",
    "ai_explain_model_openai": "gpt-4o-mini",
}

_current: dict[str, Any] = {}


def _load() -> dict[str, Any]:
    if _SETTINGS_FILE.exists():
        try:
            data = json.loads(_SETTINGS_FILE.read_text(encoding="utf-8"))
            return {**_DEFAULTS, **data}
        except Exception:
            pass
    return dict(_DEFAULTS)


def _save(data: dict[str, Any]) -> None:
    _SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    # Only persist non-default values to keep file clean
    diff = {k: v for k, v in data.items() if k in _DEFAULTS and v != _DEFAULTS.get(k)}
    _SETTINGS_FILE.write_text(json.dumps(diff, indent=2), encoding="utf-8")


def get_all() -> dict[str, Any]:
    """Return merged defaults + user overrides."""
    global _current
    if not _current:
        _current = _load()
    return dict(_current)


def get(key: str, default: Any = None) -> Any:
    return get_all().get(key, default)


def update(patch: dict[str, Any]) -> dict[str, Any]:
    """Merge patch into current settings, save, return full settings."""
    global _current
    current = get_all()
    # Only accept known keys
    for k, v in patch.items():
        if k in _DEFAULTS:
            current[k] = v
    _current = current
    _save(current)
    return dict(_current)


def reset() -> dict[str, Any]:
    """Reset all settings to defaults."""
    global _current
    _current = dict(_DEFAULTS)
    if _SETTINGS_FILE.exists():
        _SETTINGS_FILE.unlink()
    return dict(_current)


def get_defaults() -> dict[str, Any]:
    return dict(_DEFAULTS)
