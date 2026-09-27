"""Read-only dump of the persisted Chroma collection to a readable txt file.

Not part of the ingest pipeline — purely so humans can inspect chunks and
embeddings (class demo aid). Reads from the on-disk index (the source of truth).
"""

from __future__ import annotations

import datetime

from rag_agent.ingest.store import COLLECTION_NAME, get_client
from rag_agent.paths import DATA_DIR

OUT_PATH = DATA_DIR / "chunks_export.txt"

# Show only the head/tail of each 384-dim vector so the file stays readable.
HEAD_DIMS = 8
TAIL_DIMS = 5


def _fmt_vector(vector: list[float]) -> str:
    head = ", ".join(f"{v:.4f}" for v in vector[:HEAD_DIMS])
    tail = ", ".join(f"{v:.4f}" for v in vector[-TAIL_DIMS:])
    return f"[{head}, ... {len(vector) - HEAD_DIMS - TAIL_DIMS} more ..., {tail}]"


def export_chunks_txt() -> str:
    collection = get_client().get_collection(COLLECTION_NAME)
    data = collection.get(include=["documents", "metadatas", "embeddings"])

    records = sorted(
        zip(data["ids"], data["documents"], data["metadatas"], data["embeddings"]),
        key=lambda r: r[0],  # chunk_id order: elss_000, elss_001, ...
    )

    lines = [
        "RAG-Agent — chunk + embedding export (read-only dump from Chroma)",
        f"generated : {datetime.datetime.now().isoformat(timespec='seconds')}",
        f"collection: {COLLECTION_NAME}",
        f"total     : {len(records)} chunks",
        f"dimension : {len(records[0][3])} (all-MiniLM-L6-v2)",
        "",
        f"per scheme:",
    ]
    from collections import Counter

    counts = Counter(meta["scheme_type"] for _, _, meta, _ in records)
    for scheme_type in sorted(counts):
        lines.append(f"  {scheme_type:<11} {counts[scheme_type]} chunks")

    for chunk_id, document, meta, embedding in records:
        lines.extend(
            [
                "",
                "=" * 72,
                f"chunk_id    : {chunk_id}",
                f"scheme_name : {meta['scheme_name']}",
                f"scheme_type : {meta['scheme_type']}",
                f"source_url  : {meta['source_url']}",
                f"fetched_at  : {meta['fetched_at']}",
                "text        :",
            ]
        )
        lines.extend(f"    {row}" for row in document.splitlines())
        lines.append(f"embedding   : {_fmt_vector(embedding)}")

    OUT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return OUT_PATH


if __name__ == "__main__":
    path = export_chunks_txt()
    print(f"wrote {path}")