"""Citation + freshness, ALWAYS from retrieval metadata (architecture §5.7)."""

from __future__ import annotations

from rag_agent.retrieve.search import SearchHit


def pick_citation(hits: list[SearchHit]) -> tuple[str, str]:
    """Return the one citation as ``(source_url, last_updated)``.

    - ``source_url``: the top hit's URL from chunk metadata — never the model's.
    - ``last_updated``: the newest ``fetched_at`` among the chunks used as context.
    """
    top = hits[0]
    last_updated = max(hit.fetched_at for hit in hits)
    return top.source_url, last_updated