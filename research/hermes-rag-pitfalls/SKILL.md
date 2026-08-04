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
