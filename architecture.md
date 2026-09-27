# Architecture

**Product:** HDFC Mutual Fund FAQ RAG Chatbot  
**Based on:** [PRD.md](./PRD.md)  
**Audience:** Class demo — every RAG stage is a distinct, inspectable step  
**Date:** 27 September 2026

---

## 1. Purpose

This document describes how the facts-only FAQ assistant is built: two pipelines (**ingest** and **query**), the components in each stage, data contracts, and where safety rules run.

It is **not** a single LLM prompt over a whole website. Retrieval happens in ChromaDB; generation is allowed to use **retrieved chunks only**.

---

## 2. System context

```
┌──────────────┐     public HTTP      ┌─────────────────────┐
│ Groww scheme │  (or local snapshot) │ Ingest job          │
│ pages (5)    │ ───────────────────► │ load / chunk / embed│
└──────────────┘                      └──────────┬──────────┘
                                                 │ persist
                                                 ▼
                                      ┌─────────────────────┐
                                      │ ChromaDB            │
                                      │ collection:         │
                                      │ hdfc_mf_faqs        │
                                      └──────────▲──────────┘
                                                 │ query embed + top-k
┌──────────────┐     question         ┌──────────┴──────────┐
│ Demo user    │ ───────────────────► │ Chat app            │
│ (browser)    │ ◄─────────────────── │ guardrails + RAG    │
└──────────────┘     answer + 1 URL   │ + LLM               │
                                      └──────────┬──────────┘
                                                 │ optional
                                                 ▼
                                      ┌─────────────────────┐
                                      │ LLM API or local    │
                                      │ (grounded prompt)   │
                                      └─────────────────────┘
```

**External dependencies**

| Dependency | Role |
|------------|------|
| 5 Groww public URLs (corpus) | Source of scheme facts |
| `sentence-transformers/all-MiniLM-L6-v2` | Same model for chunks and queries |
| ChromaDB (local disk) | Vector index |
| LLM (API or local) | Short grounded answer; no extra world knowledge in the prompt contract |
| Optional: AMFI/SEBI education URL | Used only on **advice refusals** |

No login, no AMC APIs, no user accounts, no PII store.

---

## 3. High-level design: two pipelines

Ingest runs **offline** (script). Query runs **online** (chat UI). They share the embedding model and the Chroma collection.

```
INGEST (batch)
  URLs / snapshots → Load → Clean HTML → Chunk → Embed → Upsert Chroma

QUERY (per request)
  User text → Guardrails → Embed query → Retrieve top-k → Generate → Format (citation + date)
```

If guardrails fire (PII, advice, returns comparison), **skip retrieval and LLM** and return a fixed refusal template.

---

## 4. RAG stages (must remain separate in code)

| Stage | Ingest | Query |
|-------|--------|--------|
| **Loading** | Fetch HTML or read snapshot; extract main text; attach `url`, `scheme_name`, `scheme_type`, `fetched_at` | Load persisted Chroma + embedding model |
| **Chunking** | Heading-first, then recursive split | — |
| **Embedding** | Embed each chunk | Embed the user question |
| **Store** | Write vectors + metadata to Chroma | — |
| **Retrieval** | — | Similarity search `k = 3–5` |
| **Answer** | — | Prompt LLM with chunks only; attach one URL + last-updated |

Class demo: each stage should be a function or module you can point to (not one giant `run_chatbot()` blob).

---

## 5. Component architecture

```
rag_agent/
  ingest/
    load.py          # HTTP or snapshot → Document
    clean.py         # HTML → plain text (main content)
    chunk.py         # heading split + recursive character split
    embed.py         # MiniLM encode
    store.py         # Chroma upsert
    run_ingest.py    # CLI: rebuild index
  retrieve/
    search.py        # embed query + Chroma query
  generate/
    prompt.py        # system + chunks + constraints
    llm.py           # provider wrapper
    cite.py          # pick single source_url + fetched_at
  safety/
    pii.py           # detect PAN / Aadhaar / phone / email / OTP-like
    intent.py        # advice vs returns vs factual
    refusals.py      # canned messages + educational / factsheet links
  app/
    ui.py            # Streamlit/Gradio/FastAPI — welcome, 3 examples, disclaimer
  data/
    sources.csv      # the 5 URLs
    snapshots/       # optional checked-in HTML
    chroma/          # local persist (gitignored)
```

