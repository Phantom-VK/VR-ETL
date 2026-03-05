from __future__ import annotations

from typing import Dict, Any
import sys

import sympy as sp
from sympy.parsing.sympy_parser import (
    parse_expr,
    standard_transformations,
    implicit_multiplication_application,
)

from src.utils.exception import VRETLException
from src.utils.logger import logger

# Tool schema for OpenAI/DeepSeek function calling
MATH_TOOL: list[Dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "evaluate_math",
            "strict": True,
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
                "additionalProperties": False,
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
        transformations = standard_transformations + (implicit_multiplication_application,)
        expr = parse_expr(expression, local_dict=_ALLOWED_FUNCS, transformations=transformations)
        val = expr.evalf(precision)
        result = f"{val}"
        logger.info("math_tool expression='%s' -> %s", expression, result)
        return result
    except Exception as exc:
        logger.exception("math_tool failed for expression='%s'", expression)
        raise VRETLException(str(exc), sys) from exc


__all__ = ["MATH_TOOL", "run_math_tool"]
