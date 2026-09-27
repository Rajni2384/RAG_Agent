# Implementation guide (phase-wise)

**Product:** HDFC Mutual Fund FAQ RAG Chatbot  
**Follow:** [architecture.md](./architecture.md) then [PRD.md](./PRD.md)  
**How to use:** One phase per Cursor chat (or per agent turn). Paste the **Cursor prompt** block. Do not start the next phase until the **Done when** checklist passes.

**Hard rules for every phase**

- Keep RAG stages in **separate modules** (no single `run_chatbot.py` that loads, chunks, embeds, and answers).
- Do not invent extra features (auth, returns calculators, multi-AMC, rerankers).
- Never commit `.env`, API keys, or `data/chroma/`.
- Citations must come from **chunk metadata**, not from the LLM inventing a URL.

---

## Phase map

| Phase | Name | Pipeline | Outcome |
|-------|------|----------|---------|
| 0 | Repo skeleton | — | Python project, ignore rules, deps listed |
| 1 | Corpus + load + clean | Ingest | 5 documents with text + metadata |
| 2 | Chunking | Ingest | Section-aware chunks, prefixed, sized |
| 3 | Embed + Chroma + ingest CLI | Ingest | Rebuildable `hdfc_mf_faqs` index |
| 4 | Retrieval | Query | `top-k` search returns typed hits |
| 5 | Safety | Query | PII / advice / performance stop **before** RAG |
| 6 | Generate + cite + orchestrate | Query | Facts-only answer object |
| 7 | Chat UI | Query | Tiny demo UI |
| 8 | Milestone wrap | — | README, sources, sample Q&A, disclaimer |

---

## Phase 0 — Repo skeleton

**Goal:** Empty but runnable project layout matching architecture §5.

**Create**

```
rag_agent/          # package (or src/rag_agent — pick one and stick to it)
  ingest/
  retrieve/
  generate/
  safety/
  app/
data/
  sources.csv
  snapshots/
requirements.txt
.env.example
.gitignore
```

**Cursor prompt — copy from here**

```
Read architecture.md. Implement Phase 0 only: repo skeleton.

- Python 3.11+ package with folders: rag_agent/ingest, retrieve, generate, safety, app and data/snapshots.
- Add empty __init__.py files so the package imports.
- requirements.txt with placeholders we will use: sentence-transformers, chromadb, beautifulsoup4, lxml, python-dotenv, and streamlit (UI in a later phase). Pin reasonably recent versions.
- .gitignore: .env, data/chroma/, __pycache__/, .venv/, *.pyc
- .env.example with LLM_API_KEY= and LLM_MODEL= (no real secrets).
- data/sources.csv with header scheme_type,scheme_name,url and these 5 rows (Groww HDFC pages from architecture/PRD):
  large_cap, HDFC Large Cap Fund Direct Growth, https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth
  flexi_cap, HDFC Flexi Cap Fund Direct Growth, https://groww.in/mutual-funds/hdfc-equity-fund-direct-growth
  elss, HDFC ELSS Tax Saver Direct Growth, https://groww.in/mutual-funds/hdfc-elss-tax-saver-fund-direct-plan-growth
  small_cap, HDFC Small Cap Fund Direct Growth, https://groww.in/mutual-funds/hdfc-small-cap-fund-direct-growth
  hybrid, HDFC Balanced Advantage Fund Direct Growth, https://groww.in/mutual-funds/hdfc-balanced-advantage-fund-direct-growth
- Do not implement load/chunk/embed/UI yet.
Stop when the tree and files exist.
```

**Done when**

- [ ] Folders match architecture §5
- [ ] `sources.csv` has exactly the five URLs
- [ ] `.gitignore` excludes chroma and `.env`

---

## Phase 1 — Load and clean

**Goal:** Each source becomes a `Document` with `text`, `url`, `scheme_name`, `scheme_type`, `fetched_at`. Prefer snapshots if HTTP fails.

**Implement (architecture §5.1–5.2)**

