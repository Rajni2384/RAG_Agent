# Sample Q&A — real assistant output

Every answer below is **real output** from the live pipeline
(`python -m rag_agent.app.ask "…"`, LLM: `openai/gpt-oss-20b` via Groq,
index built 2026-09-27, 409 chunks). The footer line each answer would show in
the UI is included.

> **Disclaimer:** This assistant answers factual questions from public scheme
> pages only. It is not investment advice, not a SEBI-registered adviser, and
> does not recommend buy, sell, or hold. Do not share PAN, Aadhaar, account
> numbers, OTPs, email, or phone numbers.

---

## 1. Expense ratio — HDFC Large Cap Fund Direct Growth

**Q:** What is the expense ratio of HDFC Large Cap Fund Direct Growth?

**A:** The expense ratio for HDFC Large Cap Fund Direct Growth is 1.03 %.

**Source:** https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth
**Last updated from sources:** 2026-09-27

---

## 2. ELSS lock-in

**Q:** What is the lock-in for HDFC ELSS Tax Saver?

**A:** The lock‑in period for the HDFC ELSS Tax Saver Direct Growth scheme is 3 years.

**Source:** https://groww.in/mutual-funds/hdfc-elss-tax-saver-fund-direct-plan-growth
**Last updated from sources:** 2026-09-27

---

## 3. Minimum SIP — HDFC Small Cap Fund Direct Growth

**Q:** What is the minimum SIP for HDFC Small Cap Fund Direct Growth?

**A:** The minimum SIP for HDFC Small Cap Fund Direct Growth is ₹100.

**Source:** https://groww.in/mutual-funds/hdfc-small-cap-fund-direct-growth
**Last updated from sources:** 2026-09-27

---

## 4. Exit load — HDFC Flexi Cap Fund Direct Growth

**Q:** What is the exit load for HDFC Flexi Cap Fund Direct Growth?

**A:** The exit load for HDFC Flexi Cap Fund Direct Growth is 1% if redeemed within one year.

**Source:** https://groww.in/mutual-funds/hdfc-equity-fund-direct-growth
**Last updated from sources:** 2026-09-27

---

## 5. Statement / tax documents — out of corpus

**Q:** Where can I download my statement or tax documents?

**A:** I’m sorry, but the provided context does not contain information on where to download statements or tax documents.

**Source:** https://groww.in/mutual-funds/hdfc-elss-tax-saver-fund-direct-plan-growth
**Last updated from sources:** 2026-09-27

> Honest limitation: no personal-account data is in the corpus; this matched a
> scheme page but correctly reports the information is unavailable.

---

## 6. Investment advice — refused (gate, before retrieval)

**Q:** Should I buy this fund?

**A:** I'm a facts-only assistant and can't give investment advice or tell you whether to buy, sell, or hold. Please consult a SEBI-registered investment adviser.

**Learn more:** https://www.sebi.gov.in/
**(gate refused — no retrieval, no LLM call)**

---

## 7. Performance comparison — refused (gate, before retrieval)

**Q:** Which fund gave higher returns?

**A:** I don't compute or compare fund returns or performance. See the official factsheet on the scheme's page (such as Groww's scheme page) for verified historical figures.

**(gate refused — no retrieval, no LLM call)**

---

## 8. PII — refused (gate, before retrieval)

**Q:** My PAN is ABCDE1234F, show holdings

**A:** I can't process personal identifiers like PANs — please don't share PAN, Aadhaar, account numbers, OTPs, emails, or phone numbers here. I don't store or answer with them; keep them safe instead.

**(gate refused — no retrieval, no LLM call — PII not echoed or stored)**

---

## 9. Off-topic — not found

**Q:** who won the cricket match yesterday

**A:** I couldn't find that in the index. Try asking about expense ratio, exit load, lock-in period, minimum SIP, or holdings for one of the five HDFC schemes.

---

*Generated 2026-09-27 from the live `ask()` pipeline. Answers are capped at
three sentences and carry exactly one citation.*