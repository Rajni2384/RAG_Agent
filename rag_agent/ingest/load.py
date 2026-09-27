"""Load scheme pages from snapshots or HTTP (Phase 1)."""

from __future__ import annotations

import csv
from datetime import date, datetime, timezone
from pathlib import Path

import requests

from rag_agent.ingest.clean import html_to_text
from rag_agent.ingest.models import Document
from rag_agent.paths import SNAPSHOTS_DIR, SOURCES_CSV

USER_AGENT = (
    "Mozilla/5.0 (compatible; RAG-Agent-class-demo/1.0; "
    "+https://github.com/) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)
REQUEST_TIMEOUT_SEC = 30
MIN_USEFUL_TEXT_CHARS = 200


class SourceLoadError(RuntimeError):
    """Raised when a single scheme page cannot be loaded or cleaned."""


def load_all_documents(
    sources_csv: Path | None = None,
    snapshots_dir: Path | None = None,
    *,
    save_snapshot_on_fetch: bool = True,
) -> list[Document]:
    csv_path = sources_csv or SOURCES_CSV
    snap_dir = snapshots_dir or SNAPSHOTS_DIR
    snap_dir.mkdir(parents=True, exist_ok=True)

    rows = _read_sources(csv_path)
    documents: list[Document] = []
    errors: list[str] = []

    for row in rows:
        try:
            documents.append(
                _load_one(row, snap_dir, save_snapshot_on_fetch=save_snapshot_on_fetch)
            )
        except Exception as exc:  # noqa: BLE001 — report every row, then fail
            errors.append(f"{row['scheme_type']} ({row['url']}): {exc}")

    if errors:
        detail = "\n".join(f"  - {e}" for e in errors)
        raise SourceLoadError(
            f"Failed to load {len(errors)} of {len(rows)} sources:\n{detail}"
        )
    return documents


def _read_sources(csv_path: Path) -> list[dict[str, str]]:
    if not csv_path.is_file():
        raise FileNotFoundError(f"Sources CSV not found: {csv_path}")
    with csv_path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
    required = {"scheme_type", "scheme_name", "url"}
    if not rows:
        raise SourceLoadError(f"No rows in {csv_path}")
    missing = required - set(rows[0].keys())
    if missing:
        raise SourceLoadError(f"{csv_path} missing columns: {sorted(missing)}")
    return rows


def _load_one(
    row: dict[str, str],
    snap_dir: Path,
    *,
    save_snapshot_on_fetch: bool,
) -> Document:
    scheme_type = row["scheme_type"].strip()
    scheme_name = row["scheme_name"].strip()
    url = row["url"].strip()
    snapshot_path = snap_dir / f"{scheme_type}.html"

    if snapshot_path.is_file():
        html = snapshot_path.read_text(encoding="utf-8")
        fetched_at = date.fromtimestamp(snapshot_path.stat().st_mtime)
        source = "snapshot"
    else:
        html = _http_get(url)
        fetched_at = datetime.now(timezone.utc).date()
        source = "http"
        if save_snapshot_on_fetch:
            snapshot_path.write_text(html, encoding="utf-8")

    text = html_to_text(html)
    if len(text) < MIN_USEFUL_TEXT_CHARS:
        raise SourceLoadError(
            f"{source} produced only {len(text)} characters of text "
            f"(need >= {MIN_USEFUL_TEXT_CHARS}). Page may be JS-only or blocked."
        )

    return Document(
        url=url,
        scheme_name=scheme_name,
        scheme_type=scheme_type,
        fetched_at=fetched_at,
        text=text,
        raw_html=html,
    )


def _http_get(url: str) -> str:
    response = requests.get(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-IN,en;q=0.9",
        },
        timeout=REQUEST_TIMEOUT_SEC,
    )
    response.raise_for_status()
    response.encoding = response.apparent_encoding or "utf-8"
    return response.text


def _print_summary(documents: list[Document]) -> None:
    for doc in documents:
        print(f"{doc.scheme_name}\t{doc.scheme_type}\t{len(doc.text)}\t{doc.url}")


if __name__ == "__main__":
    docs = load_all_documents()
    _print_summary(docs)