- `rag_agent/ingest/load.py` — read CSV; for each row, load `data/snapshots/{scheme_type}.html` if present, else GET the URL (User-Agent, timeout).
- `rag_agent/ingest/clean.py` — HTML → visible text; drop obvious nav/footer noise; keep headings; normalize newlines.
- Optional helper: `save_snapshots.py` that writes HTML once so the demo is reproducible.

**Cursor prompt**

```
Read architecture.md §5.1, §5.2, §6.2, §8. Implement Phase 1 only (load + clean). Do not chunk, embed, or use Chroma.

- Document dataclass: url, scheme_name, scheme_type, fetched_at (ISO date), text, optional raw_html.
- load.py: sources from data/sources.csv. Prefer data/snapshots/{scheme_type}.html; else HTTP GET. Set fetched_at to today (UTC date) or file mtime date for snapshots.
- clean.py: BeautifulSoup; extract main-ish text; preserve heading lines; collapse whitespace; keep expense ratio, exit load, SIP, riskometer, benchmark, lock-in if present in the page.
- If live fetch is blocked, save whatever HTML you can into snapshots and load from disk. If a page cannot be fetched, fail that row with a clear error, do not silently skip all five.
- Add a small script or `if __name__` in load to print scheme_name and len(text) for all five docs.
Do not add embeddings or UI.
```

**Done when**

- [ ] Running load prints five schemes with non-trivial `text` length (not empty / not only “Groww” chrome)
- [ ] Each document has `url` matching `sources.csv`
- [ ] Snapshots exist **or** live fetch works (prefer both: snapshot after first successful fetch)

**Verify:** `python -m rag_agent.ingest.load` (or the script you added) — five documents.

---

## Phase 2 — Chunking

**Goal:** Heading-first then recursive split. No one-chunk-per-page.

**Implement (architecture §5.3)**

- `rag_agent/ingest/chunk.py`
- Size **400–600** characters, overlap **80–100**
- Separators: `\n\n`, `\n`, `. `, space
- Prepend `Scheme: {name} | Type: {type}` to stored chunk **text**
- Metadata: `chunk_id`, `source_url`, `scheme_name`, `scheme_type`, `fetched_at`

**Cursor prompt**

```
Read architecture.md §5.3 and §6.3. Implement Phase 2 only: chunk.py. Use Document from Phase 1.

- Heading-first split when lines look like fact headings (Exit load, Expense ratio, Riskometer, Benchmark, SIP, lock-in, and similar).
- Then recursive character split: 400–600 chars, overlap 80–100, separators \n\n, \n, ". ", space.
- Do NOT emit one chunk for the entire page. Reject/split any chunk that is still huge.
- Prefix each chunk text with "Scheme: {scheme_name} | Type: {scheme_type}".
- chunk_id like {scheme_type}_{n:03d}.
- Add a tiny debug path: load all docs, chunk, print count per scheme and min/max chunk length.
Do not embed or write Chroma.
```

**Done when**

- [ ] Each scheme produces **multiple** chunks
- [ ] Typical chunk length in the 400–600 band (last chunk may be shorter)
- [ ] Prefix present on every chunk
- [ ] `source_url` on every chunk matches the parent document

---

## Phase 3 — Embed, Chroma, ingest CLI

**Goal:** Offline index rebuild. Collection `hdfc_mf_faqs`. Same MiniLM for later queries.

**Implement (architecture §5.4–5.5, §8)**

- `rag_agent/ingest/embed.py` — `sentence-transformers/all-MiniLM-L6-v2`, batch encode
- `rag_agent/ingest/store.py` — persist `data/chroma`, collection name `hdfc_mf_faqs`; rebuild = wipe collection then upsert
- `rag_agent/ingest/run_ingest.py` — load → clean → chunk → embed → upsert → write `data/ingest_manifest.json` (`run_at`, urls, chunk_count)

**Cursor prompt**

