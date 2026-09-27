"""Full query path: guardrails → retrieve → prompt → LLM → cite (Phase 6)."""

from __future__ import annotations

import sys

from rag_agent.generate.cite import pick_citation
from rag_agent.generate.llm import complete
from rag_agent.generate.postprocess import enforce_three_sentences
from rag_agent.generate.prompt import build_prompt
from rag_agent.retrieve.search import TOP_K, search
from rag_agent.safety import classify_or_refuse
from rag_agent.safety.models import (
    KIND_ANSWER,
    KIND_NOT_FOUND,
    REFUSAL_KINDS,
    QueryResponse,
)

# One documented relevance threshold (cosine distance). Above it → not_found,
# no LLM call, no invented facts. Measured: factual queries sit at ~0.14-0.50;
# off-topic questions land above ~0.74.
MAX_DISTANCE = 0.70

_NOT_FOUND_TEXT = (
    "I couldn't find that in the index. Try asking about expense ratio, exit load, "
    "lock-in period, minimum SIP, or holdings for one of the five HDFC schemes."
)


def ask(question: str) -> QueryResponse:
    """Answer a question or refuse it. Never calls the LLM on unsafe/unknown input."""
    # 1) Safety first: refusal stops here — no embed, no Chroma, no LLM.
    refusal = classify_or_refuse(question)
    if refusal is not None:
        return refusal

    # 2) Retrieve the nearest chunks (closest first).
    hits = search(question, n_results=TOP_K)

    # 3) No useful hits → not_found, no LLM, no invented numbers.
    if not hits or hits[0].distance > MAX_DISTANCE:
        return QueryResponse(kind=KIND_NOT_FOUND, text=_NOT_FOUND_TEXT)

    # 4) Generate from the chunks only, then force the contract in code.
    prompt = build_prompt(question, hits)
    raw_answer = complete(prompt)
    answer = enforce_three_sentences(raw_answer)
    source_url, last_updated = pick_citation(hits)

    return QueryResponse(
        kind=KIND_ANSWER,
        text=answer,
        source_url=source_url,
        last_updated=last_updated,
    )


if __name__ == "__main__":
    question = " ".join(sys.argv[1:]) or "What is the lock-in for HDFC ELSS Tax Saver?"
    try:
        result = ask(question)
    except RuntimeError as exc:
        print(f"Q: {question}\nERROR: {exc}")
        sys.exit(1)

    print(f"Q: {question}")
    print(f"kind: {result.kind}")
    if result.kind in REFUSAL_KINDS:
        print("(gate refused — no retrieval, no LLM call)")
    print(f"text: {result.text}")
    if result.source_url:
        print(f"source_url: {result.source_url}")
    if result.last_updated:
        print(f"last_updated: {result.last_updated}")
    if result.education_url:
        print(f"education_url: {result.education_url}")