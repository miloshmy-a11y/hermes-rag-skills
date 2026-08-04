---
name: hermes-rag-pitfalls
description: "RAG terminal pitfalls: paths, interpreters, scripts."
version: 1.0.0
author: Hermes Agent
license: MIT
tags: [rag, pitfalls, paths, windows, hermes, pdf, catalog]
---

# Hermes RAG Pitfalls — the consolidated fix-guide

Load this skill before ANY RAG terminal work. It captures the failure patterns that
keep recurring across sessions and gives copy-paste commands that actually work.

## 0. The two interpreters (root of most failures)
| Interpreter | Path | PDF libs? | web_extract? |
|---|---|---|---|
| **terminal `python3`** | `C:\Python314\python.exe` (3.14) | ✅ PyMuPDF, pdftotext | ❌ no hermes_tools |
| **execute_code venv** | `...\hermes-agent\venv\Scripts\python.exe` (3.11) | ❌ none | ✅ `from hermes_tools import web_extract` |

**Rule:** All PDF work → `terminal()`. All `web_extract` → `execute_code`. Never mix.

## 1. MSYS path mangling (most common breakage)
In `terminal()` (bash/MSYS) a leading `/c/...` is fine, BUT:
- `python3 "C:/Users/..."/script.py` → bash rewrites `C:/` into `C:\c\...` → `No such file`.
- **Fix:** use forward slashes and a variable, OR use `C:/Users/...` WITHOUT a leading slash
  ambiguity. Safest: assign to a var and quote it:
  ```bash
  SCRIPT="<HERMES_SKILLS>/software-development/pdf-processing/pdf_extract.py"
  python3 "$SCRIPT" --pdf "C:/path/to.pdf" --outdir "C:/path/out"
  ```
- Inside `python3 -c "..."` inline, **NEVER** use backslashes (`\U` = unicode error).
  Use forward slashes or write a `.py` file and run it.

## 2. Skill vs script entry points (don't guess)
| Want to… | Correct call | Common wrong call |
|---|---|---|
| Search catalog | `from precise_search import staged_search` (script in `.../general-purpose-rag/scripts/`) | running `universal_rag.py` from wrong CWD |
| CLI search/ingest | `python3 universal_rag.py --search "..."` (script in `.../general-purpose-rag/` ROOT, NOT scripts/) | `from universal_rag import ...` without `sys.path.insert` to the ROOT |
| Extract PDF text | `pdf-processing` skill → `pdf_extract.py` | hand-rolled `import fitz` in execute_code (FAILS) |
| Download PDF by DOI | `paper-fetch` skill → `scripts/fetch.py` | web_extract on doi.org landing (0 chars) |

**`precise_search.py` import gotcha:** it only imports from its OWN `scripts/` dir.
Running it from the catalog dir fails. Always:
```python
sys.path.insert(0, r"<HERMES_SKILLS>/research/general-purpose-rag/scripts")
from precise_search import staged_search
```

## 3. `staged_search` result schema (don't print non-existent keys)
Each item in `out["core_results"]` has: `doc, score, matched_terms, found_via,
judgment, evidence, nurse_in_title, is_student, ...`
- ❌ There is **NO** `match_type` and **NO** `source` key.
- ✅ Use `r.get("found_via")` (`index`/`fulltext`/...) and `r.get("judgment")` (`ON_TOPIC`/...).
- Web-fallback candidates: `out["web_candidates"]`, each with `needs_indexing=True`.

`out` dict keys: `core_results, student_results, reference_results, web_candidates,
breadth, needs_narrowing, open_fulltext, total_core_available, suggested_actions,
terms_used, stage_reached, judgment, ...`

## 4. Dedicated skills to use (not hand-rolled)
- **`pdf-processing`** (`software-development/pdf-processing`): `pdf_extract.py` → produces
  `<stem>.txt` + `<stem>_meta.json`. Metadata heuristic is DRAFT — Crossref-override
  title/authors. Tested: Nikitara 2024 → 76k chars, 20 pages, 0 empty. ✅
- **`paper-fetch`** (`research/paper-fetch`): `scripts/fetch.py <DOI>` → downloads OA PDF.
  Sources: unpaywall→S2→PMC→europe_pmc. Tested: Woodnutt + Nikitara both fetched. ✅
- **`research-fulltext-retrieval`**: when paywalled, extract S2 paper-page HTML via
  `web_extract` (execute_code only).

## 5. Verified end-to-end ingest recipe (copy-paste)
```bash
# 1) Download PDF (terminal)
python3 "<HERMES_SKILLS>/research/paper-fetch/scripts/fetch.py" \
  "10.1111/inm.70039" --out "<HERMES_CACHE>/universal_rag/pdfs" --format json

# 2) Extract text (terminal) -> uses pdf-processing skill
python3 "<HERMES_SKILLS>/software-development/pdf-processing/pdf_extract.py" \
  --pdf "<HERMES_CACHE>/universal_rag/pdfs/Woodnutt_2025_....pdf" \
  --outdir "<HERMES_CACHE>/universal_rag/source_text"

# 3) Verify DOI via Crossref (terminal) -> authoritative metadata
python3 -c "import urllib.request,json; print(json.load(urllib.request.urlopen('https://api.crossref.org/works/10.1111/inm.70039'))['message']['title'])"
```
Then build the catalog entry (Crossref title/authors/year override the _meta.json draft),
append to `UNIVERSAL_CATALOG.json["documents"]`, save. Back up first.