```
Read architecture.md §5.4, §5.5, §8. Implement Phase 3 only.

- embed.py: sentence-transformers/all-MiniLM-L6-v2; function encode_texts(list[str]) -> embeddings. Reuse this module later for queries (do not duplicate the model name elsewhere).
- store.py: Chroma persistent client at data/chroma. Collection hdfc_mf_faqs. Upsert ids=chunk_id, documents=prefixed text, metadatas as architecture §6.3, embeddings from embed.py. Rebuild must replace old vectors (delete collection or equivalent) so reruns are clean.
- run_ingest.py: full ingest pipeline; write data/ingest_manifest.json with run time, URL list, chunk count.
- .gitignore already has data/chroma — do not commit the index.
- After implementation, I should run: python -m rag_agent.ingest.run_ingest
Do not implement chat, LLM, or safety yet.
```

**Done when**

- [ ] `run_ingest` completes without error
- [ ] `data/chroma` exists locally
- [ ] Manifest `chunk_count` > 5 (many chunks, not five pages-as-vectors)
- [ ] Re-running ingest does not duplicate IDs / explode count

**Verify:** Second ingest; collection count equals manifest chunk count.

---

## Phase 4 — Retrieval

**Goal:** Query embedding + top-k. No LLM.

**Implement (architecture §5.6)**

- `rag_agent/retrieve/search.py`
- `n_results` default **4** (allowed 3–5)
- Return `{ text, source_url, scheme_name, fetched_at, distance }`
- Optional: if the question names a scheme, metadata `where` filter (nice-to-have, not required)

**Cursor prompt**

```
Read architecture.md §5.6. Implement Phase 4 only: retrieve/search.py.

- Open the same Chroma persist path and collection hdfc_mf_faqs.
- Embed the query with the SAME encode function / MiniLM as ingest (import from ingest.embed — do not load a second model name).
- query n_results=4.
- Return a list of typed hits: text, source_url, scheme_name, fetched_at, distance.
- CLI or __main__: python -m rag_agent.retrieve.search "What is the expense ratio of HDFC Large Cap Fund Direct Growth?" and print scheme_name + source_url + first 200 chars.
Do not call an LLM.
```

**Done when**

- [ ] Expense-ratio query returns HDFC Large Cap (or clearly that scheme’s URL) in top hits
- [ ] ELSS lock-in query surfaces ELSS chunks
- [ ] Hits include `source_url` and `fetched_at`

---

## Phase 5 — Safety (before RAG)

**Goal:** Deterministic gates. Unsafe questions never embed or retrieve.

**Implement (architecture §5.8, §6.4, §7)**

- `rag_agent/safety/pii.py` — PAN, Aadhaar, Indian phone, email, OTP-like digit runs
- `rag_agent/safety/intent.py` — `advice` | `performance` | `factual`
- `rag_agent/safety/refusals.py` — canned ≤3 sentences + `education_url` (AMFI/SEBI investor education) or factsheet/scheme URL for performance
- A single `classify_or_refuse(text) -> QueryResponse | None` (None means continue to RAG)

**Cursor prompt**

```
Read architecture.md §5.8, §6.4, §7. Implement Phase 5 only: safety package. No Chroma, no LLM.

- Shared response dataclass matching §6.4: kind, text, source_url, last_updated, education_url.
- pii.py: detect PAN-like, Aadhaar-like, phone, email, OTP-like. On hit: kind=refusal_pii, do not echo the PII back, tell the user not to share identifiers.
- intent.py: advice (buy/sell/should I/best fund/recommend/allocate) vs performance (returns, CAGR, outperformed, which did better) vs factual.
- refusals.py: polite facts-only messages; advice uses one AMFI or SEBI investor-education URL; performance does not compute returns and points to the relevant Groww scheme URL or a generic "see official factsheet on the scheme page" if scheme unknown.
- Unit-style tests or a small __main__ with the PRD examples: "Should I buy this fund?", "Which fund gave higher returns?", "My PAN is ABCDE1234F, show holdings", and a normal expense-ratio question (must pass through as factual).
Do not wire UI yet.
```

