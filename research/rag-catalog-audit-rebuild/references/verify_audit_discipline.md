# Verify-Audit Discipline (copy-paste procedure)

Companion to the **Verification discipline (V1–V4)** section in SKILL.md. Run this BEFORE any
expansion/addition pass. Scope = `doc_type: study` only (skip ebook/website/policy/instrument/
org_doc/gov_doc/tool/assignment).

## The audit loop (execute_code, Python)
```python
import os, json
BASE = r"C:\Users\Milos\AppData\Local\hermes\cache\web\universal_rag"
cat = json.load(open(os.path.join(BASE, "UNIVERSAL_CATALOG.json"), encoding='utf-8'))
docs = cat['documents']

def has_id(d):   return bool(d.get('doi') or d.get('url'))
def has_ft(d):
    f = d.get('files', {}) or {}
    p = f.get('full_text_pdf') or f.get('full_text_html') or f.get('extracted_text') or f.get('full_text_md')
    return bool(p and os.path.exists(p))
def has_meta(d):
    return bool((d.get('title') or '').strip()) and bool(d.get('year')) and (
        bool(d.get('abstract') and len(d.get('abstract','')) > 50) or
        bool(d.get('authors')) or bool(d.get('keywords')) or bool(d.get('tags')))

studies = [d for d in docs if d.get('doc_type') == 'study']
# 1) broken paths
broken = [d for d in studies if (lambda f:(f.get('full_text_pdf') or f.get('full_text_html') or
    f.get('extracted_text') or f.get('full_text_md')) and not os.path.exists(
    f.get('full_text_pdf') or f.get('full_text_html') or f.get('extracted_text') or f.get('full_text_md') or 'x'))(d.get('files', {}) or {})]
# 2) locate missing files on source disk by basename, relink (absolute path)
#    e.g. walk <YOUR_WORK_FOLDER> and C:\Users\Milos; copy into SOURCE_PDFS/SOURCE_TEXT; rewrite path
# 3) metadata gaps
incomplete = [d for d in studies if not has_meta(d)]
# 4) recover metadata: Crossref by DOI, or read first lines of extracted_text file
# 5) exact-DOI duplicates -> merge (keep user-verified copy, fold in full text)
# 6) assert: 0 broken paths, 0 dup DOIs, all studies has_meta
```

## Decision rules (from user corrections)
- **Filter before add:** never dump a raw search result. Relevance + recency (default 2018+) +
  dedup, then show filtered scope to user before committing.
- **Metadata gate:** no abstract AND no authors AND no keywords = not a usable record.
- **Missing file on a real study:** mark `full_text_status: pending` (user may upload), keep metadata.
  Never leave a broken path.
- **Delete only** if provably non-existent AND obviously wrong. When in doubt: keep + flag.
- **Reclassify** mis-typed non-studies (checklists, scales, manuals, TOCs) out of `doc_type: study`.
- **Studies-only scope** for the audit pass; web/org/gov/tool refs stay `web_reference`, not audited.

## User-uploaded PDF ingestion (recurring pattern — user uploads a file, agent merges it)
The user often says: "here is the PDF, copy it to RAG, extract keywords, update the index."
Concrete sequence (proven with Cheku 2024 this session):
1. Copy uploaded file into `SOURCE_PDFS/` with a descriptive name
   (`<author>_<year>_<short_title>.pdf`); also copy any extracted `.txt`/`.md` companion.
2. Extract text + metadata via the `pdf-processing` helper
   (`skills/software-development/pdf-processing/pdf_extract.py`, run via `terminal`).
3. Locate the existing catalog entry by title or DOI. If found but `full_text_status: pending_user_upload`:
   - set `files.full_text_pdf` + `files.extracted_text` to the new absolute paths,
   - fill/verify title/authors/year/abstract/keywords from the PDF (Crossref-override by DOI),
   - flip `full_text_status: present`, add `full_text_fetched: user_upload`.
   If NOT found: create a new `study` entry (domain per topic, e.g. `Malaysian_Nursing_Studies`).
4. Re-verify the path exists on disk before saving. Assert 0 broken paths.

## Reclassify-then-merge ordering (avoids leaving junk as `study`)
Run in this order during the audit:
1. First PASS — find entries with `full_text_status: pending` and split them:
   - web/org/gov/tool refs → `web_reference` (no abstract expected; they are bibliography, not studies).
   - real studies with missing full text → fetch (direct URL) or mark `pending_user_upload`.
2. SECOND PASS — reclassify mis-typed non-studies (STROBE checklist, NASA-TLX, APA manual,
   journal TOC, courseware) out of `doc_type: study` into `instrument`/`other`/`ebook`.
   Match by title substring when the stored DOI is a `local:` placeholder that won't match.
3. THIRD PASS — exact-DOI duplicates: merge (keep the user-verified / thesis copy, fold in the
   other's full text + abstract). Report `Duplicate DOIs: 0`.
4. Recover real metadata from extracted text for any study still incomplete (e.g. a `local:`-ID
   paper whose text lives under SOURCE_TEXT/ — read it, pull title/authors/year/DOI).
5. Assert: 0 broken paths, 0 dup DOIs, all studies `has_meta`.

## After the audit
Re-save catalog, confirm: `Broken paths: 0`, `Duplicate DOIs: 0`, `Studies with complete metadata:
N/N`. Only then proceed to discovery/expansion.
