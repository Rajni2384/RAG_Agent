"""Embeddings via all-MiniLM-L6-v2 (Phase 3).

The model name lives ONLY here. Later phases (query) import ``encode_texts``
from this module so ingest and retrieval share one model, one dimension.
"""

from __future__ import annotations

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_DIMENSION = 384  # MiniLM-L6 output size (architecture §5.4)

_model = None


def _get_model():
    """Lazy-singleton SentenceTransformer (loaded once per process)."""
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer

        _model = SentenceTransformer(MODEL_NAME)
    return _model


def encode_texts(texts: list[str]) -> list[list[float]]:
    """Batch-encode strings into a list of 384-dim float vectors."""
    model = _get_model()
    vectors = model.encode(
        texts,
        batch_size=32,
        show_progress_bar=False,
        convert_to_numpy=True,
        normalize_embeddings=True,
    )
    return [vector.tolist() for vector in vectors]


if __name__ == "__main__":
    test = encode_texts(
        ["What is the expense ratio of this fund?", "How long is the ELSS lock-in period?"]
    )
    print("model:", MODEL_NAME)
    print("dimension:", len(test[0]))
    print("vectors:", len(test))