Exact folder names can match the repo when implemented; the **boundaries** above are the architecture.

### 5.1 Load

- Input: URL list from `sources.csv` (and optional snapshot path).  
- Prefer **snapshots** if live fetch is blocked or flaky.  
- Output: `Document { text, url, scheme_name, scheme_type, fetched_at }`.  
- Do not ingest blogs, screenshots, or authenticated pages.

### 5.2 Clean

- Strip nav/footer/boilerplate where practical.  
- Keep headings that name facts (Exit load, Expense ratio, Riskometer, SIP, Benchmark, lock-in).  
- Normalize whitespace so chunking separators work (`\n\n`, `\n`).

### 5.3 Chunk

**Strategy (from PRD):** section-aware recursive character split.

1. Split on headings when present (`Exit Load`, `Riskometer`, …).  
2. If a section is still large, recursive split: paragraph → sentence → character.  
3. **Size:** 400–600 characters. **Overlap:** 80–100 characters.  
4. Prepend `Scheme: {name} | Type: {type}` to the stored chunk text.  
5. Attach metadata: `source_url`, `scheme_name`, `chunk_id`, `fetched_at`.

Do not store one embedding per entire page.

### 5.4 Embed

- Model: `sentence-transformers/all-MiniLM-L6-v2`.  
- Ingest: encode chunk strings once.  
- Query: encode the **same** user string after guardrails pass (no PII in the embed path).  
- Dimension: 384 (MiniLM-L6). Chroma collection must match.

### 5.5 Vector store

- **ChromaDB**, persist directory on disk (e.g. `data/chroma`).  
- Collection: `hdfc_mf_faqs`.  
- Each item: `id` (chunk_id), `embedding`, `document` (chunk text), `metadata`.  
- Rebuild: delete collection or `reset` then re-run ingest (demo-scale; no incremental sync required).

### 5.6 Retrieve

- Query embedding → `collection.query(n_results=4)` (range 3–5).  
- Return list of `{ text, source_url, scheme_name, fetched_at, distance }`.  
- No reranker in v1 (keep the demo small). Optional later: filter metadata by `scheme_name` if the question names a scheme.

### 5.7 Generate

- Prompt contract:
  - Use **only** the retrieved texts.
  - ≤ 3 sentences.
  - Facts only; no advice; no return calculations.
  - If chunks do not contain the fact: say the index does not have it.
- **Citation:** exactly one URL — `source_url` of the top hit (or the chunk that supports the stated fact).  
- **Freshness:** `Last updated from sources: {max fetched_at among used chunks}` (or ingest run date).  
- LLM keys live in `.env`; never in git.

### 5.8 Safety (before RAG)

| Gate | Detection (v1) | Action |
|------|----------------|--------|
| PII | Regex: PAN, Aadhaar, phone, email, long digit sequences / OTP-like | Refuse; do not log the message body; do not embed |
| Advice | Keywords / phrases: should I buy/sell, best fund, allocate, recommend | Refuse + AMFI/SEBI education link |
| Performance | returns, CAGR, outperformed, which did better | Refuse compute; link factsheet / scheme page disclosure |
| Else | Treat as factual RAG | Retrieve + generate |

Guardrails are **deterministic** so the class can show “RAG is not even called” for unsafe asks.

### 5.9 UI

- Welcome line + three example questions + persistent *Facts-only. No investment advice.*  
- Input box → answer text + one hyperlink + last-updated line.  
- Chat history **in memory only** for the session.  
- Optional footer: “Answer grounded in retrieved chunks (RAG).”

---

## 6. Data model

### 6.1 Source row (`sources.csv`)

| Field | Example |
|-------|---------|
| `scheme_type` | `large_cap` |
| `scheme_name` | `HDFC Large Cap Fund Direct Growth` |
| `url` | `https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth` |

### 6.2 Document (after load)

```
url, scheme_name, scheme_type, fetched_at, raw_html?, text
```

### 6.3 Chunk (Chroma metadata)

```
chunk_id:        string   # e.g. hdfc_large_cap_003
source_url:      string
scheme_name:     string
scheme_type:     string
fetched_at:      string   # ISO date
```

