MATH_INTENT_PATTERNS = [
    "cagr",
    "compound annual",
    "growth rate",
    "year over year",
    "yoy",
    "increase by",
    "decrease by",
    "percentage",
    "%",
    "growth",
    "compare",
    "vs",
]


def query_suggests_math(query: str) -> bool:
    q = query.lower()
    return any(pat in q for pat in MATH_INTENT_PATTERNS)


__all__ = ["query_suggests_math"]
