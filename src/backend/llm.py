"""Minimal LLM wrapper for DeepSeek/OpenAI-compatible chat completions."""
from __future__ import annotations

import sys
from typing import Optional

from openai import OpenAI

from src.config import settings
from src.utils.logger import logger
from src.utils.exception import VRETLException


def call_llm(prompt: str, model: str = "deepseek-reasoner", temperature: float = 0.0, base_url: Optional[str] = None) -> str:
    """Call the chat completion API and return the assistant message content.

    Defaults target DeepSeek via base_url, but remains compatible with OpenAI API surface.
    """
    try:
        settings.validate(require_openai=False, require_pageindex=False, require_deepseek=True)
        api_key = settings.deepseek_api_key
        api_base = base_url or settings.deepseek_base_url
        client = OpenAI(api_key=api_key, base_url=api_base)
        logger.info("Calling LLM model=%s temp=%.2f", model, temperature)
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            stream=False,
        )
        content = response.choices[0].message.content if response.choices else ""
        logger.info("LLM call completed (chars=%d)", len(content))
        return content or ""
    except Exception as exc:  # noqa: BLE001
        raise VRETLException(str(exc), sys) from exc


__all__ = ["call_llm"]
