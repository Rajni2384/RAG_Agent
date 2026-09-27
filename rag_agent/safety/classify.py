"""Single guardrail gate: PII → advice → performance → None (architecture §7).

None means "safe, proceed to RAG". The original question is never stored,
logged, or embedded when a gate refuses.
"""

from __future__ import annotations

from rag_agent.safety.intent import (
    INTENT_ADVICE,
    INTENT_PERFORMANCE,
    classify_intent,
)
from rag_agent.safety.models import (
    KIND_REFUSAL_ADVICE,
    KIND_REFUSAL_PERFORMANCE,
    KIND_REFUSAL_PII,
    QueryResponse,
)
from rag_agent.safety.pii import detect_pii
from rag_agent.safety.refusals import (
    refusal_advice_response,
    refusal_performance_response,
    refusal_pii_response,
)

# PRD examples (F6/F8) plus factual pass-throughs and extra PII variants.
_EXAMPLES: tuple[tuple[str, str | None], ...] = (
    ("Should I buy this fund?", KIND_REFUSAL_ADVICE),
    ("Which fund gave higher returns?", KIND_REFUSAL_PERFORMANCE),
    ("My PAN is ABCDE1234F, show holdings", KIND_REFUSAL_PII),
    ("My email is raj@example.com, send me the factsheet", KIND_REFUSAL_PII),
    ("Verify my OTP 4829134 before proceeding", KIND_REFUSAL_PII),
    ("What is the expense ratio of HDFC Large Cap Fund Direct Growth?", None),
    ("How long is the ELSS lock-in period?", None),
)


def classify_or_refuse(text: str) -> QueryResponse | None:
    """Return a refusal QueryResponse, or None when the question is factual."""
    pii_kind = detect_pii(text)
    if pii_kind is not None:
        return refusal_pii_response(pii_kind)

    intent = classify_intent(text)
    if intent == INTENT_ADVICE:
        return refusal_advice_response()
    if intent == INTENT_PERFORMANCE:
        return refusal_performance_response(text)

    return None


def _expect(question: str, expected_kind: str | None, failures: list[str]) -> None:
    result = classify_or_refuse(question)
    actual = result.kind if result else None
    status = "PASS" if actual == expected_kind else "FAIL"
    if actual != expected_kind:
        failures.append(question)
    print(f"  [{status}] {question!r}")
    print(f"         -> {actual or 'factual (passes to RAG)'}")
    if result and result.education_url:
        print(f"         -> education_url: {result.education_url}")


if __name__ == "__main__":
    failures: list[str] = []
    for question, expected in _EXAMPLES:
        _expect(question, expected, failures)

    # Refusal texts must never contain the submitted PII.
    pii_result = classify_or_refuse("My PAN is ABCDE1234F, show holdings")
    if pii_result and "ABCDE1234F" in pii_result.text:
        failures.append("PII echoed in refusal text")
        print("  [FAIL] refusal text echoes the PAN")
    else:
        print("  [PASS] refusal text does not echo the PAN")

    # A performance refusal that names a known scheme should carry its URL.
    perf = classify_or_refuse("Which fund gave higher returns?")
    if perf and perf.education_url:
        failures.append("expected generic performance refusal (no scheme named)")
        print("  [FAIL] performance refusal unexpectedly has education_url")
    else:
        print("  [PASS] generic performance refusal has no education_url (scheme not named)")

    named = classify_or_refuse("How did HDFC ELSS Tax Saver Direct Growth perform?")
    if named and named.education_url:
        print("  [PASS] performance refusal points to the named scheme's factsheet")
    else:
        failures.append("named-scheme performance refusal missing factsheet URL")
        print("  [FAIL] named-scheme performance refusal missing factsheet URL")

    print(f"\n{'ALL CHECKS PASSED' if not failures else 'FAILURES: ' + str(failures)}")