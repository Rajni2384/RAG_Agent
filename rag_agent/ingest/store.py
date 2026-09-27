"""Persist chunk embeddings into a local ChromaDB collection (Phase 3).

Rebuild semantics: every ingest wipes the ``hdfc_mf_faqs`` collection and
upserts fresh vectors, so reruns are always clean (no stale/duplicate ids).
"""

from __future__ import annotations

import chromadb

from rag_agent.ingest.chunk import Chunk
from rag_agent.ingest.embed import encode_texts
from rag_agent.paths import DATA_DIR

COLLECTION_NAME = "hdfc_mf_faqs"
CHROMA_DIR = DATA_DIR / "chroma"


def get_client() -> chromadb.PersistentClient:
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=str(CHROMA_DIR))


def rebuild_index(chunks: list[Chunk]) -> int:
    """Wipe the collection, embed every chunk, and write them all. Returns count."""
    client = get_client()
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:  # noqa: BLE001 — first run: nothing to delete
        pass

    collection = client.create_collection(
        COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )

    if not chunks:
        return 0

    embeddings = encode_texts([chunk.text for chunk in chunks])
    collection.add(
        ids=[chunk.chunk_id for chunk in chunks],
        embeddings=embeddings,
        documents=[chunk.text for chunk in chunks],
        metadatas=[
            {
                "chunk_id": chunk.chunk_id,
                "source_url": chunk.source_url,
                "scheme_name": chunk.scheme_name,
                "scheme_type": chunk.scheme_type,
                "fetched_at": chunk.fetched_at.isoformat(),
            }
            for chunk in chunks
        ],
    )
    return collection.count()


def collection_count() -> int:
    """Number of vectors currently stored (0 when the collection is absent)."""
    client = get_client()
    try:
        return client.get_collection(COLLECTION_NAME).count()
    except Exception:  # noqa: BLE001 — collection never built
        return 0