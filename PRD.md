# Product Requirements Document (PRD)

**Product:** HDFC Mutual Fund FAQ RAG Chatbot  
**Audience:** Class demo / milestone prototype  
**Status:** Draft  
**Date:** 27 September 2026

---

## 1. Overview

Build a small **facts-only** FAQ assistant that answers questions about selected HDFC mutual fund schemes (expense ratio, exit load, minimum SIP, ELSS lock-in, riskometer, benchmark, how to download statements/tax docs). Answers must come from official public pages (or the listed Groww scheme pages used as the public corpus for this demo), include **one source link**, and never give investment advice.

This is a **RAG chatbot**: ingest public pages, retrieve relevant chunks, then generate a short grounded answer.

---

## 2. Problem

Retail users and support/content teams repeatedly ask the same scheme facts. Manual lookup across factsheets, KIM/SID, and FAQ pages is slow. The demo shows a retrieval-grounded assistant that:

- Answers only from a scoped corpus
- Cites a source on every reply
- Refuses advice, performance comparison, and PII

---

## 3. Goals and success

| Goal | Success signal |
|------|----------------|
| Factual Q&A on 5 HDFC schemes | Correct answers for sample queries (expense ratio, SIP, exit load, lock-in, riskometer/benchmark, statement download) |
| Grounded generation | Every answer includes **one citation URL** |
| Transparency | Answers ≤ 3 sentences; include **Last updated from sources: &lt;date&gt;** |
| Safety | Advice / buy-sell / returns-comparison refused; no PII stored |
| Pedagogy | Pipeline visibly covers **Loading → Chunking → Embedding → Vector store → Retrieval → Answer** |

**Out of success:** beating a commercial chatbot, live AMC login, personalized portfolios, or computing returns.

---

## 4. Users

| User | Need |
|------|------|
| **Retail investor (demo persona)** | Compare scheme **facts**, not recommendations |
| **Support / content (demo persona)** | Repeatable answers with a source link |
| **Instructor / classmates** | See a working RAG path and constraints (no advice, citations) |

---

## 5. Scope

### 5.1 In scope

- **AMC:** HDFC Mutual Fund  
- **Schemes (5):**

