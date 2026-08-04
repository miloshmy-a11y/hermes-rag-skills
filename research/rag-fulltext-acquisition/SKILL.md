---
name: rag-fulltext-acquisition
description: "Get full text for catalog studies or thesis citations."
version: 1.0.0
author: Hermes Agent (curator)
license: MIT
---

# RAG Full-Text Acquisition (implementation layer)

This skill is the **acquisition/extraction** complement to `general-purpose-rag` (which owns
search + indexing). It captures the *verified-working* way to actually obtain study full text
and register it in `UNIVERSAL_CATALOG.json`, including the paywalled-publisher fallback that the
SSOT `fulltext-retrieval-priority.md` lists but does not implement.

> OVERLAP NOTE: `general-purpose-rag`, `pdf-processing`, and `rag` master are **user-owned /
> protected** — the curator cannot patch them without `hermes curator adopt`. Once adopted,
> fold this skill's scripts + pitfalls into them. Until then this skill is the working reference.

## Workflow (THESIS-FIRST — user directive)
Do NOT blindly open the whole catalog. For a thesis/topic:
1. **Read the thesis full text first** (`files.extracted_text` of the FYP/local doc).
2. **Harvest its REFERENCES** — regex `10\.\d{4,9}/[^\s)...` for DOIs, plus bare URLs.
3. Cross-check DOIs vs catalog; find which are **META-only (no `extracted_text`)**.
4. **Only fetch/read the missing ones** — not all 500 docs. This is the on-topic, cheap path.
5. When filling GLOBAL evidence gaps, **prefer REVIEWS** (SR / meta-analysis / umbrella) over
   primary studies — user preference for additional/global evidence.

## Acquisition chain (canonical, from general-purpose-rag SSOT)
OpenAlex `oa_url` → Unpaywall → Europe PMC → CORE/DOAJ → **S2 paper-page HTML** → **PubMed**.
Sci-Hub EXCLUDED. Two critical real-world facts learned this session:

### PITFALL 1 — stem mismatch (silent full-text loss)
`pdf-processing/pdf_extract.py` writes the `.txt` sidecar using the **PDF filename stem**,
NOT the DOI. A batch loop that registers `extracted_text` under the **DOI** stem will find
nothing and mark the study "failed" even though text exists on disk.
**FIX:** parse the helper's stdout JSON and use its `"txt"` field:
```python
r = subprocess.run([PY, HELPER, "--pdf", src, "--outdir", OUT], capture_output=True, text=True)
meta = json.loads(r.stdout.strip().splitlines()[-1])
txt = meta.get("txt")   # absolute path the helper actually wrote
```
Never reconstruct the path from the DOI.

### PITFALL 2 — paywalled PDFs need the S2/PubMed fallback
Direct PDF GET via OpenAlex/Unpaywall/EuropePMC returns **login-wall HTML, not a PDF**, for
Wiley / Elsevier / SAGE / Wolters Kluwer / APA PsycNet / Karger. `is_pdf()` check
(`b[:4]==b"%PDF" and len>5000`) catches it. The working fallback (verified: filled 50/53):
- **Semantic Scholar paper page** (`https://www.semanticscholar.org/paper/<paperId>`) — bot-accessible
  even for paywalled papers; fetch `paperId` via `api.semanticscholar.org/graph/v1/paper/DOI:<doi>`.
- **PubMed efetch** abstract (`eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id=<pmid>&rettype=abstract`)
  — covers biomedical DOIs via `esearch` by DOI first.
Save the result as `<stem>.txt`, set `full_text_status: pending_s2_page` / `pending_pubmed`,
and **LLM-verify** it's real content before trusting as full text.

### PITFALL 3 — never claim "complete" from disk writes
Extraction succeeding on disk ≠ registered in catalog. After any batch, **re-query the catalog**
and count docs with `(files.extracted_text and os.path.exists(...))`. Report the REAL number
(e.g. "77/79 thesis citations now have full text; 2 classic theory papers remain META"). A
partial result stated as complete is a correctness failure, not a minor wording issue.

## Environment facts (stable for this user's setup)
- PDF extraction MUST run in **terminal Python** (`C:\Python314`), NOT `execute_code`'s venv
  (no PyMuPDF/pypdf there). Use `software-development/pdf-processing/pdf_extract.py`.
- `web_extract` / `web_search` tools work from `execute_code` and `terminal`.
- Memory store is **hard-capped at 2,200 chars with no in-app setting to raise it** (verified
  by searching config). Compact entries or move durable procedures to skills when full.

## Scripts (verified this session, generalized)
- `scripts/acquire_citations_batch.py` — for a DOI list / thesis, try OpenAlex→Unpaywall→EuropePMC
  PDF, extract via helper, register `extracted_text`.
- `scripts/acquire_citations_fallback.py` — for DOIs still META, fetch S2 page + PubMed abstract,
  register as `pending_<src>` for later LLM verification.

Run both via `terminal` (needs network + PyMuPDF). Both read/write `UNIVERSAL_CATALOG.json`
in place; back it up first.
