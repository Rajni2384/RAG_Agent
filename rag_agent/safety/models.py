"""Shared query-response shape (architecture §6.4). Not a UI type."""

from __future__ import annotations

from dataclasses import dataclass

KIND_ANSWER = "answer"
KIND_REFUSAL_PII = "refusal_pii"
KIND_REFUSAL_ADVICE = "refusal_advice"
KIND_REFUSAL_PERFORMANCE = "refusal_performance"
KIND_NOT_FOUND = "not_found"

REFUSAL_KINDS = (
    KIND_REFUSAL_PII,
    KIND_REFUSAL_ADVICE,
    KIND_REFUSAL_PERFORMANCE,
)


@dataclass
class QueryResponse:
    """Outcome of guarding a question (or, later, of the full RAG pipeline)."""

    kind: str
    text: str
    source_url: str | None = None  # required for kind == answer
    last_updated: str | None = None
    education_url: str | None = None  # refusals