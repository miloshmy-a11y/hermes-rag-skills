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

## 8. BULK INGEST PIPELINE (the reusable, copy-paste flow — STOP hand-rolling it)
This is the full "recover missing full texts → match → extract → index → verify → push" loop.
It is ONE pattern; do not rewrite it per session. Build a single script that does all of it.

### 8.1 Find missing full texts (post-2020 nursing example)
```python
import json, os
docs=json.load(open(CAT,encoding="utf-8"))   # BARE LIST, not data["documents"]
def is_nurs(x): return "nurs" in " ".join(str(x.get(k,"")) for k in
    ["title","abstract","keywords_llm","brief_abstract","measures"] if x.get(k)).lower()
def has_ft(x): p=(x.get("files") or {}).get("extracted_text"); return bool(p and os.path.exists(p))
missing=[x for x in docs if is_nurs(x) and (lambda y:isinstance(y,int) and y>=2020)(x.get("year")) and not has_ft(x)]
open("_retry_dois.txt","w").write("\n".join(x.get("doi") for x in missing if x.get("doi")))
```

### 8.2 Match PDF → catalog record by DOI parsed FROM INSIDE the PDF (authoritative)
- NEVER match by (author,year) filename heuristics — they break on name-format variants.
- Extract first 1–3 pages of the PDF text; regex `10\.\d{4,9}/[^\s\)\"<>]+`; normalize
  (`lower()`, strip `https://doi.org/`, strip trailing `.,;`). Match against `by_doi`.
- Fallback: title-similarity ONLY if DOI absent/garbled; then verify body contains catalog title.
- S2 sometimes returns a journal-level DOI (e.g. `10.47772/IJRISS`) — that is NOT the article
  DOI; use the article-specific suffix (`10.47772/ijriss.2024.8120314`) from Crossref.

### 8.3 Extract + index in ONE pass (no deferred backfill)
For each matched PDF: write `<EXTRACTED>/<safe-doi>.txt`; set `files.extracted_text`,
`full_text_status="present"`, detect instruments, set `measures`/`keywords_llm`/INSTRUMENT
brief_abstract line, `country_note`; `d["files"].pop("full_text_md",None)`. Detect instruments
from the BODY only (canonical list: ENSS/NSS/BM-NSS/MBI/DASS/ProQOL/PSS/JSS/SAQ/JCQ/GHQ/K10/
OLBI/NWI). Do NOT guess `measures` when no instrument is present.

### 8.4 Add a NEW record (when a provided PDF is a real study absent from catalog)
Crossref-verify FIRST (`https://api.crossref.org/works/<DOI>` → title/authors/year/journal).
Then append `{doi,title,authors,year,journal,apa_citation,measures,country,keywords_llm,
brief_abstract,full_text_status:"present",files:{extracted_text:...},source:"user-provided"}`.
Always check duplicate DOI AND duplicate title before append.

## 9. GITHUB PUSH PATTERN (verified; the `force-with-lease` quirk is real)
Full clone (NOT --depth 1) → assert `behind==0` → copy local → PII scan → commit → PLAIN `--force`.
```python
# run via subprocess; abort if behind!=0 (remote may have commits you lack)
behind = run(["git","-C",WORK,"rev-list","--count","HEAD..origin/master"]).stdout.strip()
assert behind == "0", "remote has commits I lack; aborting force"
# PII scan: reject if r"ghp_...|github_pat_..." appears in any .json/.py/.md
run(["git","-C",WORK,"push","--force","origin","HEAD:master"])
```
- `--force-with-lease` returns "stale info" EVEN when behind==0 in this Windows+GCM setup.
  Plain `--force` is safe ONLY after the `behind==0` guard. Don't loop on force-with-lease.
- SYNTAX TRAP (hit 2026-08-04): `run(["git","-C",WORK,"config","user.email","x@y.z")`  ←
  MISSING closing `)`. A bare `run(` that isn't closed crashes the whole push with SyntaxError.
  Always close `run(...)`.

## 10. SEMANTIC SCHOLAR (S2) fetch lessons (verified 2026-08-04)
- S2 API WORKS from this env (200 OK). Failures were SELF-INFLICTED, not rate-limit:
  1. **Double-encoded DOI**: `urllib.parse.quote()` on an already-clean DOI → `10.x%2Fyyy` → 400.
     FIX: use raw DOI, only strip `https://doi.org/` prefix.
  2. **Deprecated `pdfUrls` field** → 400. FIX: request `fields=title,openAccessPdf,publicationDate`.
  3. **Rate limit**: respect 1 request/sec (`time.sleep(1.0)`) — honor this regardless.
- S2 `openAccessPdf.url` returns real OA links, but this sandbox EGRESS 403s most PDF hosts
  (MDPI/ScienceDirect/scholarhub/myjms). PMC-hosted links work via `europepmc.org/articles/PMC…?pdf=render`.
- Primary route that WORKS here: `paper-fetch` skill → europe_pmc. Use S2 only to discover
  hidden PMC IDs.

## 11. AD-HOC VERIFY (and the broken-pointer counting bug)
- Verify against the LIVE `json.load(open(CAT))` (bare list) — never a frozen audit warning.
- **BROKEN-POINTER COUNT BUG (hit 2026-08-04):** `broken=[d for d in docs if
  d.get("full_text_status")=="present" and not A or not B]` — the `not A or not B` binds
  wrong (precedence), producing false "96 broken". CORRECT:
  `broken=[d for d in docs if d.get("full_text_status")=="present" and not (has_ft(d))]`
  where `has_ft` checks the pointer resolves AND file exists. Direct check is authoritative:
  all 337 present-status records resolved, 0 broken.
- Always run the verify script (don't claim results you didn't execute). Temp pattern:
  `fd,path=tempfile.mkstemp(prefix="hermes-verify-",suffix=".py",dir=r"C:/Users/Milos/AppData/Local/Temp")`;
  write script; `os.system(f'python3 "{path}"')`; delete after.
