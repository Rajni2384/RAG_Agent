"""Heading-first, then recursive character splitting (Phase 2)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date

from rag_agent.ingest.models import Document

# Size band and overlap from PRD §8.2 / architecture §5.3.
MIN_CHUNK = 400
MAX_CHUNK = 600
CHUNK_OVERLAP = 90

_SEPARATORS = ("\n\n", "\n", ". ", " ")

# Fact labels that mark the start of a section on Groww scheme pages.
_HEADING_HINTS = (
    "expense",
    "exit load",
    "exit",
    "load",
    "sip",
    "lumpsum",
    "lock-in",
    "lock",
    "riskometer",
    "risk",
    "benchmark",
    "nav",
    "aum",
    "min.",
    "minimum",
    "min",
    "tenure",
    "rating",
    "returns",
    "return",
    "objective",
    "fund house",
    "fund manager",
    "portfolio",
    "holdings",
    "holding",
    "sector",
    "instruments",
    "assets",
    "name",
    "category",
    "scheme",
    "fund",
    "elss",
    "tax",
    "statement",
    "cagr",
    "growth",
    "distribution",
    "launch",
    "type",
    "plan",
)


@dataclass
class Chunk:
    """One retrievable unit, ready for embedding (Phase 3)."""

    chunk_id: str
    source_url: str
    scheme_name: str
    scheme_type: str
    fetched_at: date
    text: str  # prefixed text: "Scheme: {name} | Type: {type}\n\n{content}"


def chunk_document(doc: Document) -> list[Chunk]:
    """Chunk a single Document into prefixed, sized chunks."""
    sections = _split_sections(doc.text)
    contents = _coalesce_sections(sections)

    chunks: list[Chunk] = []
    for index, content in enumerate(contents):
        prefix = f"Scheme: {doc.scheme_name} | Type: {doc.scheme_type}"
        chunks.append(
            Chunk(
                chunk_id=f"{doc.scheme_type}_{index:03d}",
                source_url=doc.url,
                scheme_name=doc.scheme_name,
                scheme_type=doc.scheme_type,
                fetched_at=doc.fetched_at,
                text=f"{prefix}\n\n{content}",
            )
        )
    return chunks


def chunk_documents(documents: list[Document]) -> list[Chunk]:
    """Convenience: chunk every document in a list."""
    chunks: list[Chunk] = []
    for doc in documents:
        chunks.extend(chunk_document(doc))
    return chunks


# --------------------------------------------------------------------------
# Sectioning: split the flat text at fact-heading boundaries.
# --------------------------------------------------------------------------


def _split_sections(text: str) -> list[str]:
    """Group lines into sections, starting each new section at a fact heading."""
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    sections: list[str] = []
    current: list[str] = []

    def flush() -> None:
        if current:
            sections.append("\n".join(current))
            current.clear()

    for line in lines:
        if _is_heading(line):
            flush()
            current.append(line)
        else:
            current.append(line)
    flush()
    return sections or [text]


def _is_heading(line: str) -> bool:
    """A short, label-like line that names a fact (per _HEADING_HINTS)."""
    if not line or len(line) > 60:
        return False
    # Real headings are labels, not sentences. Reject anything sentence-like.
    if re.search(r"[\?\:;,]\.?$", line):
        return False
    if line.endswith((".", "!", "?")):
        return False
    lowered = line.lower()
    return any(hint in lowered for hint in _HEADING_HINTS)


# --------------------------------------------------------------------------
# Coalescing + recursive split: size to 400–600, never one blob per page.
# --------------------------------------------------------------------------


def _coalesce_sections(sections: list[str]) -> list[str]:
    """Group small sections into 400–600 char units; split oversized ones."""
    chunks: list[str] = []
    buffer = ""

    for section in sections:
        if len(section) > MAX_CHUNK:
            if buffer:
                chunks.append(buffer)
                buffer = ""
            chunks.extend(_recursive_split(section))
        elif not buffer:
            buffer = section
        elif len(buffer) + 2 + len(section) <= MAX_CHUNK:
            buffer = f"{buffer}\n\n{section}"
        else:
            chunks.append(buffer)
            buffer = section

    if buffer:
        chunks.append(buffer)
    return chunks


def _recursive_split(text: str) -> list[str]:
    """Split text longer than MAX_CHUNK using the best separator, with overlap."""
    return _split_inner(text)


def _split_inner(text: str) -> list[str]:
    if len(text) <= MAX_CHUNK:
        return [text]

    join_sep: str | None = None
    parts: list[str] = []

    for sep in _SEPARATORS:
        if sep not in text:
            continue
        candidate = [p for p in text.split(sep) if p]
        if candidate and max(len(p) for p in candidate) <= MAX_CHUNK:
            join_sep = sep
            parts = candidate
            break

    if join_sep is None:
        # No separator breaks it finely enough — hard character cut (rare).
        return [text[i : i + MAX_CHUNK] for i in range(0, len(text), MAX_CHUNK)]

    out: list[str] = []
    for part in parts:
        if len(part) <= MAX_CHUNK:
            out.append(part)
        else:
            out.extend(_split_inner(part))
    return _merge_with_overlap(out, join_sep)


def _merge_with_overlap(parts: list[str], join_sep: str) -> list[str]:
    """Merge parts back up to MAX_CHUNK, carrying an overlap tail between chunks."""
    chunks: list[str] = []
    current = ""

    for part in parts:
        if not current:
            current = part
            continue
        if len(current) + len(join_sep) + len(part) <= MAX_CHUNK:
            current = f"{current}{join_sep}{part}"
        else:
            chunks.append(current)
            tail = current[-CHUNK_OVERLAP:] if len(current) > CHUNK_OVERLAP else current
            current = f"{tail}{join_sep}{part}"
            if len(current) > MAX_CHUNK:  # overlap made it oversized — drop it
                current = part

    if current:
        chunks.append(current)
    return chunks


if __name__ == "__main__":
    from rag_agent.ingest.load import load_all_documents

    for doc in load_all_documents():
        chunks = chunk_document(doc)
        lengths = [len(c.text) for c in chunks]
        sized = [len(c.text) - len(c.text.split("\n\n", 1)[0]) - 2 for c in chunks]
        print(
            f"{doc.scheme_type:<11} chunks={len(chunks):<4} "
            f"raw min={min(sized):<4} raw max={max(sized):<4} "
            f"raw avg={sum(sized) // max(len(sized), 1):<4} "
            f"prefixed max={max(lengths)}"
        )