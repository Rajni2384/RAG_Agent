"""Download Groww scheme HTML into data/snapshots/{scheme_type}.html."""

from __future__ import annotations

import csv

from rag_agent.ingest.load import _http_get
from rag_agent.paths import SNAPSHOTS_DIR, SOURCES_CSV


def save_snapshots() -> None:
    SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    with SOURCES_CSV.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    for row in rows:
        scheme_type = row["scheme_type"].strip()
        url = row["url"].strip()
        html = _http_get(url)
        path = SNAPSHOTS_DIR / f"{scheme_type}.html"
        path.write_text(html, encoding="utf-8")
        print(f"Wrote {path} ({len(html)} bytes) from {url}")


if __name__ == "__main__":
    save_snapshots()
