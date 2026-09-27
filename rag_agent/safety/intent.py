"""Question intent: advice | performance | factual (architecture §5.8)."""

from __future__ import annotations

import re

INTENT_ADVICE = "advice"
INTENT_PERFORMANCE = "performance"
INTENT_FACTUAL = "factual"

# Advice: buying/selling/allocating/portfolio questions.
_ADVICE_PATTERNS = (
    re.compile(r"\bshould i (buy|sell|invest|hold|redeem|switch|allocate)\b"),
    re.compile(r"\bis it (good|wise|safe|worth).*?(buy|invest|add)\b"),
    re.compile(r"\bbuy\b"),
    re.compile(r"\bsell\b"),
    re.compile(r"\bredeem\b"),
    re.compile(r"\bswitch\b"),
    re.compile(r"\bbest fund\b"),
    re.compile(r"\brecommend"),
    re.compile(r"\ballocate\b|\basset allocation\b"),
    re.compile(r"\badd (more|money|lumpsum|sip)\b"),
)

# Performance: computing, ranking, or comparing returns.
_PERFORMANCE_PATTERNS = (
    re.compile(r"\breturns?\b"),
    re.compile(r"\bcagr\b"),
    re.compile(r"\boutperform"),
    re.compile(r"\bperform(ed|s|ance)?\b"),
    re.compile(r"\bdid better\b"),
    re.compile(r"\bwhich (is|was) better\b"),
    re.compile(r"\bhigher returns?\b"),
    re.compile(r"\bbeat(ing)? (the )?(fund|market|index)\b"),
)


def classify_intent(text: str) -> str:
    """Advice is checked first (architecture §7), then performance, else factual."""
    lowered = text.lower()
    if any(pattern.search(lowered) for pattern in _ADVICE_PATTERNS):
        return INTENT_ADVICE
    if any(pattern.search(lowered) for pattern in _PERFORMANCE_PATTERNS):
        return INTENT_PERFORMANCE
    return INTENT_FACTUAL


def is_advice(text: str) -> bool:
    return classify_intent(text) == INTENT_ADVICE


def is_performance(text: str) -> bool:
    return classify_intent(text) == INTENT_PERFORMANCE