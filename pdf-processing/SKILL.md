---
name: pdf-processing
description: Robust PDF text + metadata extraction for the Hermes RAG pipeline. Use whenever you need to extract text from a PDF, recover a paper's title/authors/abstract/keywords, or ingest a user-uploaded PDF into the universal_rag catalog. Encodes the critical environment gotcha (execute_code venv has no PDF libs) so it is never rediscovered.
---

# PDF Processing (Windows / Hermes)

## CRITICAL ENVIRONMENT FACT (learned the hard way)
There are TWO Python interpreters on this machine and they differ:

| Interpreter | Path | PDF libs? | pip? |
|---|---|---|---|
| **terminal** `python3` | `C:\Python314\python.exe` (3.14) | ✅ PyMuPDF 1.28 (fitz), ✅ `pdftotext` CLI (MinGW) | yes |
| **execute_code** venv | `C:\Users\<USER>\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe` (3.11) | ❌ NO pdf libs | ❌ no pip |

**`import fitz` inside execute_code FAILS (ModuleNotFoundError).** Do NOT try to install into the execute_code venv (no pip). Instead, **run all PDF work through `terminal()`**, which uses the 3.14 interpreter that has PyMuPDF.

## The working pattern
A helper script `pdf_extract.py` (same folder as this SKILL.md) does the extraction.
Call it from execute_code via `terminal()`:

```python
from hermes_tools import terminal
SCRIPT = r"C:\Users\<USER>\AppData\Local\hermes\skills\software-development\pdf-processing\pdf_extract.py"
pdf   = r"C:\Users\<USER>\AppData\Local\hermes\cache\web\universal_rag\SOURCE_PDFS\some.pdf"
out   = r"C:\Users\<USER>\AppData\Local\hermes\cache\web\universal_rag\SOURCE_TEXT"
r = terminal(f'python3 "{SCRIPT}" --pdf "{pdf}" --outdir "{out}"')
print(r["output"])   # JSON: {ok, method, chars, pages, empty_pages, txt, meta}
```

## Extraction strategy (in priority order)
1. **PyMuPDF (fitz)** — primary. Best text + layout, fast, gives page count + empty-page count.
2. **`pdftotext -layout`** (MinGW CLI) — fallback if PyMuPDF unavailable.
3. **OCR stub** — if NO text layer (image-only scan), the script exits code 3 with
   `needs_ocr: true`. Do NOT silently claim success. Either ask the user to upload a
   text version, or install/run tesseract. (Never fabricate extracted text.)

## Outputs (per PDF, stem = filename without .pdf)
- `<outdir>/<stem>.txt` — full extracted plain text
- `<outdir>/<stem>_meta.json` — recovered metadata draft:
  `{title, authors, year, abstract, keywords, pages, empty_pages, method, char_count}`

## Metadata recovery is HEURISTIC — treat as DRAFT, verify
The `_meta.json` title/authors/keywords are regex-guessed from the text. They are
often imperfect (e.g. catches affiliation lines, misses one author). **Authoritative
metadata precedence:**
1. **Crossref** (`https://api.crossref.org/works/<DOI>`) — if a DOI is known
2. **OpenAlex** (`https://api.openalex.org/works/doi:<DOI>`) — concepts/keywords
3. **User-provided citation** (e.g. from `references.txt` or a manual upload note)
4. **Filename** (paper-fetch / EBSCO naming often encodes author_year)
5. _meta.json from this script — LAST, as a hint to confirm against

Always verify the recovered title/authors against the abstract before writing to the
catalog. If a DOI exists, Crossref-override the heuristic values.

## Ingesting a user-uploaded PDF into the RAG (proven workflow)
1. Copy the uploaded file into `SOURCE_PDFS/` with a descriptive name:
   `cp "<upload>" "SOURCE_PDFS/<author>_<year>_<short_title>.pdf"`
2. Run `pdf_extract.py` → produces `.txt` + `_meta.json`.
3. Load `_meta.json` in execute_code; build/merge the catalog entry
   (`doc_type: study`, `files: {full_text_pdf, extracted_text}`, `full_text_status: present`).
4. If a DOI is known, Crossref-verify title/authors/year and override the heuristic.
5. Add `abstract` (from PDF or Crossref), `keywords` (from Crossref/OpenAlex or PDF),
   `tags`, `country` (MY for Malaysian), `domain`.
6. Save catalog; confirm `full_text_status: present` and both file paths exist on disk.

## Pitfalls
> Windows/MSYS path + interpreter gotchas are consolidated in `references/windows-environment-notes.md` (single source) — keep edits there.

- **Never `import fitz` in execute_code** — use `terminal()` with the helper script.
- **Backslash paths** in inline `python3 -c "..."` break (`\U` unicode error) — prefer
  forward slashes or call the script via a file. In execute_code, `os.path` is fine.
- **Don't trust empty-page count blindly** — some PDFs embed text in images; the
  `empty_pages` field flags this so you can decide on OCR.
- **Don't redownload** a PDF that's already in `SOURCE_PDFS/` (check basename first).
- The helper's metadata regex is best-effort; **verify, don't assume**.

## Paywalled full text → extract S2 paper-page HTML (key lesson 2026-08-03)
When a PDF is behind a paywall (Wiley/Elsevier/SAGE etc.), **direct PDF download 403s**
and `web_extract` on the `doi.org` landing page returns 0 chars (publisher blocks bots).
The reliable workaround: **extract the Semantic Scholar paper page**, which is bot-accessible
and embeds the abstract + references + often full text:
```python
from s2 import get_paper
from hermes_tools import web_extract
p = get_paper(f"DOI:{doi}", fields="paperId,title")
url = f"https://www.semanticscholar.org/paper/{p['paperId']}"
r = web_extract(urls=[url], char_limit=10000)
text = r['results'][0]['content']   # save as <stem>.md in SOURCE_TEXT/
```
This recovered full text for ~46/47 paywalled 2020+ thesis refs in one pass. Mark the
entry `full_text_status: html_extracted` and store the `.md` path in `files.full_text_md`.
Not a substitute for a real PDF when one is obtainable, but far better than nothing for a
lit review. (Open-access publishers — MDPI, PMC, Frontiers, PLOS, Hindawi, BMJ Open —
often DO serve real PDFs via their article URL; try those first.)

## Test status (2026-08-03)
- Cheku 2024 PDF (754KB, 11pp): PyMuPDF extracted 48,052 chars, 0 empty pages. ✅
- `pdftotext -layout` produces equivalent text as fallback. ✅
- Metadata heuristic: year + abstract reliable; title/authors need verification. ✅ (as draft)
- S2 paper-page HTML extraction: recovered full text for 46/47 paywalled thesis refs. ✅
