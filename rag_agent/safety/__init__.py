"""Safety gates (Phase 5). Nothing here touches Chroma or any LLM.

Exports are lazy so that ``python -m rag_agent.safety.classify`` still works
without a circular package import.
"""

__all__ = ["classify_or_refuse", "QueryResponse"]


def __getattr__(name: str):
    if name == "classify_or_refuse":
        from rag_agent.safety.classify import classify_or_refuse

        return classify_or_refuse
    if name == "QueryResponse":
        from rag_agent.safety.models import QueryResponse

        return QueryResponse
    raise AttributeError(f"module 'rag_agent.safety' has no attribute {name!r}")