**Done when**

- [ ] Advice → `refusal_advice` + education link, no retrieval
- [ ] Returns comparison → `refusal_performance`, no numbers invented
- [ ] PII → `refusal_pii`, PII not stored/logged
- [ ] Normal FAQ question is `factual` / not a refusal

---

## Phase 6 — Generate, cite, orchestrate

**Goal:** Full query path: guardrails → retrieve → prompt → LLM → citation from metadata.

**Implement (architecture §5.7, §9, §7)**

- `rag_agent/generate/prompt.py` — fixed system rules (facts-only, context only, ≤3 sentences)
- `rag_agent/generate/llm.py` — read `.env`; one provider function `complete(prompt) -> str`. Keep provider swappable.
- `rag_agent/generate/cite.py` — **one** `source_url` from top hit (or supporting chunk); `last_updated` = max `fetched_at` of used chunks
- `rag_agent/generate/postprocess.py` (or inside cite) — force ≤3 sentences; never trust model-invented URLs
- `rag_agent/app/ask.py` (or `pipeline.py`) — sequence in architecture §7: safety first; if RAG, retrieve; if empty/low similarity → `not_found`; else LLM; attach citation

**Low relevance:** if Chroma returns nothing, or distances are worse than a documented threshold, return `not_found` without calling the LLM (or after a cheap check). Pick a simple threshold and put it in one constant.

**Cursor prompt**

```
Read architecture.md §5.7, §6.4, §7, §9. Implement Phase 6: generate + a single ask() orchestrator. UI is still not required (CLI is enough).

- prompt.py: system instructions exactly as architecture §9. User block includes QUESTION and numbered CONTEXT with source_url and scheme_name per chunk.
- llm.py: load dotenv; call the configured LLM. If no API key, raise a clear error. Do not put keys in code.
- cite.py: citation URL MUST come from retrieval metadata (top hit), never from model output. last_updated from chunk fetched_at.
- Post-process: cap answer at 3 sentences.
- ask(question) -> QueryResponse:
  1) safety: if refusal, return immediately (do not embed, retrieve, or call LLM)
  2) retrieve top-4
  3) if no useful hits: kind=not_found, invite a scheme-fact question
  4) else LLM with chunks only; kind=answer; source_url + last_updated set in code
- CLI: python -m rag_agent.app.ask "What is the lock-in for HDFC ELSS Tax Saver?"
Also handle: advice and PII via the same ask() without hitting Chroma (assert or log a skip).
Do not build Streamlit yet.
```

**Done when**

- [ ] Factual question: `kind=answer`, one real Groww URL, `Last updated` date, ≤3 sentences
- [ ] Advice/PII: no Chroma/LLM call
- [ ] Garbage / unknown: `not_found`, no invented TER
- [ ] Model cannot change the citation URL

**Verify:** Three CLI questions — fact, advice, PII.

---

## Phase 7 — Tiny chat UI

**Goal:** PRD F5. Streamlit (already in requirements) unless you already chose Gradio.

**Implement (architecture §5.9)**

- `rag_agent/app/ui.py` (or `streamlit_app.py` at repo root)
- Welcome line
- Three example questions (click fills the input)
- Persistent: **Facts-only. No investment advice.**
- Full disclaimer from PRD §9
- Show `text`, source link, `Last updated from sources: YYYY-MM-DD`
- Session chat only (in-memory)
- Optional footer: grounded in retrieved chunks (RAG)

**Cursor prompt**

```
Read architecture.md §5.9 and PRD.md §7.2, §9. Implement Phase 7 only: Streamlit UI that calls ask() from Phase 6.

- Welcome: Ask factual questions about five HDFC schemes.
- Three clickable examples:
  1. What is the expense ratio of HDFC Large Cap Fund Direct Growth?
  2. What is the lock-in for HDFC ELSS Tax Saver?
  3. What is the minimum SIP for HDFC Small Cap Fund Direct Growth?
- Persistent short line: Facts-only. No investment advice.
- Show the full disclaimer snippet from PRD.md.
- On submit: ask(question); render answer text, one citation hyperlink, last updated line. For refusals show education_url if present.
- Do not persist chat to disk. Do not add login.
- README snippet in comments or I'll add README in Phase 8: streamlit run ...
Keep UI tiny. No extra pages.
```