Document field in Chroma = prefixed chunk text.

### 6.4 Query response (API/UI)

```
kind:            "answer" | "refusal_pii" | "refusal_advice" | "refusal_performance" | "not_found"
text:            string   # ≤ 3 sentences for answers
source_url:      string | null   # required for kind == answer
last_updated:    string | null
education_url:   string | null   # refusals
```

---

## 7. Query sequence

```
User submits question
        │
        ▼
   PII check ──yes──► refusal_pii (stop)
        │ no
        ▼
   Intent check ──advice──► refusal_advice + education URL (stop)
        │
        ├──performance──► refusal_performance + factsheet URL (stop)
        │
        ▼ factual
   Embed question (MiniLM)
        │
        ▼
   Chroma top-k
        │
        ├── empty / low relevance──► not_found (no invented facts)
        │
        ▼
   LLM(prompt = rules + chunks)
        │
        ▼
   cite.py picks one URL + last_updated
        │
        ▼
   UI renders answer
```

---

## 8. Ingest sequence

```
Read sources.csv
  for each URL:
    load snapshot or GET
    clean → text
    chunk (headings + recursive)
    embed MiniLM
  upsert all into hdfc_mf_faqs
  write ingest_manifest.json  # run time, URL list, chunk count
```

`fetched_at` on chunks should match this run (or HTTP `Last-Modified` if used). The UI’s “Last updated from sources” comes from this metadata, not “today’s date” unless they coincide.

---

## 9. Prompt sketch (generation)

System / instruction block (fixed):

- You are a facts-only mutual fund FAQ assistant for five HDFC schemes.  
- Answer using **only** CONTEXT.  
- At most three sentences.  
- No buy/sell/hold, no portfolio advice, no computed returns.  
- If CONTEXT is insufficient, say so.  
- Do not invent expense ratios, loads, or lock-in periods.

User block:

- `QUESTION: ...`  
- `CONTEXT:` numbered chunks with `source_url` and `scheme_name` each.

Post-process in code (do not trust the model alone):

- Truncate to three sentences if needed.  
- Attach citation from retrieval metadata, not from a URL the model invented.  
- Append `Last updated from sources: YYYY-MM-DD`.

---

## 10. Suggested runtime (demo)

| Piece | Choice |
|-------|--------|
| Language | Python 3.11+ |
| Embeddings | `sentence-transformers` |
| Vectors | `chromadb` |
| UI | Streamlit or Gradio (fastest for class) |
| LLM | Instructor-allowed API **or** a small local model |
| Config | `.env` for API keys; `sources.csv` for corpus |

Open decisions from the PRD (provider, live vs snapshot, extra AMC PDFs) do not change this diagram; they only change `load.py` and `llm.py`.

---

## 11. Non-goals (architecture)

- Production auth, rate limits, multi-tenant Chroma.  
- Streaming crawl / scheduled re-ingest (manual `run_ingest.py` is enough).  
- Cross-encoder rerank, hybrid BM25 (optional homework, not required).  
- Storing chat logs or any identifier.  
- Calling tools that compute NAV history or returns.

---

## 12. Mapping to PRD requirements

| PRD | Architecture |
|-----|----------------|
| F1 Chat Q&A | UI → retrieve → generate |
| F2 One citation | `cite.py` uses chunk `source_url` |
| F3 Last updated | Chunk `fetched_at` / ingest manifest |
| F4 ≤ 3 sentences | Prompt + post-process |
| F5 Tiny UI | `app/ui.py` |
| F6–F8 Safety | `safety/` before RAG |
| F9 Unknown | Low-similarity / empty context → `not_found` |
| Visible RAG stages | Separate ingest vs query modules (§4–§5) |

---

## 13. Risks

| Risk | Mitigation |
|------|------------|
| Groww HTML changes / scrape blocked | Checked-in snapshots |
| Chunk mixes two facts | Heading-first split, small chunk size |
| Wrong scheme retrieved | Scheme prefix on chunks; optional metadata filter |
| LLM ignores context | Strict prompt + citation from metadata + not_found path |
| Stale TER / load | Show ingest date; re-run ingest before demo |
