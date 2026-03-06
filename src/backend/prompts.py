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


def build_search_prompt(query: str) -> str:
    return (
        "You are given a question and have a tree structure of a document.\n"
        "Each node contains a node id, node title, and a corresponding summary.\n"
        "Your task is to find all nodes that are likely to contain the answer to the question.\n"
        "By analyzing the question and nodes, decide if math calculations are required for this query or not.\n"
        "Set require_math=true when the question involves growth rates, CAGR, percentages, comparisons, or arithmetic over time targets/baselines.\n\n"
        f"Question: {query}\n\n"
        "Please reply in the following JSON format:\n"
        "{\n"
        '    "node_list": ["node_id_1", "node_id_2", ..., "node_id_n"],\n'
        '    "require_math": <true|false>,\n'
        '    "citations": ["<doc=file.pdf;page=1>", "..."]\n'
        "}\n"
        "Only return node_id values that appear in the tree. Do not invent node_ids.\n"
        "Directly return the final JSON structure. Do not output anything else.\n"
    )


__all__ = [
    "SYSTEM_PROMPT",
    "build_user_prompt",
    "build_citation_retry_prompt",
    "build_search_prompt",
]
