"""Retrieval: embed a question, pull top-k nearest chunks (Phase 4). No LLM.

Uses the SAME MiniLM model as ingest — ``ingest.embed.encode_texts`` — so query
and document vectors live in the same space. The model name appears only there.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass

from rag_agent.ingest.embed import encode_texts
from rag_agent.ingest.store import COLLECTION_NAME, get_client

# Allowed range is 3-5 (architecture §5.6); 4 is the default.
TOP_K = 4


@dataclass
class SearchHit:
    text: str
    source_url: str
    scheme_name: str
    fetched_at: str
    distance: float


def search(question: str, n_results: int = TOP_K) -> list[SearchHit]:
    """Return the n nearest chunks to ``question``, closest first.

    Distance comes from Chroma's cosine index (lower = more similar).
    """
    collection = get_client().get_collection(COLLECTION_NAME)  # raises if index missing
    query_vector = encode_texts([question])[0]

    result = collection.query(
        query_embeddings=[query_vector],
        n_results=n_results,
        include=["documents", "metadatas", "distances"],
    )

    hits: list[SearchHit] = []
    for doc, meta, distance in zip(
        result["documents"][0],
        result["metadatas"][0],
        result["distances"][0],
    ):
        hits.append(
            SearchHit(
                text=doc,
                source_url=meta.get("source_url", ""),
                scheme_name=meta.get("scheme_name", ""),
                fetched_at=meta.get("fetched_at", ""),
                distance=float(distance),
            )
        )
    return hits


def _index_ready() -> bool:
    from rag_agent.ingest.store import collection_count

    return collection_count() > 0


if __name__ == "__main__":
    if not _index_ready():
        print("Index not built yet — run: python -m rag_agent.ingest.run_ingest")
        sys.exit(1)

    question = " ".join(sys.argv[1:]) or "What is the expense ratio of HDFC Large Cap Fund Direct Growth?"
    top = search(question)
    print(f"Q: {question}\n")
    for rank, hit in enumerate(top, start=1):
        print(f"#{rank}  {hit.scheme_name}  (distance {hit.distance:.4f})")
        print(f"     url: {hit.source_url}")
        print(f"     updated: {hit.fetched_at}")
        print(f"     text: {hit.text[:200].replace(chr(10), ' ')}")