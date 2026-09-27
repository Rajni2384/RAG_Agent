# HDFC Fund Facts — RAG chatbot (milestone)

A **facts-only** RAG chatbot that answers factual questions about five HDFC
mutual fund schemes. It retrieves from a local Chroma index built from public
Groww scheme pages, then answers strictly from the retrieved chunks — with one
citation per answer.

> **Disclaimer:** This assistant answers factual questions from public scheme
> pages only. It is not investment advice, not a SEBI-registered adviser, and
> does not recommend buy, sell, or hold. Do not share PAN, Aadhaar, account
> numbers, OTPs, email, or phone numbers.

---

## Quick start

Requires **Python 3.12** (built and tested on 3.12.13).

```bash
# 1) Create and activate a virtual environment
python -m venv .venv
# Windows:      .venv\Scripts\activate
# macOS/Linux:  source .venv/bin/activate

# 2) Install dependencies
pip install -r requirements.txt

# 3) Configure the LLM — copy the template and fill in an API key
cp .env.example .env      # Windows: copy .env.example .env
```

`.env` needs three values (never commit this file):

| Key | Example |
|-----|---------|
| `LLM_API_KEY` | your OpenAI-compatible API key |
| `LLM_MODEL` | `openai/gpt-oss-20b` (any OpenAI-compatible model works) |
| `LLM_BASE_URL` | `https://api.groq.com/openai/v1` (Groq) — omit for OpenAI |

### Build the index (one time)

```bash
python -m rag_agent.ingest.run_ingest
```

This loads the 5 saved HTML snapshots (`data/snapshots/`), cleans them, splits
into ~409 chunks, embeds with `all-MiniLM-L6-v2`, and persists the vectors into
`data/chroma/`. On first run it also downloads the MiniLM ONNX model (~83 MB).
The embedder runs on **ONNX Runtime (fastembed), no PyTorch**, so the whole app
sits at ~250 MB RAM and fits Render's free 512 MB plan. Reruns do **not**
duplicate chunks. A copy of every chunk + its embedding, readable as text, is
written to `data/chunks_export.txt` (via
`python -m rag_agent.ingest.export_chunks`).

### Run the chat UI

```bash
streamlit run streamlit_app.py
```

Opens at http://localhost:8501 — welcome line, three clickable example
questions, answer + source link + last-updated line, in-memory session chat
only (nothing written to disk).

### Ask from the command line (no UI)

```bash
python -m rag_agent.app.ask "What is the lock-in for HDFC ELSS Tax Saver?"
```

### Deploy on Render (free plan — fits in 512 MB)

Push the repo to GitHub, create a **Web Service** from it, and use:

| Setting | Value |
|---|---|
| Root Directory | *(leave empty — repo root)* |
| Python version | `3.12` — pinned by `.python-version` in the repo (**required**: Render's default 3.14 can't install `fastembed==0.8.1` + `streamlit==1.49.1` — pillow conflict) |
| Build Command | `python -m pip install --upgrade pip && pip install -r requirements.txt && python -m rag_agent.ingest.run_ingest` |
| Start Command | `streamlit run streamlit_app.py --server.address 0.0.0.0 --server.port $PORT --server.headless true` |

Environment variables: `LLM_API_KEY`, `LLM_MODEL` (`openai/gpt-oss-20b`),
`LLM_BASE_URL` (`https://api.groq.com/openai/v1`). The build command bakes the
Chroma index + the ONNX model into the image, so the runtime needs no
downloads. First question after a cold start is slower (one-time model load);
later ones are under a second.

---

## The five schemes (HDFC Mutual Fund)

| Type | Scheme | Source |
|------|--------|--------|
| Large cap | HDFC Large Cap Fund Direct Growth | [Groww](https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth) |
| Flexi cap | HDFC Flexi Cap Fund Direct Growth | [Groww](https://groww.in/mutual-funds/hdfc-equity-fund-direct-growth) |
| ELSS | HDFC ELSS Tax Saver Direct Growth | [Groww](https://groww.in/mutual-funds/hdfc-elss-tax-saver-fund-direct-plan-growth) |
| Small cap | HDFC Small Cap Fund Direct Growth | [Groww](https://groww.in/mutual-funds/hdfc-small-cap-fund-direct-growth) |
| Hybrid | HDFC Balanced Advantage Fund Direct Growth | [Groww](https://groww.in/mutual-funds/hdfc-balanced-advantage-fund-direct-growth) |

Machine-readable copy: `data/sources.csv`. Human-readable copy: `SOURCES.md`.

---

## How it works (pipeline)

| Phase | Module | What it does |
|-------|--------|--------------|
| 1. Load / clean | `rag_agent/ingest/load.py` | Read saved HTML snapshots → plain text documents |
| 2. Chunk | `rag_agent/ingest/chunk.py` | 400–600-char chunks, 80–100 overlap, scheme prefix + metadata |
| 3. Embed / store | `rag_agent/ingest/embed.py`, `store.py` | `all-MiniLM-L6-v2` via ONNX (fastembed, no PyTorch) → 384-dim vectors → persistent Chroma collection `hdfc_mf_faqs` |
| 4. Retrieve | `rag_agent/retrieve/search.py` | Top-4 nearest chunks (capped at distance ≤ 0.70) |
| 5. Guardrails | `rag_agent/safety/` | Refuses advice, performance, and PII **before** any retrieval |
| 6. Generate / cite | `rag_agent/generate/` + `rag_agent/app/ask.py` | LLM answers from retrieved chunks only, ≤ 3 sentences, one citation |
| 7. UI | `streamlit_app.py` | Streamlit chat calling `ask()` |

## Safety behaviour

- **`refusal_advice`** — "Should I buy this fund?" → refused, points to a
  SEBI-registered adviser, no buy/sell/hold language.
- **`refusal_performance`** — "Which fund gave higher returns?" → no computed
  comparison; points to the scheme's official factsheet.
- **`refusal_pii`** — PAN/Aadhaar/account/OTP → refused without echoing the PII.
- **`not_found`** — anything outside the corpus → offered factual topic hints.
- Answers are capped at 3 sentences and must carry exactly one citation.

---

## Known limits

- **Facts can go stale.** Freshness = the last ingest date
  ("Last updated from sources: 2026-09-27"), *not* a live AMC API. Rebuild the
  index with `run_ingest` after AMC updates TER/exit loads.
- **Groww is an aggregator** of public scheme data. For a stricter "official"
  story, later snapshots could be taken from HDFC AMC factsheets/KIMs.
- **MiniLM is English-centric and small**; Hindi or code-mixed queries may
  retrieve poorly.
- **Prototype, not SEBI-complete disclosure.** No guarantee of complete or
  investment-grade information. LLM output is grounded in retrieved chunks, but
  treat every answer as a starting point, not a filing.
- **Statement / tax-document questions** are out of corpus (no personal
  accounts are linked); the assistant will say it cannot find that information.

## Reproducibility

- Python 3.12 · pinned deps in `requirements.txt`
- Deterministic reruns: ingest is idempotent, vector count stays 409
- Full source history in `PRD.md`, `architecture.md`, `implementation.md`
- Chunks + embeddings are inspectable in `data/chunks_export.txt`