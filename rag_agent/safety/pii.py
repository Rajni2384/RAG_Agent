"""PII detection (architecture §5.8). Regex-only, deterministic, no storage."""

from __future__ import annotations

import re

# Order matters: PAN before Aadhaar before bare digit runs.
_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("pan", re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b")),
    (
        "aadhaar",
        re.compile(r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}\b"),
    ),
    ("phone", re.compile(r"(?:\+91[\s-]?)?[6-9]\d{9}\b")),
    ("email", re.compile(r"\b[\w.+-]+@[\w-]+\.[A-Za-z.]+\b")),
    ("otp_like", re.compile(r"\b\d{6,8}\b")),
)

_KIND_LABEL = {
    "pan": "PAN",
    "aadhaar": "Aadhaar",
    "phone": "phone number",
    "email": "email address",
    "otp_like": "verification/OTP code",
}


def detect_pii(text: str) -> str | None:
    """Return the first PII kind found ('pan', 'aadhaar', ...), else None.

    Never returns the matched value itself — callers must not echo it.
    """
    for kind, pattern in _PATTERNS:
        if pattern.search(text):
            return kind
    return None


def pii_label(kind: str) -> str:
    return _KIND_LABEL.get(kind, "personal identifier")