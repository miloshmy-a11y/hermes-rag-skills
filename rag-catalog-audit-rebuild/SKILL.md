---
name: rag-catalog-audit-rebuild
description: "Audit or rebuild a corrupted RAG catalog from source PDFs."
version: 1.0.0
author: Hermes Agent
license: MIT
---

# RAG Catalog Audit & Rebuild

Use when a RAG / literature index (e.g. `UNIVERSAL_CATALOG.json` + `*.json` per-paper records, or any
doc-per-entry catalog) is suspected wrong: misattributed citations (e.g. "French 2000 is the ENSS
developer, not evidence for discrimination"), instrument/population mistags, or assignments/checklists
mislabeled as published studies. Covers BOTH a safe in-place audit AND a full ground-up rebuild from
source PDFs on disk.

## When to load
- User says the index "might be wrong", "audit the catalog", "rebuild from my PDFs on D:\", or questions
  a specific citation/attribution.
- You detect systematic instrument over-assignment (same tool tagged on hundreds of unrelated papers).

## Golden rules (learned the hard way)
1. **BACKUP BEFORE ANY EDIT.** `cp UNIVERSAL_CATALOG.json backups/CAT_before_<task>_<ts>.json`.
   Everything below is reversible from there. Report the backup path to the user.
2. **cited-DOI ≠ paper-DOI.** An auto-importer can stamp a paper's *referenced* DOI onto an
   assignment / instrument / draft file. Before trusting any DOI, confirm it appears on the file's OWN
   title page (grep first ~4000 chars of extracted text). If only *other* DOIs appear, the entry is
   mislabeled — do NOT load metadata from that DOI. (This was real corruption the user caught.)
3. **Separate doc_type.** Tag every entry `study | ebook | assignment | instrument | other`.
   An instrument/questionnaire or FYP draft is NEVER a "study". Mixing them is how the index rots.
4. **Instrument/population over-assignment is the #1 bug.** Re-derive instrument tags FROM THE PAPER'S
   TEXT ("does it actually use this scale?"), not from the prior tag. Session result: ERI tags
   538 → 30 after text re-derivation; 12 spurious MBI/NWSQ/STAI removed.
5. **Crossref = authoritative metadata.** For each study with a real `10.x` DOI, call
   `https://api.crossref.org/works/<DOI>` (User-Agent header) for clean title/authors/year/journal/
   abstract. Far better than regex-parsing PDF first pages (layouts vary wildly; one parser grabbed
   "2015. Obzornik zdravstvene nege, 49(3)…" as a title).
6. **Defer, don't assume-corrupt.** If a source set (e.g. a Mendeley export) has some unreadable
   files, the user may know some open fine. Do NOT declare the whole set corrupt — defer it; only
   exclude genuinely broken files (pdftotext rc != 0).
7. **Dedup by normalized real DOI (case-insensitive) + normalized title.** Report "duplicate count = 0".
8. **VERIFY before merging, never blindly copy.** When re-importing entries from a PREVIOUS/old
   catalog (e.g. the user points you at an old `UNIVERSAL_CATALOG.json`), do NOT trust its records.
   Re-resolve each `10.x` DOI via Crossref and confirm the title matches; for local-DOI / no-DOI
   records, web-search to confirm it is a real citable work. Drop malformed-DOI placeholders
   (`10.1155/2023`, `10.1093/humupd`) and unverifiable student files. In one session, re-verifying
   92 old ENSS/SelectedStudies candidates caught 13 junk malformed DOIs and recovered 69 real studies.
9. **Prefer the obvious academic subtree over whole-drive scans.** User said studies live under
   `OUM` and its subfolders — do NOT scan all of `D:\` (1,182 PDFs of which most are bitcoin/visa/
   accounting junk). Target `<YOUR_WORK_FOLDER>\sayang\OUM` + `mendeley import`; that's where the ~600 article
   PDFs are. Saves time and avoids junk.
10. **INCLUSIVE scope — never advise excluding doc types.** The user explicitly plans to include theses,
   ebooks, instruments, and web/org references in the RAG, not just peer-reviewed `study` PDFs. Do NOT
   edit skills, search code, or advice to hard-filter to `study`-only. Keep `doc_type` as a FILTER
   parameter (study | ebook | assignment | instrument | org_doc | gov_doc | tool | web | other). A
   search for "studies" applies the filter; a search for "all my sources" does not. Non-DOI
   thesis-bibliography entries (HSE, WHO, OECD, MOH Malaysia, hospital sites, sample-size calculators)
   are legitimate `org_doc`/`gov_doc`/`tool`/`web` entries — dedup by `url`, store `url` in
   `files.full_text_html`. (User correction this session: "do not edit skill to exclude this
   possibility in the future.")
11. **Attached bibliography must be FULLY covered (don't drop cited works).** When the user hands a
   `references.txt` / pasted bibliography, treat 100% coverage as the success bar:
   - Parse every entry; extract DOI (regex `10\.\d{4,9}/[^\s)]]+`) OR URL.
   - For each DOI: if already in catalog → OK; else Crossref-verify and ADD as `study`
     (`Thesis_References` domain, `cited_in_thesis:true`).
   - For non-DOI entries: still ADD as `org_doc`/`gov_doc`/`tool`/`web` (dedup by `url`). Reclassify
     real articles that lack a DOI in the citation (e.g. MJPHM, e-mjm PDFs) as `study` and fetch their
     OA PDF if available.
   - Report coverage `X/Y` and the 0-missing target. Proven: 91/91 attached refs covered (79 already in
     catalog, 12 non-DOI added; 3 as study w/ 2 PDFs fetched).
12. **Semantic Scholar = citation intelligence layer (Crossref has none).** After metadata is in place,
   enrich every `study` with live citation data via the Semantic Scholar Graph API (see `semanticscholar-skill`
   + its `references/citation_enrichment.md`):
   - `batch_papers(ids, fields="...citationCount,influentialCitationCount,referenceCount,externalIds")`
     posts up to 500 DOIs in ONE request — avoids per-call throttling. Merge `citation_count` etc. into
     each catalog entry. Proven: 234/242 catalog DOIs enriched in one pass.
   - Forward citations (`get_citations`) build a "citation pedigree" for scale papers (ENSS French 2000 →
     Revised NSS Pavek 2024) — strong Discussion support.
   - Recommendations (`recommend` with ENSS+NSS seeds) surface related work but are SEED-MATCHING, NOT a
     literature-gap analysis. Do NOT present recommendation output as evidence of a gap (e.g. "no Malaysian
     ENSS studies found" is the algorithm's seed-matching, not a finding — the user's stated knowledge that
     their thesis is the Malaysian ENSS study they know of is the ground truth). See `verified-academic-research`
     pitfall on not fabricating gaps.

## Rebuild recipe (from source PDFs on disk)
See `references/catalog_audit_rebuild.md` for the full, copy-pasteable script outline:
inventory (hash first 1MB for dedup) → copy good PDFs (skip corrupt) → extract text with pdftotext →
classify by reading first page → Crossref-verify studies → build deduped catalog → merge thesis/key docs.
 Full-text fetch (Step 8) detail and a re-runnable runner live in `references/fulltext_retrieval.md` and
 `scripts/download_fulltext.py`. The full-disk article-harvest recipe (Step 9) is in
 `references/full_disk_scan.md`. **Semantic Scholar citation enrichment (Step 12) recipe lives in
 `references/semantic_scholar_enrichment.md`** — install `semanticscholar-skill` (`s2.py`) first.

## Step 7 — Cross-check against the thesis's OWN bibliography (context-limited)
A disk rebuild only indexes PDFs you pointed it at. The papers the thesis actually CITES often live in
a different tree (e.g. a deferred Mendeley export). In one session the rebuild captured only **3 of 73**
cited references; **70 were missing** and had to be added back. Run this as a distinct pass:
1. Extract the bibliography: find the `REFERENCES` header, drop preceding body/appendix lines, then
   split entries on `^Author, X. (YYYY).` patterns that contain a `doi.org` / `10.x` token. NOTE the
   reference list is usually far down the extracted text (lines ~730+ in a 950-line thesis) — NOT right
   after the "REFERENCES" string, which may precede appendices/tables of figures.
2. Save as `THESIS_REFERENCE_LIST.json` (raw bib strings).
3. Process **in batches of 8, one entry at a time** — a whole 73-item list blows the context window if
   loaded at once. Use `scripts/ref_check_batch.py <start>`: verifies each DOI via Crossref, reports
   OK / CROSSREF_FAIL / NOT_IN_CATALOG, ADDS missing verified studies (domain `Thesis_References`,
   `cited_in_thesis:true`), persists progress to `REF_CHECK_PROGRESS.json`. Run `0`, then `8`,`16`,…
   until all checked. Outcome target: cited/total, 0 missing, 0 Crossref failures.
4. Added refs have Crossref metadata but **empty `full_text_pdf`** until the deferred source is imported —
   record that gap; don't claim they have full text.

## Step 8 — Fetch full text for indexed-but-PDF-less references
A disk rebuild (or thesis-ref add) can leave studies with correct metadata but no local PDF. Retrieve
the open-access full text **legitimately only** (Unpaywall / PMC / publisher OA / `web_extract` HTML;
never Sci-Hub/LibGen). The working pipeline is in `references/fulltext_retrieval.md`.
**Primary method — `web_extract` HTML (highest success):** resolve each DOI to its publisher landing
URL (Crossref `URL` field or `doi.org` redirect), then fetch via `web_extract` inside `execute_code`
(`from hermes_tools import web_extract`, batch ≤5 DOIs/call, `char_limit=60000`). The HTML page holds
the FULL paper (~50–60k chars markdown). In one session this retrieved **46/50** DOIs that failed PDF
download — so expect **~63/70** thesis refs to get full text (13 PDF + 50 HTML), NOT ~13/70.
Key gotchas: (a) PDF route: validate bytes start with `%PDF-` AND > 5 KB — publishers often return an
HTML landing page instead of a PDF (BMC `track/pdf` now serves HTML); (b) `web_extract` is NOT importable
from terminal Python (`ModuleNotFoundError: hermes_tools`) — run the fetch loop via `execute_code`;
(c) bot-walled sites (BMJ Open, OUP) and subscription instruments (JSTOR/APA/Elsevier scale papers)
stay metadata-only — they need a real browser session (the `browser` tool) to fetch; record those with
`full_text_html:''` rather than claiming fetched; (d) `cp` the catalog to `backups/CAT_before_download_<ts>.json`
before writing paths.

## Step 9 — Full-disk scan of the user's own PDF library (the REAL article pool)
When the user says "I have 100-200 peer-reviewed articles across my disk / my thesis," the catalog is
probably missing most of them because a prior rebuild only indexed a few pointed-at folders. Scan the
user's actual research subtree (not the whole drive — see rule 9). Working approach (proven this session):
1. `find` the subtree for `*.pdf` (e.g. `<YOUR_WORK_FOLDER>\sayang\OUM` + `<YOUR_WORK_FOLDER>\mendeley import` → ~600 PDFs).
2. Extract text with pdftotext (run via `terminal`, absolute path) into a `DISK_TEXT/` dir. KEEP the
   extracted text across runs — re-runs are then near-instant.
3. **Classifier pitfall (cost a revert this session):** a naive "has abstract + references → study"
   rule MISLABELS course modules, anatomy lectures, ebooks (front-matter heavy), and FYP declaration
   forms as `study`. First naive pass added 145 junk entries (74 "thesis" were actually declaration
   sheets/forms). **Fix = DOI-first:**
   - For every file, regex a DOI from the WHOLE text (not just first 8k — 63/226 DOIs sat deeper).
     If a DOI exists → `https://api.crossref.org/works/<DOI>` → if Crossref resolves, ADD as `study`
     with Crossref's authoritative title/authors/year/journal. Dedup by DOI against the catalog.
     Skip DOI files already present (real dedup — ~180 were already in catalog).
   - For NO-DOI files → only add if they have `abstract` (first 4k) AND `references`/`bibliography`
     (last 5k) AND are not course/ebook/form junk (regex out `module code`, `credit hour`, `tutorial`,
     `declaration`, `borang`, `application form`, `lecture`). Title via a smarter heuristic (skip
     'abstract/journal/vol/doi/fig' leading lines); flag as `LOCAL (no DOI) — unverified`.
   - **Skip landing pages** (ResearchGate "see discussions, stats", Springer/BMC "log in to a free
     account") — they are not articles.
4. If a classifier pass goes wrong, **revert to the pre-scan backup and rerun** — do not patch junk in
   place. Outcome this session: 256 studies total (241 Crossref-verified), 0 duplicate DOIs, from a
   369-doc catalog. Meets a "~100-200 peer-reviewed articles" user expectation.

## Tooling pitfalls (Windows / Hermes desktop)
- **pdftotext**: available in the interactive terminal but NOT on PATH inside `execute_code`'s Python
  sandbox (subprocess can't resolve it). Use the absolute Windows path
  (`cygpath -w /mingw64/bin/pdftotext` to find it, typically
  `C:\Users\<user>\scoop\apps\git\2.52.0\mingw64\bin\pdftotext.exe`). Run extraction scripts via
  `terminal`, not `execute_code`.
- **Mendeley exports: some "PDFs" are gzip, not PDF.** Check magic bytes — real PDF starts with
  `%PDF`, gzip starts with `\x1f\x8b`. For gzip files, `gzip.decompress()` then test the result for
  `%PDF`; if a PDF is inside, extract text normally (it counts as usable), else it is HTML/metadata —
  skip it. In one session 16/78 Mendeley files were gzip; 5 held a usable PDF, 11 were HTML/metadata.
  So a gzip file is NOT automatically "corrupt" — decompress before judging.
- **python-docx not installed** → extract .docx by `zipfile` + regex on `word/document.xml`.
- **fitz/PyMuPDF**: check before relying on it; in one session it was importable from terminal but not
  from the execute_code sandbox. pdftotext binary is the reliable choice.
- **execute_code sandbox quirks:** `hermes_tools` (e.g. `web_extract`) is ONLY importable inside
  `execute_code` — NOT from `terminal` Python (`ModuleNotFoundError: hermes_tools`). Conversely,
  `pdftotext` binary + `glob`/`runpy` behave better from `terminal`. Pattern that worked: write the
  script file, then run it with `runpy.run_path('<path>')` inside `execute_code` when you need BOTH
  `hermes_tools` AND file ops. `import json/re/glob/urllib.request` must be EXPLICIT inside execute_code
  (not auto-imported). `from hermes_tools import web_extract` must be removed if running via terminal.
- **Path typo trap:** writing scripts via `write_file` with a path like `.../uiversal_rag/...` (a
  one-char slip) creates a stray dir; `mv` it back into `universal_rag/` and `rmdir` the typo dir.
- **Rebuild only sees the folders you point it at.** After building from disk, ALWAYS cross-check the
  catalog against the thesis's own bibliography (Step 7) — cited papers in a deferred/other tree will
  be absent. In one session: 70 of 73 cited refs were missing post-rebuild until added from Crossref.

## Scope discipline
- Exclude coursework/notes trees (e.g. `...\docs\` at 4.3GB) unless the user wants them.
- The user's "literature" set and "working files" (drafts, supervisor forms, ethics letters) are
  different things — keep them in separate domains so a search for studies doesn't surface a form.
- Attribution-level errors (citation misused, not just mislabeled) need per-paper reading of the
  Discussion; flag this as a separate, focused pass on the user's own cited papers — don't pretend a
  structural grep catches it.

## Verification discipline (USER-ENFORCED audit rules — learned this session)
When auditing an existing index (not just rebuilding from disk), these rules are mandatory:

**V1 — FILTER BEFORE YOU ADD.** A discovery search (OpenAlex/S2/Crossref) returns N candidates; do
NOT add all N. Filter by (a) relevance — title/abstract must match the topic; (b) recency — apply a
year cutoff the user implies (default 2018+ unless told otherwise); (c) dedup vs existing catalog.
Then SHOW the filtered count + sample titles to the user BEFORE committing. Dumping 220 unfiltered
candidates when asked for "studies" produced pure noise and had to be rolled back.

**V2 — METADATA COMPLETENESS GATE.** A RAG entry with no abstract AND no keywords AND no authors is
not usable. Before adding/expanding, each study needs: title, year, identifier (DOI or url), and ≥1 of
{abstract, authors, keywords/tags}. Recover real metadata from Crossref (by DOI) or from the extracted
text file (read first lines) — never leave a junk title like "Open Access Original DOI: 10.x…". User-
verified thesis links are authoritative: keep them, only fill missing fields.

**V3 — LINE-BY-LINE VERIFY AUDIT (run before any expansion).** Audit the existing index entry-by-entry,
**studies only** (skip ebook / website / policy / instrument / org_doc / gov_doc / tool / assignment):
1. Does `files.*` path exist on disk? If yes → open it, confirm title/authors/year in the index match
   the content; fix mismatches from the file. If missing → locate on source disk by basename; copy/relink
   (absolute path under SOURCE_PDFS/SOURCE_TEXT). If still missing and it's a real study → set
   `full_text_status: pending` (user may upload later); keep metadata, never leave a broken path.
2. Stub (<3KB) or empty extracted text → flag `notes.fulltext_status='stub_or_empty_needs_retry'`.
3. Missing metadata → enrich from Crossref (DOI) or extracted text.
4. Only DELETE an entry if provably non-existent AND obviously wrong (garbage title, no identifier, no
   content). When in doubt → keep + flag. User: "do not delete records; mark pending / note as wrong."
5. Reclassify mis-typed entries (STROBE checklist, NASA-TLX, APA manual stored as `doc_type: study`)
   to true type — correction, not deletion.
6. Resolve exact-DOI duplicates by merging (keep user-verified copy, fold in its full text).
After the pass: assert 0 broken paths, 0 duplicate DOIs, all studies `has_meta`.

**V4 — SCOPE IS STUDIES-FIRST for literature audits.** When the user says "studies", operate on
`doc_type: study` only. Web/org/gov/tool references (WHO, ILO, HSE, OECD, MOH, Raosoft, hospital sites)
are legitimate bibliography entries but NOT studies — keep as `web_reference`, don't force abstracts,
don't audit them in a "studies" pass. (See also rule 10 / Step 11 on inclusive scope for the whole
catalog — those are kept; V4 is about scoping a *studies* verification pass, not excluding them globally.)

See `references/verify_audit_discipline.md` for the copy-paste audit loop.

## Related
- `general-purpose-rag` (the search/import skill this catalog belongs to). It is currently user-owned,
  so the curator could not patch it directly with these rules. If you want them merged, the user must
  run `hermes curator adopt general-purpose-rag` first.
