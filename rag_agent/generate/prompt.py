"""Prompt assembly (architecture §9). Rules block + QUESTION + numbered CONTEXT.

The citation URL is deliberately left OUT of the model's instructions output —
cite.py attaches one from retrieval metadata in code, never from the model.
"""

from __future__ import annotations

from rag_agent.retrieve.search import SearchHit

SYSTEM_RULES = (
    "You are a facts-only mutual fund FAQ assistant for five HDFC schemes.\n"
    "Answer using ONLY the provided CONTEXT.\n"
    "At most three sentences.\n"
    "No buy/sell/hold advice, no portfolio advice, no computed returns.\n"
    "If CONTEXT is insufficient, say so plainly.\n"
    "Do not invent expense ratios, loads, or lock-in periods.\n"
    "Do not include any URLs in your answer; a citation is attached separately."
)


def build_prompt(question: str, hits: list[SearchHit]) -> str:
    """Assemble the full prompt: rules, the question, and numbered context."""
    context_blocks = [
        f"{index}. [{hit.scheme_name}] ({hit.source_url})\n{hit.text}"
        for index, hit in enumerate(hits, start=1)
    ]
    context = "\n\n".join(context_blocks)
    return f"{SYSTEM_RULES}\n\nQUESTION: {question}\n\nCONTEXT:\n{context}"