## 6. Quick catalog sanity check
```python
import json
d = json.load(open(r"<HERMES_CACHE>/universal_rag/UNIVERSAL_CATALOG.json", encoding="utf-8"))["documents"]
print(len(d), "docs")
print([x for x in d if not x.get("doi")], "missing-doi")
```

## 7. Catalog data-integrity pitfalls (recurring — found & fixed 2026-08-04)
These are the **data** failures (not logic), each verified and resolved. Re-check before
trusting a search result's full text.

### 7.1 Two records share a DOI = NOT always a duplicate
- **Symptom:** dedup-by-DOI deletes a record, but the two papers have *different* titles/authors.
- **Cause:** one record carries a **wrong DOI** (copy-paste/extraction error); the other is the real paper.
- **Resolution (verified):** never delete on DOI alone. Compare **title + first author**; if they
  differ, FLAG for review (wrong-DOI-on-different-study), do NOT delete. Only merge when
  title+authors+year match (e.g. preprint `10.21203/rs.3.rs-...` vs published `10.1136/bmjopen-...`).
- **Verify:** `from collections import Counter; c=Counter(d.get('doi') for d in docs if d.get('doi')); assert not any(v>1 for v in c.values())` — but ALSO scan same-normalized-title across *different* DOIs.

### 7.2 `full_text_md` / `extracted_text` pointing at a Semantic Scholar / search page
- **Symptom:** file exists but content is `"[Skip to search form] ..."` or a Related-Papers list —
  NOT the paper. Often stored as a bare `SOURCE_TEXT/.md` (empty basename) and linked by 3+ records.
- **Cause:** S2 paper-page HTML was saved as the "full text" without extracting the article body.
- **Resolution (verified):** delete the orphan `.md`; set affected records `full_text_status: pending`,
  remove the bad `full_text_md` key. They have NO valid full text — do not fabricate.
- **Verify:** grep file head for `semanticscholar.org/paper/` + `Skip to` + `Related Papers`.

### 7.3 `meta_only` record with dangling `full_text_pdf`/`extracted_text` keys
- **Symptom:** `full_text_status: meta_only` BUT `files` block lists `full_text_pdf`/`extracted_text`
  paths to PDFs that were never downloaded (status says meta_only, pointers imply a file).
- **Resolution (verified):** strip the dangling keys so `files` reflects reality; keep `meta_only`.
- **Verify:** for every `meta_only` record, assert none of
  `full_text_pdf/extracted_text/full_text_html/full_text_md` exist in `files`.

### 7.4 Audit-script format drift (the silent stale-warning trap)
- **Symptom:** `audit_fulltext_mismatch.py` crashes with `TypeError: list indices must be integers`
  and an old "7 status=present no file" warning keeps replaying.
- **Cause:** the audit expects `data["documents"]` (dict) but the live catalog is a **bare JSON
  list**. The warning is FROZEN OLD DATA, not a fresh run.
- **Resolution (verified):** run the audit logic against `json.load(...)` (a list) directly;
  current catalog shows 0 status/disk inconsistencies, 0 wrong-body files. Don't trust the
  cached stale warning — re-run the check against the live list.
- **Verify:** `docs = json.load(open(CAT))` (no `["documents"]`); re-run the same checks fresh.

### 7.5 Index↔full-text link must be 100% (the RAG contract)
- The index is a HELPER to narrow candidates; the LLM opens the resolved full text for the final
  relevance call. If a `files.extracted_text` path doesn't resolve, the loop silently loses a study.
- **Verify (run before any search-driven claim):** resolve every `extracted_text`/`full_text_md`/
  `full_text_html` pointer across all records; `broken` must be 0. (Verified 480/480 resolve, 0 broken.)
- **Enhancement rule:** when the LLM judges a full text RELEVANT, backfill `key_findings` (1–3
  sentence conclusion) FROM that text, so later index searches surface it. Never invent rankings.

### 7.6 Title-field corruption (abstract text / doubled chars leaked in)
- **Symptom:** `authors` or `title` contains `"Background: ..."` or `"TThhee W Woorlrdld..."`.
- **Cause:** PDF text-extraction artifact bled into metadata; or `['Ethics']` from a cover-letter doc.
- **Resolution (verified):** clear/repair from the authoritative source (Crossref for authors;
  extracted_text for title). WHO-5 title repaired from its own extracted body.
- **Verify:** flag any `authors` entry containing `background:`/`methods`/`ethics` as leaked text.
