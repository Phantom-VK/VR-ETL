"""Minimal LLM wrapper for OpenAI-compatible chat completions."""
from __future__ import annotations

import sys
from typing import Optional

from openai import OpenAI

from src.config import settings
from src.utils.logger import logger
from src.utils.exception import VRETLException


def call_llm(prompt: str, model: Optional[str] = None, temperature: float = 0.0, base_url: Optional[str] = None) -> str:
    """Call the chat completion API and return the assistant message content.

    Defaults target DeepSeek via base_url, but remains compatible with OpenAI API surface.
    """
    try:
        settings.validate(require_openai=False, require_pageindex=False, require_generic_llm=True)
        api_key = settings.api_key
        api_base = base_url or settings.base_url
        model_name = model or settings.model_name
        client = OpenAI(api_key=api_key, base_url=api_base)
        logger.info("Calling LLM model=%s temp=%.2f prompt_chars=%d", model_name, temperature, len(prompt))
        response = client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            stream=False,
        )
        content = response.choices[0].message.content if response.choices else ""
        logger.info("LLM call completed (chars=%d) preview=%r", len(content), content[:120])
        return content or ""
    except Exception as exc:  # noqa: BLE001
        raise VRETLException(str(exc), sys) from exc


__all__ = ["call_llm"]
