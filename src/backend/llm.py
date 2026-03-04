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


def call_llm_stream(prompt: str, model: Optional[str] = None, temperature: float = 0.0, base_url: Optional[str] = None):
    """Stream tokens from the chat completion API (generator of text chunks)."""
    try:
        settings.validate(require_pageindex=False, require_generic_llm=True)
        api_key = settings.api_key
        api_base = base_url or settings.base_url
        model_name = model or settings.model_name
        client = OpenAI(api_key=api_key, base_url=api_base)
        logger.info("Streaming LLM model=%s temp=%.2f prompt_chars=%d", model_name, temperature, len(prompt))
        stream = client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            stream=True,
        )
        for chunk in stream:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            content = getattr(delta, "content", None)
            if not content:
                continue
            if isinstance(content, str):
                yield content
            elif isinstance(content, list):
                parts = []
                for part in content:
                    if hasattr(part, "text"):
                        parts.append(part.text)
                    elif isinstance(part, dict) and "text" in part:
                        parts.append(part["text"])
                if parts:
                    yield "".join(parts)
    except Exception as exc:  # noqa: BLE001
        raise VRETLException(str(exc), sys) from exc


__all__ = ["call_llm"]
