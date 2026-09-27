"""Embeddings via all-MiniLM-L6-v2 in ONNX (fastembed) — Phase 3.

Swapped from sentence-transformers (PyTorch) to fastembed (ONNX Runtime) so
the app fits inside 512 MB containers (Render free plan). It is the SAME
Hugging Face model, so the 384-dim vectors and cosine similarity behaviour are
unchanged; the index must be rebuilt once after this swap (run_ingest).

The model name lives ONLY here. Later phases (query) import ``encode_texts``
from this module so ingest and retrieval share one model, one dimension.
"""

from __future__ import annotations

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_DIMENSION = 384  # MiniLM-L6 output size (architecture §5.4)

_model = None


def _get_model():
    """Lazy-singleton fastembed TextEmbedding (loaded once per process)."""
    global _model
    if _model is None:
        from fastembed import TextEmbedding

        _model = TextEmbedding(model_name=MODEL_NAME)
    return _model


def encode_texts(texts: list[str]) -> list[list[float]]:
    """Batch-encode strings into a list of 384-dim float vectors."""
    # fastembed normalizes by default (cosine-ready), matching the old
    # SentenceTransformer(normalize_embeddings=True) behaviour.
    model = _get_model()
    vectors = model.embed(texts, batch_size=32)  # generator of numpy arrays
    return [vector.astype("float32").tolist() for vector in vectors]


if __name__ == "__main__":
    test = encode_texts(
        ["What is the expense ratio of this fund?", "How long is the ELSS lock-in period?"]
    )
    print("model:", MODEL_NAME)
    print("dimension:", len(test[0]))
    print("vectors:", len(test))