**Done when**

- [ ] `streamlit run` shows welcome, 3 examples, disclaimer
- [ ] Example click works
- [ ] Answer shows one link + last updated
- [ ] Advice example in the box still refuses

**Verify in browser** if tools exist: send one fact question and one “Should I buy?”.

---

## Phase 8 — Milestone deliverables

**Goal:** What the class asks to submit (PRD §11–12).

**Create / update**

- `README.md` — setup (venv, `pip install`, `.env`, `run_ingest`, Streamlit), AMC + 5 schemes, known limits (stale data, Groww aggregator, MiniLM/English, prototype)
- `data/sources.csv` already exists; also `SOURCES.md` if you want a human-readable list (same 5 URLs)
- `sample_qa.md` — 5–10 queries with **actual** assistant outputs + links (run `ask()` and paste)
- Disclaimer in README = same snippet as UI
- Confirm `.env` not committed

**Cursor prompt**

```
Read PRD.md §11–12 and architecture.md. Phase 8: documentation only, no architecture changes.

- README.md: Python version, venv, pip install -r requirements.txt, copy .env.example to .env, run ingest, run Streamlit, list HDFC + 5 schemes with URLs, known limits (ingest date not live API; Groww pages; no Hindi guarantee; no advice).
- SOURCES.md: the 5 URLs in a table.
- sample_qa.md: run the ask() pipeline (or use existing CLI) for 8 questions covering: expense ratio, ELSS lock-in, min SIP, exit load or riskometer/benchmark, statement/tax-doc if in corpus, should I buy, which returned more, and a PII example. Paste real answers + links. If LLM is unavailable, generate sample_qa from retrieval-only extractive stubs and note that in the file — but prefer real ask() output.
- Do not weaken safety or add new product features.
```

**Done when**

- [ ] README is enough for a classmate to run ingest + UI
- [ ] Source list matches the five URLs
- [ ] Sample Q&A has 5–10 items with links
- [ ] Disclaimer matches the UI

---

## Suggested Cursor workflow

1. New chat per phase (keeps context small).
2. First line: `Implement only Phase N from implementation.md. Read architecture.md.`
3. After the agent finishes, run **Verify** yourself before Phase N+1.
4. If a phase fails, stay on that phase; do not “just add the UI”.

### If Groww fetch fails in Phase 1

Stay in Phase 1: save HTML snapshots (browser Save As, or curl) into `data/snapshots/{scheme_type}.html`, then load from disk. Do not skip to embeddings on empty text.

### If no LLM key in Phase 6

Implement `llm.py` behind an interface. Temporary **extractive** fallback (first sentences of top chunk) is allowed **only** as a flagged demo mode, still with `cite.py` metadata. Prefer a real LLM for the class demo.

---

## File checklist (end state)

| Path | Phase |
|------|-------|
| `data/sources.csv` | 0 |
| `rag_agent/ingest/load.py`, `clean.py` | 1 |
| `rag_agent/ingest/chunk.py` | 2 |
| `rag_agent/ingest/embed.py`, `store.py`, `run_ingest.py` | 3 |
| `rag_agent/retrieve/search.py` | 4 |
| `rag_agent/safety/*` | 5 |
| `rag_agent/generate/*`, `ask()` | 6 |
| `rag_agent/app/ui.py` | 7 |
| `README.md`, `SOURCES.md`, `sample_qa.md` | 8 |

---

## Do not implement (any phase)

- Buy/sell recommendations or return math
- User accounts, PAN storage, chat logs on disk
- Extra AMCs, rerankers, cron ingest (unless a later homework)
- Secrets in git
