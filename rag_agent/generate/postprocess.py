"""Post-process the model output: hard-cap at three sentences (§9)."""

from __future__ import annotations

import re

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


def enforce_three_sentences(text: str) -> str:
    """Normalize whitespace and keep only the first 3 sentences.

    Never trusts any URL the model might have written; citation handling lives
    in cite.py using verified metadata only.
    """
    cleaned = " ".join(text.strip().split())
    sentences = [part for part in _SENTENCE_SPLIT.split(cleaned) if part]
    if len(sentences) <= 3:
        return cleaned
    return " ".join(sentences[:3]).strip()