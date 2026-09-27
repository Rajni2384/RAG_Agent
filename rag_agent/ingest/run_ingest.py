"""Full ingest pipeline: load → clean → chunk → embed → upsert → manifest (Phase 3)."""

from __future__ import annotations

import json
from datetime import datetime, timezone

from rag_agent.ingest.chunk import chunk_documents
from rag_agent.ingest.load import load_all_documents
from rag_agent.ingest.store import COLLECTION_NAME, collection_count, rebuild_index
from rag_agent.paths import DATA_DIR

MANIFEST_PATH = DATA_DIR / "ingest_manifest.json"


def run_ingest() -> dict:
    documents = load_all_documents()
    chunks = chunk_documents(documents)

    stored = rebuild_index(chunks)

    manifest = {
        "run_at": datetime.now(timezone.utc).isoformat(),
        "urls": [doc.url for doc in documents],
        "chunk_count": len(chunks),
        "collection": COLLECTION_NAME,
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print(f"documents: {len(documents)}")
    print(f"chunks written to index: {stored}")
    print(f"collection count: {collection_count()}")
    print(f"manifest: {MANIFEST_PATH}")
    return manifest


if __name__ == "__main__":
    run_ingest()