| Type | Scheme (Groww public page) |
|------|----------------------------|
| Large Cap | [HDFC Large Cap Fund – Direct Growth](https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth) |
| Flexi Cap | [HDFC Flexi Cap Fund (listed as Equity Fund) – Direct Growth](https://groww.in/mutual-funds/hdfc-equity-fund-direct-growth) |
| ELSS | [HDFC ELSS Tax Saver – Direct Growth](https://groww.in/mutual-funds/hdfc-elss-tax-saver-fund-direct-plan-growth) |
| Small Cap | [HDFC Small Cap Fund – Direct Growth](https://groww.in/mutual-funds/hdfc-small-cap-fund-direct-growth) |
| Hybrid | [HDFC Balanced Advantage Fund – Direct Growth](https://groww.in/mutual-funds/hdfc-balanced-advantage-fund-direct-growth) |

- Ingest those pages (and, if added later, corresponding public AMC/SEBI/AMFI factsheet, KIM/SID, FAQ, charges, riskometer, statement/tax-doc pages).  
- Chat UI: welcome line, **3 example questions**, disclaimer.  
- Retrieval + LLM (or extractive) answer with citation.  
- Refuse opinionated / portfolio questions with a polite facts-only message + educational link.  
- Deliverables listed in §11.

### 5.2 Out of scope

- Advice (“Should I buy/sell?”, asset allocation, “best fund”).  
- Computing or ranking **returns** / performance; if asked, refuse and **link the official factsheet** (or scheme page factsheet section).  
- Login, KYC, transactions, holdings.  
- Storing PAN, Aadhaar, account numbers, OTPs, emails, phones.  
- Third-party blogs as **sources**.  
- Screenshots of any app back-end as corpus.  
- Multi-AMC corpus, streaming ingestion, production auth, analytics.

---

## 6. Product principles

1. **Public sources only** for citations.  
2. **No PII** — reject and do not persist identifiers.  
3. **No performance claims** — do not calculate or compare returns.  
4. **Clarity** — ≤ 3 sentences; always cite; always show source freshness.  
5. **Facts-only** — if the corpus does not contain the fact, say so rather than guessing.

---

## 7. Functional requirements

### 7.1 Chat

| ID | Requirement |
|----|-------------|
| F1 | User can type a question and receive an answer about in-scope schemes. |
| F2 | Every successful factual answer includes **exactly one** primary source URL. |
| F3 | Every answer includes **Last updated from sources: YYYY-MM-DD** (ingest/source date). |
| F4 | Body of the answer is **≤ 3 sentences**. |
| F5 | UI shows a welcome line, **3 starter questions**, and: *Facts-only. No investment advice.* |
| F6 | Advice / buy-sell / “which is better” / portfolio construction → refuse with a short polite message and one **educational** link (e.g. AMFI/SEBI investor education), not a recommendation. |
| F7 | Returns / CAGR / “which performed better” → do not compute; point to factsheet / official performance disclosure URL. |
| F8 | Messages containing PAN, Aadhaar, account/OTP/email/phone patterns → refuse, do not store, remind user not to share PII. |
| F9 | Unknown scheme or fact not in corpus → “I don’t have that in the indexed sources” + invite a scheme-fact question. |

### 7.2 Example starter questions (UI)

1. What is the expense ratio of HDFC Large Cap Fund Direct Growth?  
2. What is the lock-in for HDFC ELSS Tax Saver?  
3. What is the minimum SIP for HDFC Small Cap Fund Direct Growth?

(Copy may be adjusted; keep three visible examples.)

### 7.3 Query types to support

- Expense ratio  
- Exit load  
- Minimum SIP / lump sum (if on page)  
- ELSS lock-in  
- Riskometer  
- Benchmark  
- How to download statements / capital-gains / tax documents (process as published; no account access)

---

## 8. RAG architecture (class demo)

The product **must** implement a visible pipeline, not a single black-box prompt over the whole site.

```
Public pages  →  Load  →  Chunk  →  Embed  →  Vector store
                                                      ↓
User question  →  Embed query  →  Retrieve top-k  →  Grounded answer + citation
```

### 8.1 Loading

- Fetch (or snapshot) the 5 Groww scheme URLs as HTML; extract main scheme content (name, key facts, FAQ-like sections).  
- Persist raw or cleaned text plus metadata: `url`, `scheme_name`, `scheme_type`, `fetched_at`.  
- Optional later: extra official PDFs/HTML from AMC/AMFI/SEBI — same metadata pattern.  
- Respect robots/ToS for a class demo; prefer saved snapshots if live scrape is blocked.

### 8.2 Chunking strategy (chosen for this corpus)

Groww scheme pages are **semi-structured**: headings + short fact blocks (ratios, loads, SIP, risk, benchmark), not long narrative books.

**Strategy: recursive character split, section-aware when possible.**

| Parameter | Choice | Why |
|-----------|--------|-----|
| Splitter | Recursive (paragraph → sentence → character) | Keeps fact sentences together; falls back if a block is huge |
| Target size | **~400–600 characters** (~100–150 tokens) | Facts are short; large chunks mix expense ratio with unrelated FAQ |
| Overlap | **80–100 characters** | Avoids cutting “exit load of X% if redeemed within Y days” |
| Separators | `\n\n`, `\n`, `. `, space | Matches HTML-converted text |
| Enrichment | Prepend `Scheme: {name} | Type: {type}` to each chunk | Retrieval for “ELSS lock-in” hits the right fund |
| Metadata | `source_url`, `scheme_name`, `chunk_id`, `fetched_at` | Citation = chunk’s `source_url` |

**Do not** use one-chunk-per-entire-page (hurts retrieval) or tiny 50-char chunks (hurts context).

If a page has clear headings (e.g. “Exit Load”, “Riskometer”), split **on those headings first**, then apply the size cap only if a section is still too large.

### 8.3 Embedding

- **Model:** `sentence-transformers/all-MiniLM-L6-v2`  
- Embed each chunk once at ingest; embed the user query at ask time with the **same** model.

### 8.4 Vector store

- **ChromaDB** (local persist directory for the demo).  
- Collection e.g. `hdfc_mf_faqs`.  
- Store embedding + document text + metadata above.

### 8.5 Retrieval and generation

- Embed query → similarity search **top-k = 3–5**.  
- Build a prompt: retrieved chunks only + instructions (facts-only, ≤3 sentences, one URL from metadata, no advice).  
- LLM (or local small model) **must not** use knowledge outside retrieved text; if chunks lack the answer, say so.  
- **Citation:** URL of the **highest-scoring** chunk used (or the chunk that contains the stated fact). One link only.

---

## 9. UX requirements

- Tiny UI (web or notebook is acceptable).  
- Welcome line (e.g. “Ask factual questions about five HDFC schemes.”).  
- Three example questions (clickable if web).  
- Persistent disclaimer: **Facts-only. No investment advice.**  
- Answer area: text + source link + last-updated line.  
- Optional: show “retrieved from RAG” in a demo footer for the class.

**Disclaimer snippet (submit as deliverable):**

> This assistant answers factual questions from public scheme pages only. It is not investment advice, not a SEBI-registered adviser, and does not recommend buy, sell, or hold. Do not share PAN, Aadhaar, account numbers, OTPs, email, or phone numbers.

---

## 10. Non-functional requirements

| Area | Requirement |
|------|-------------|
| Latency | Demo-quality: answer in a few seconds on a laptop after index is built |
| Corpus size | 5 pages initially; index rebuildable from a script |
| Privacy | No user identity store; chat may be in-memory only |
| Reproducibility | `README` documents Python version, deps, how to ingest and run |
| Transparency | Source list CSV/MD with the 5 URLs (expand if more official pages added) |

---

## 11. Deliverables (milestone)

1. Working prototype (app) **or** ≤ 3-minute demo video if hosting is not possible.  
2. **Source list** (CSV or MD) of the 5 URLs used (more if corpus grows, still public-only).  
3. **README:** setup, AMC + schemes, known limits.  
4. **Sample Q&A** file: 5–10 queries with assistant answers + links.  
5. **Disclaimer** snippet used in the UI.

---

## 12. Known limits (document in README)

- Facts can go stale when AMC updates TER/load; freshness = last ingest date, not live AMC API.  
- Groww pages are aggregators of public scheme data; for a stricter “official” story, add AMC factsheet/KIM URLs later.  
- MiniLM is English-centric and small; Hindi queries may retrieve poorly.  
- No guarantee of SEBI-complete disclosure; prototype only.

---

## 13. Sample acceptance tests

| # | Input | Expected |
|---|--------|----------|
| 1 | Expense ratio of HDFC Large Cap Direct Growth | Short fact + Groww (or official) URL + last updated |
| 2 | ELSS lock-in | 3 years (if in corpus) + citation |
| 3 | Minimum SIP HDFC Small Cap Direct | Number from page + citation |
| 4 | Should I buy this fund? | Refusal + educational link; no buy/sell |
| 5 | Which fund gave higher returns? | No computed comparison; point to factsheet |
| 6 | My PAN is ABCDE1234F, show holdings | PII refusal; no storage |

---

## 14. Tech snapshot (demo)

| Layer | Choice |
|-------|--------|
| Load | HTTP + HTML-to-text (or saved snapshots) |
| Chunk | Recursive / heading-first, 400–600 chars, 80–100 overlap |
| Embed | `sentence-transformers/all-MiniLM-L6-v2` |
| Vector DB | ChromaDB |
| App | Small chat UI (Streamlit/Gradio/FastAPI+HTML — implementation choice) |
| LLM | Any instructor-allowed API or local model, **grounded on retrieved chunks only** |

---

## 15. Open decisions (implementation, not product)

- Exact LLM provider and API key handling (`.env`, never commit secrets).  
- Live fetch vs. checked-in HTML snapshots (prefer snapshots if scrape is flaky).  
- Whether to add official HDFC factsheet PDFs beyond Groww for stronger “official source” citations.
