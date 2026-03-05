from __future__ import annotations

from langgraph.graph import StateGraph, END

from src.backend.graph.nodes import retrieve_node
from src.backend.graph.state import ChatState


def build_chat_graph():
    """Compile the chat LangGraph (retrieval → end)."""
    graph = StateGraph(ChatState)
    graph.add_node("retrieve", retrieve_node)
    graph.set_entry_point("retrieve")
    graph.add_edge("retrieve", END)
    return graph.compile()


__all__ = ["build_chat_graph"]
