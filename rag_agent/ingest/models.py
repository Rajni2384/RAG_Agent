from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass
class Document:
    url: str
    scheme_name: str
    scheme_type: str
    fetched_at: date
    text: str
    raw_html: str | None = None
