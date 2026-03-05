"""Minimal LLM wrapper for OpenAI-compatible chat completions."""
from __future__ import annotations

import sys
from typing import Optional, List, Dict, Any, Iterable

from openai import OpenAI

from src.config import settings
from src.utils.logger import logger
from src.utils.exception import VRETLException


def call_llm_stream(prompt: str, model: Optional[str] = None, temperature: float = 0.0, base_url: Optional[str] = None):
    """Stream reasoning and answer tokens separately.

    Yields dict events: {"type": "reason"|"answer", "text": str}
    """
    try:
        settings.validate(require_pageindex=False, require_generic_llm=True)
        api_key = settings.api_key
        api_base = base_url or settings.base_url
        model_name = model
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
            # DeepSeek reasoner: reasoning_content first, then content
            if getattr(delta, "reasoning_content", None):
                yield {"type": "reason", "text": delta.reasoning_content}
            elif getattr(delta, "content", None):
                yield {"type": "answer", "text": delta.content}
    except Exception as exc:  # noqa: BLE001
        logger.exception("LLM streaming call failed")
        raise VRETLException(str(exc), sys) from exc


def call_llm_stream_messages(
    messages: List[Dict[str, Any]],
    model: Optional[str] = None,
    temperature: float = 0.0,
    base_url: Optional[str] = None,
):
    """Stream reasoning and answer tokens given full message list (system/user/tool etc)."""
    try:
        settings.validate(require_pageindex=False, require_generic_llm=True)
        api_key = settings.api_key
        api_base = base_url or settings.base_url
        model_name = model
        client = OpenAI(api_key=api_key, base_url=api_base)
        logger.info("Streaming LLM (messages) model=%s temp=%.2f msg_count=%d", model_name, temperature, len(messages))
        stream = client.chat.completions.create(
            model=model_name,
            messages=messages,
            temperature=temperature,
            stream=True,
        )
        for chunk in stream:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            if getattr(delta, "reasoning_content", None):
                yield {"type": "reason", "text": delta.reasoning_content}
            elif getattr(delta, "content", None):
                yield {"type": "answer", "text": delta.content}
    except Exception as exc:  # noqa: BLE001
        logger.exception("LLM streaming call (messages) failed")
        raise VRETLException(str(exc), sys) from exc


def call_llm_tools(
    messages: List[Dict[str, Any]],
    tools: Iterable[Dict[str, Any]],
    model: Optional[str] = None,
    temperature: float = 0.0,
    base_url: Optional[str] = None,
    tool_choice: Any = "auto",
) -> Dict[str, Any]:
    """Single non-stream call with tool choice=auto. Returns dict with tool_call or None."""
    try:
        settings.validate(require_pageindex=False, require_generic_llm=True)
        api_key = settings.api_key
        api_base = base_url or settings.base_url
        model_name = model
        client = OpenAI(api_key=api_key, base_url=api_base)
        logger.info("LLM tool call model=%s temp=%.2f messages=%d", model_name, temperature, len(messages))
        resp = client.chat.completions.create(
            model=model_name,
            messages=messages,
            temperature=temperature,
            tools=tools,
            tool_choice=tool_choice,
        )
        return resp.choices[0].message
    except Exception as exc:  # noqa: BLE001
        logger.exception("LLM tool call failed")
        raise VRETLException(str(exc), sys) from exc


__all__ = ["call_llm_stream", "call_llm_stream_messages", "call_llm_tools"]
