"""HDFC Fund Facts — tiny Streamlit chat UI (Phase 7).

Run:
    streamlit run streamlit_app.py

There is nothing to configure: it calls ask() from Phase 6. Chat history stays
in-memory for the session only; nothing is written to disk.
"""

from __future__ import annotations

import streamlit as st

from rag_agent.app.ask import ask

_EXAMPLES = [
    "What is the expense ratio of HDFC Large Cap Fund Direct Growth?",
    "What is the lock-in for HDFC ELSS Tax Saver?",
    "What is the minimum SIP for HDFC Small Cap Fund Direct Growth?",
]

_DISCLAIMER = (
    "This assistant answers factual questions from public scheme pages only. "
    "It is not investment advice, not a SEBI-registered adviser, and does not "
    "recommend buy, sell, or hold. Do not share PAN, Aadhaar, account numbers, "
    "OTPs, email, or phone numbers."
)

st.set_page_config(page_title="HDFC Fund Facts", page_icon="📊")

st.title("HDFC Fund Facts")
st.markdown("Ask factual questions about five HDFC mutual fund schemes.")
st.caption("**Facts-only. No investment advice.**")

# Session-only chat history (never written to disk).
st.session_state.setdefault("history", [])

# Three clickable examples: fill the input box AND ask immediately.
for example in _EXAMPLES:
    if st.button(example):
        # Set the widget's value through its key (before the widget is
        # instantiated on the next rerun) so the box really fills with it.
        st.session_state["question_input"] = example
        st.session_state["run"] = True

# A form so pressing Enter submits exactly like the Ask button.
with st.form("ask_form"):
    st.text_input(
        "Your question:",
        key="question_input",
        placeholder="e.g. What is the expense ratio of HDFC Large Cap Fund Direct Growth?",
        label_visibility="collapsed",
    )
    submitted = st.form_submit_button("Ask", type="primary")

# The question is read from the widget key itself — never from a stale local.
run = submitted or st.session_state.pop("run", False)
question = (st.session_state.get("question_input") or "").strip()

if run and question:
    st.session_state.history.append((question, "…"))
    try:
        with st.spinner("Searching the index and answering…"):
            result = ask(question)
    except RuntimeError as exc:
        result = str(exc)
        st.error(str(exc))
    st.session_state.history[-1] = (question, result)

for q, res in st.session_state.history:
    st.markdown(f"**You:** {q}")
    if isinstance(res, str):  # still running / error
        st.markdown(f"*{res}*")
        continue
    st.markdown(res.text)
    if res.kind == "answer":
        st.markdown(f"**Source:** [{res.source_url}]({res.source_url})")
        st.caption(f"Last updated from sources: {res.last_updated}")
    elif res.education_url:
        st.markdown(f"**Learn more:** [{res.education_url}]({res.education_url})")
    st.divider()

st.caption(_DISCLAIMER)
st.caption("Answers are grounded in retrieved chunks (RAG).")