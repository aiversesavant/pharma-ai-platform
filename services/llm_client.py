from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Optional

from services.llm_config import (
    LLM_API_BASE_URL,
    LLM_API_KEY,
    LLM_API_PATH_TEMPLATE,
    LLM_MAX_OUTPUT_TOKENS,
    LLM_MODEL_NAME,
    LLM_PROVIDER,
    LLM_TEMPERATURE,
    LLM_TIMEOUT_SECONDS,
    llm_is_configured,
)


def _build_gemini_url() -> str:
    path = LLM_API_PATH_TEMPLATE.format(model=LLM_MODEL_NAME)
    return f"{LLM_API_BASE_URL.rstrip('/')}{path}?key={urllib.parse.quote(LLM_API_KEY)}"


def _extract_gemini_text(response_json: dict) -> str:
    candidates = response_json.get("candidates", [])
    if not candidates:
        return ""

    content = candidates[0].get("content", {})
    parts = content.get("parts", [])

    texts = []
    for part in parts:
        text = part.get("text")
        if text:
            texts.append(text)

    return "\n".join(texts).strip()


def generate_text(prompt: str) -> Optional[str]:
    """
    Optional LLM generation layer.
    Returns None if LLM is disabled, not configured, or request fails.
    """
    if not llm_is_configured():
        return None

    if LLM_PROVIDER != "gemini":
        return None

    url = _build_gemini_url()

    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ],
        "generationConfig": {
            "temperature": LLM_TEMPERATURE,
            "maxOutputTokens": LLM_MAX_OUTPUT_TOKENS,
        },
    }

    data = json.dumps(payload).encode("utf-8")

    request = urllib.request.Request(
        url=url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=LLM_TIMEOUT_SECONDS) as response:
            raw = response.read().decode("utf-8")
            parsed = json.loads(raw)
            text = _extract_gemini_text(parsed)
            return text or None

    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError):
        return None