from __future__ import annotations

from typing import Dict, Any

import sympy as sp

from src.utils.exception import VRETLException
from src.utils.logger import logger

# Tool schema for OpenAI/DeepSeek function calling
MATH_TOOL: list[Dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "evaluate_math",
            "description": "Safely evaluate a mathematical expression (supports +,-,*,/,**, sqrt, log, exp, trig, percentages).",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "Math expression, e.g., (2030/2022)**(1/8)-1",
                    },
                    "precision": {
                        "type": "integer",
                        "minimum": 2,
                        "maximum": 10,
                        "default": 4,
                        "description": "Decimal precision for the result (default 4).",
                    },
                },
                "required": ["expression"],
            },
        },
    }
]

# Allowed symbols/functions for sympy evaluation
_ALLOWED_FUNCS = {
    "sqrt": sp.sqrt,
    "log": sp.log,
    "ln": sp.log,
    "exp": sp.exp,
    "sin": sp.sin,
    "cos": sp.cos,
    "tan": sp.tan,
    "asin": sp.asin,
    "acos": sp.acos,
    "atan": sp.atan,
    "abs": sp.Abs,
    "pi": sp.pi,
    "e": sp.E,
}


def run_math_tool(expression: str, precision: int = 4) -> str:
    """Safely evaluate math expression using sympy with a strict whitelist."""
    try:
        if not expression or len(expression) > 200:
            raise ValueError("Expression too long or empty")
        precision = min(max(int(precision), 2), 10)
        expr = sp.sympify(expression, locals=_ALLOWED_FUNCS)
        val = expr.evalf(precision)
        result = f"{val}"
        logger.info("math_tool expression='%s' -> %s", expression, result)
        return result
    except Exception as exc:  # noqa: BLE001
        logger.exception("math_tool failed for expression='%s'", expression)
        import sys as _sys

        raise VRETLException(str(exc), _sys) from exc


__all__ = ["MATH_TOOL", "run_math_tool"]
