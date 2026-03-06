SYSTEM_PROMPT = (
    "You are a precise document Q&A assistant. "
    "Use ONLY the provided context. "
    "Cite page numbers as <page=PAGE_NUMBER> for every claim. "
    "Never invent facts. "
    "If a math tool result is provided, trust it and do not recalculate."
)


def build_user_prompt(context: str, question: str) -> str:
    return (
        "Context:\n"
        f"{context}\n\n"
        f"Question: {question}\n\n"
        "Rules:\n"
        "- Be clear and concise.\n"
        "- Cite page numbers as <page=PAGE_NUMBER> wherever you use evidence.\n"
        "- Do NOT invent information outside the context.\n"
        "- Convert numerical outputs to proper units."
    )


def build_citation_retry_prompt(answer: str, context: str, question: str) -> str:
    return (
        "Your previous draft lacked required citations. "
        "Rewrite the answer to include <page=PAGE_NUMBER> for every factual claim.\n\n"
        f"Context:\n{context}\n\n"
        f"Question: {question}\n\n"
        f"Draft answer:\n{answer}\n\n"
        "Return only the corrected answer with citations."
    )


__all__ = ["SYSTEM_PROMPT", "build_user_prompt", "build_citation_retry_prompt"]
