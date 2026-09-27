"""Canned refusal messages + education/factsheet links (architecture §5.8)."""

from __future__ import annotations

import csv

from rag_agent.paths import SOURCES_CSV
from rag_agent.safety.models import (
    KIND_REFUSAL_ADVICE,
    KIND_REFUSAL_PERFORMANCE,
    KIND_REFUSAL_PII,
    QueryResponse,
)
from rag_agent.safety.pii import pii_label

# One AMFI / SEBI investor-education portal for the advice gate.
AMFI_EDUCATION_URL = "https://www.amfiindia.com/"
SEBI_EDUCATION_URL = "https://www.sebi.gov.in/"

# Generic pointer when the question names no known scheme (performance gate).
_FACTSHEET_NOTE = (
    "See the official factsheet on the scheme's page (such as Groww's scheme page) "
    "for verified historical figures."
)

_PII_MESSAGE = (
    "I can't process personal identifiers like {label}s — please don't share PAN, "
    "Aadhaar, account numbers, OTPs, emails, or phone numbers here. I don't store "
    "or answer with them; keep them safe instead."
)

_ADVICE_MESSAGE = (
    "I'm a facts-only assistant and can't give investment advice or tell you "
    "whether to buy, sell, or hold. Please consult a SEBI-registered investment "
    "adviser."
)

_PERFORMANCE_MESSAGE = (
    "I don't compute or compare fund returns or performance. " + _FACTSHEET_NOTE
)


def refusal_pii_response(pii_kind: str) -> QueryResponse:
    """Refuse without echoing the identifier (never log/embed the message)."""
    return QueryResponse(
        kind=KIND_REFUSAL_PII,
        text=_PII_MESSAGE.format(label=pii_label(pii_kind)),
    )


def refusal_advice_response() -> QueryResponse:
    return QueryResponse(
        kind=KIND_REFUSAL_ADVICE,
        text=_ADVICE_MESSAGE,
        education_url=SEBI_EDUCATION_URL,
    )


def refusal_performance_response(question: str) -> QueryResponse:
    """Point to the named scheme's Groww factsheet when known; else generic note."""
    url = _scheme_url_in(question)
    return QueryResponse(
        kind=KIND_REFUSAL_PERFORMANCE,
        text=_PERFORMANCE_MESSAGE,
        education_url=url,
    )


def _scheme_url_in(question: str) -> str | None:
    """Return the source URL of the first known scheme named in ``question``."""
    lowered = question.lower()
    with SOURCES_CSV.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            if row["scheme_name"].lower() in lowered:
                return row["url"]
    return None