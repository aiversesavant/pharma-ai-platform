from __future__ import annotations

import os

from dotenv import load_dotenv


load_dotenv()


def _to_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


LLM_ENABLED = _to_bool(os.getenv("LLM_ENABLED"), default=False)
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini").strip().lower()
LLM_API_KEY = os.getenv("LLM_API_KEY", "").strip()

LLM_API_BASE_URL = os.getenv(
    "LLM_API_BASE_URL",
    "https://generativelanguage.googleapis.com",
).strip()

LLM_API_PATH_TEMPLATE = os.getenv(
    "LLM_API_PATH_TEMPLATE",
    "/v1beta/models/{model}:generateContent",
).strip()

LLM_MODEL_NAME = os.getenv(
    "LLM_MODEL_NAME",
    "gemini-1.5-flash",
).strip()

LLM_TIMEOUT_SECONDS = int(os.getenv("LLM_TIMEOUT_SECONDS", "45"))
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.2"))
LLM_MAX_OUTPUT_TOKENS = int(os.getenv("LLM_MAX_OUTPUT_TOKENS", "500"))


def llm_is_configured() -> bool:
    return bool(LLM_ENABLED and LLM_API_KEY and LLM_MODEL_NAME and LLM_API_BASE_URL)


def llm_status_summary() -> dict:
    """
    Safe status summary for UI display.
    Never exposes the raw API key.
    """
    return {
        "enabled_flag": LLM_ENABLED,
        "configured": llm_is_configured(),
        "provider": LLM_PROVIDER or "unknown",
        "model": LLM_MODEL_NAME or "unknown",
        "base_url": LLM_API_BASE_URL or "unknown",
        "api_key_present": bool(LLM_API_KEY),
        "timeout_seconds": LLM_TIMEOUT_SECONDS,
        "temperature": LLM_TEMPERATURE,
        "max_output_tokens": LLM_MAX_OUTPUT_TOKENS,
    }