---
name: rag-catalog-auditing
description: "Audit, verify, dedup, and rebuild a RAG literature catalog (integrity, file-mismatch, instrument indexing)."
category: research
---
# RAG Catalog Auditing & Integrity (consolidated)

Consolidated from: rag-catalog-audit-rebuild, rag-corpus-integrity, rag-engineering-patterns,
research/rag-catalog-audit, research/rag-catalog-discipline, research/rag-workflow-discipline.

The catalog is GENERAL / topic-agnostic. Crossref is the authoritative metadata source.
Full-text integrity (file == right paper) is load-bearing: if the file is wrong, the
index derived from it is wrong — fix BOTH in one pass.



<!-- ===== Merged from: rag-catalog-audit-rebuild ===== -->

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
   **Co-verify the file's IDENTITY too:** a correct DOI + Crossref match does NOT mean the stored
   `extracted_text` is the right paper. A file can hold a completely different document (e.g. the ENSS
   French-2000 paper stored a p53/breast-cancer article). When auditing, run a title-overlap check
   (see `rag-verification-protocol` → `references/fulltext-integrity.md` + `scripts/audit_fulltext_mismatch.py`):
   if <25% of the title's content words appear in the file, read the file head — if it's an unrelated
   paper / publisher cover page / failed-scrape landing page, rebuild the file AND the indexed fields
   (title/journal/year/authors/brief_abstract/measures/doc_type) from Crossref/PubMed in ONE pass.
   Never leave a half-fixed record (corrected country but brief_abstract still from the bad file).
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

## Audit methodology — random small-batch + error-rate target (USER-CORRECTED this session)
Large systematic passes through the WHOLE catalog miss errors that small focused batches catch.
The user diagnosed it directly: *"maybe you work in large chunks and so lost focus on details"* — and
endorsed random sampling of ~10–12 records per round as the higher-fidelity method. Encode this:
- **Audit in random/small batches, not one giant pass.** Sample N (10–12) full-text records, verify
  EACH against its actual file (title-overlap + read head), fix only genuine issues, repeat. Random
  sampling surfaces different records each round; after ~8–10 rounds the residual error rate drops
  below 5% and approaches 0%. (A prior "audit all 252 at once" attempt missed country + measures
  errors that the small-batch rounds caught.)
- **Set an explicit error-rate target: <5%, ideally 0%.** After each round, quantify genuine issues
  remaining (NOT scanner false positives) as % of full-text records. Stop when <5%. Report the number
  + the false-positive types you excluded, so the user sees the true rate, not the raw scan.
- **Verify MULTIPLE dimensions, not just country.** Country is the easiest to check but not the only
  corruption. Each round also check: (a) is the stored `extracted_text` the RIGHT paper (title-overlap
  <25% ⇒ read head; unrelated paper / publisher cover page / "javascript disabled" landing = MISMATCH);
  (b) is `doc_type` populated & plausible; (c) does `full_text_status` match the file on disk. These
  catch the silent corruptions (e.g. ENSS French-2000 stored a p53 article; Karasek-1979 stored a 2019
  HEMS paper; NSS-1981 stored an HCV article) that a country-only audit misses entirely.
- **Add a 4th dimension: file-INTEGRITY signatures + field backfill.** The title-overlap check MISSES
  two systemic ingestion bugs: (A) PRISMA/scoping-review TEMPLATE swapped for the article ("Tips for
  reporting this item…" boilerplate, not the paper); (B) OUM coursework/student-assignment WRAPPER
  swapped for the article (Chittra/Badrul/MPU module text). Also check (C) `status=present` but NO file
  path on disk, and (D) `keywords_llm` emptiness on real research (backfill by READING the abstract —
  per-study, careful, not a dump). Full signatures + backfill recipes (verified_at churn fix, relevance
  tagging, OA chain) are in `references/fulltext_integrity_signatures.md`. Detection regexes:
  ```python
  PRISMA=["tips for reporting this item","eligibility criteria with a rationale","preferred reporting items","identify any specific restrictions such as date","data charting form"]
  COURSE=["open university malaysia","oum","chittra selvi","badrul hisham","final year project","project paper submitted","assignment 3","matrix no","learning centre","appreciation of ethics"]
  # flag if (PRISMA hit OR COURSE hit) and title_not_in_text and len(t)<8000
  ```
- **TRAP: external audit reports may target a DIFFERENT catalog/codebase.** If the user pastes a review
  from another agent citing "722 documents", "quality_score", "add_documents_from_folder()",
  "domain: OUM_Research" — those functions/fields may not exist HERE. Before acting: (1) count real docs
  (`len(data["documents"])` — this catalog had 526, not 722); (2) check which claimed fields exist;
  (3) grep the actual search code for which fields it reads (`official_keywords` IS read by
  `general_rag.py`/`hybrid_search.py`; `quality_score` does NOT exist here). Act only on points REAL for
  this catalog; tell the user which claims were from a foreign system. The *spirit* (bulk ingestion left
  quality gaps) may be valid even when the specifics are wrong. (This session: Claude's report was
  partly valid — `official_keywords` 85% empty and `verified_at` 99% missing ARE real in this code — but
  the 722-doc premise and function names were from a different codebase.)
- **When a file is wrong, fix file + indexed fields in ONE pass** (reinforces Golden Rule #2). Do NOT
  fix country but leave `brief_abstract`/`measures`/`keywords_llm` derived from the bad file. User:
  *"if full text was wrong so is likely also index record ... better save energy and verify both at
  the same time."* Re-derive title/journal/year/authors/brief_abstract/measures/doc_type from
  Crossref/PubMed (never from the corrupted file). Cleared `keywords_llm`/`measures` from the bad
  text; refill only after a real body/abstract is in place.
- **On acquiring new full text, do comprehensive re-indexing immediately** (same pass). User: *"once
  you adding any new full text do directly more comprehensive indexing."* After writing the real text,
  populate measures (from actual text, e.g. UWES/MBI for a job-engagement study), doc_type (from
  abstract/methods), brief_abstract, keywords_llm — don't leave it for a later pass.
- **Sequence: acquire missing → verify → backup.** User: *"try first get those missing papers, if
  don't have nevermind proceed next with verification before backup."* Attempt OA retrieval of
  `meta_only` records FIRST; for those with no OA (paywalled/foundational), leave valid `meta_only`
  with Crossref metadata (nevermind). THEN run a verification pass. THEN commit/push backup.
- **Verify-before-backup, and watch the save-failure trap.** A script that writes text files to disk
  but CRASHES before `json.dump` leaves the catalog JSON out of sync with disk (real file present, but
  `full_text_status` still says `meta_only`). After any multi-record edit script, re-read the catalog
  and assert `full_text_status` matches the on-disk file size (>800B for present/abstract_only). If a
  script aborted mid-loop, the disk files are real but the JSON save never ran — re-apply the status
  updates and save. Always run a FRESH ad-hoc verification (not a cached/suite-green claim) before
  pushing: catalog valid, 0 wrong-body files, 0 mismatched, status/disk consistent, country ~0%.
- OA re-acquisition chain that worked (see `references/random_audit_methodology.md` for the script
  outline): PMC `fullTextXML` (Europe PMC `rest/<PMCID>/fullTextXML`) → EPMC abstract
  (`rest/search?query=DOI:`) → Semantic Scholar `openAccessPdf` → Unpaywall `api.unpaywall.org/v2/<DOI>`
  → publisher OA PDF (Nature `/articles/<id>.pdf`, DovePress getfile). Crossref for metadata always.

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
   the content; fix mismatches from the file. **Also confirm the FILE IS THE RIGHT PAPER** (not a
   mismatched/empty file): run the title-overlap check — if <25% of the title's content words appear
   in the file, read the file head; an unrelated paper / publisher cover page / "javascript is disabled"
   landing page means the file is wrong → rebuild file + indexed fields from Crossref/PubMed in one pass
   (see `rag-verification-protocol` → `references/fulltext-integrity.md`). If missing → locate on source
   disk by basename; copy/relink (absolute path under SOURCE_PDFS/SOURCE_TEXT). If still missing and it's
   a real study → set `full_text_status: pending` (user may upload later); keep metadata, never leave a
   broken path.
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

- `references/verify_audit_discipline.md` — copy-paste audit loop for V1–V4.
- `references/random_audit_methodology.md` — random small-batch audit loop + OA re-acquisition chain
  + verify-before-backup recipe (USER-CORRECTED: small batches > one giant pass; fix file+index in
  one pass; acquire→comprehensive-reindex→verify→backup order).
- `references/fulltext_integrity_signatures.md` — PRISMA-template / OUM-coursework-wrapper / status=
  present-no-file mismatch signatures (title-overlap detector MISSES these) + `keywords_llm` backfill
  discipline + `verified_at` churn fix + `relevance` tagging + the foreign-audit-report trap.

## Related
- `general-purpose-rag` (the search/import skill this catalog belongs to). It is currently user-owned,
  so the curator could not patch it directly with these rules. If you want them merged, the user must
  run `hermes curator adopt general-purpose-rag` first.



<!-- ===== Merged from: rag-corpus-integrity ===== -->

# RAG Corpus Integrity Audit & Repair

## When to use
- After a bulk PDF/full-text extraction pass (files get **swapped** — a real, observed failure: an ENSS paper's file held a p53 article; Karasek 1979 held a 2019 HEMS-physicians paper; NSS 1981 held an HCV article).
- Before answering a literature query where you rely on `brief_abstract` / `keywords_llm` / `measures` — those fields are **derived from the extracted text**, so a wrong file silently poisons them.
- When the user says "verify the index," "check for errors," or "audit random records."

## THE CORE PRINCIPLE (load-bearing)
**If the full text is wrong, the index record derived from it is also wrong. Fix BOTH in one pass — do not fix only the file or only the metadata.**

Concretely, for any corrupted record:
1. Replace the `extracted_text` file with **Crossref/PubMed-verified** content (title + journal + year + authors + real abstract if available).
2. **Re-derive** `title`, `journal`, `year`, `authors`, `brief_abstract` from that authoritative source — NOT from the old bad file.
3. **Clear** `keywords_llm` and `measures` that were derived from the wrong text; refill them only after a real body/abstract is acquired. Never invent an abstract — set `full_text_status: meta_only` and write a one-line honest citation as `brief_abstract`.
4. Set `metadata_source: "Crossref (verified <date> after mismatch fix)"`.

## Verification workflow (small batches, not one giant pass)
The user observed: large batch passes miss errors; **random/small (~10-record) verified batches catch them**. Process records in chunks of ~10–12, reading each flagged file's head to confirm it's the RIGHT paper.

For each record with an `extracted_text`:
1. **Exists & real?** size < 800B, or contains "this page can't be found" / "Skip to main content" / "Javascript is currently disabled" → empty/failed scrape.
2. **Right paper?** Normalize title (replace non-breaking spaces, hyphens, `&amp;`) and test whether ≥25% of its significant words appear in the text. Below that → likely a **mismatched file**.
3. **PubMed.gov banner trap:** a file beginning "Skip to main content … An official website of the United States government" is the *site chrome*, not the article — the study country is NOT "US" from that; re-fetch from PMC.
4. **Country:** read the affiliation sentence ("University of X, City, COUNTRY"). Filter false positives: German reprint of a US paper (text shows DE but study is US); download-IP/"NIH Malaysia" watermark ≠ study country; multi-country author lists for reviews (leave `None`).

## False-positive filters (do NOT "fix" these — they are correct)
- `10.2307/2392498` (Karasek 1979): text shows "DE" = German reprint → keep `None` (or US if verified).
- `10.1038/138032a0` (Selye 1936): "ET"/"Ethiopia" in text = a citation, not the study.
- A scoping/systematic review whose text says "The USA dominates the research" → that's a *finding*, not the study country → keep `None`.
- Multi-country validation/comparative studies → `None` is correct.

## Reusable scripts (in `scripts/`)
- `audit_fulltext_mismatch.py` — full-coverage detector: flags empty/placeholder and title-overlap<25% (mismatched) files across all full-text records. Read-only report.
- `fix_record_from_crossref.py <DOI>` — rebuilds the file + indexed fields for one DOI from Crossref (or PubMed for PubMed-URL DOIs). One-pass fix.
- `dedup_check.py [catalog.json]` — **duplicate detector (READ-ONLY report)**. Flags exact DOI collisions, same-title/different-DOI pairs, and Jaccard>=0.6 near-dup titles, and classifies each with the correct action. Run this BEFORE any dedupe pass.

## Duplicate detection & SAFE MERGE (validated lesson, 2026-08-04)
**Two records sharing a DOI is NOT automatically a true duplicate.** Either:
(a) they are the **same study under two DOIs** (preprint `10.21203/rs.3.rs-…` ↔ published `10.1136/…` — merge), or
(b) they are **DIFFERENT studies where one carries a WRONG DOI** (a different paper cloned a real DOI) — these must be **FLAGGED FOR REVIEW, never deleted**.

**Workflow (loop until the catalog is stable, then re-run `dedup_check.py` to confirm 0 hazards):**
1. Run `dedup_check.py` to enumerate candidates.
2. For each candidate, **verify by title + authors + year**, not by DOI alone:
   - Same title/authors/year but different DOI → **TRUE DUPLICATE** → merge.
   - Different title/authors but same DOI → **WRONG DOI on one record** → flag for human review; do NOT delete.
3. **Merge recipe (true dup only):** keep the **published/canonical DOI**; backfill any field the canonical lacks from the stub; remove the stub; set `merged_from: <removed-doi>` + `merge_note:` on the canonical for traceability. Always backup the catalog first.
4. **Re-run `dedup_check.py`** after edits — assert 0 DOI collisions and 0 same-title/diff-DOI pairs. If a wrong-DOI-different-study case is simulated, assert it is *detected* (routed to review), not silently dropped.
5. **Preprint↔published pairs** are the most common true-dup shape: identical title + same author set + same year, one DOI on a preprint server. Merge to the journal DOI.

**Pitfalls:**
- ❌ Never delete both records of a "duplicate" or blindly keep the first by DOI order.
- ❌ Never assume a shared DOI means identical content — the wrong-DOI-on-different-study case is real and deletion loses a genuine paper.
- ✅ Keep merge provenance (`merged_from`) so audits can reconstruct why a record vanished.

## Pitfalls
- **Never trust keyword co-occurrence for country** — comparison countries and cited locations inflate false positives. Verify via affiliation, not title scanning.
- **Never judge a DOI wrong from fallback full text** — resolve the DOI via Crossref first (established rule). A 404/failed S2 fetch is not proof the DOI is bad.
- **Don't pad `keywords_llm` just to fill it** — only add keywords from real abstract/body. Off-topic records should be left thin, not force-enriched.
- **Backup before bulk edits:** the catalog JSON is the source of truth; commit/push to its GitHub backup after each audit round.

## See also
`references/technique.md` for worked examples from a real audit session (13 corrupted files found & repaired, error rate 5.2% → 0% corrupted).



<!-- ===== Merged from: rag-engineering-patterns ===== -->

# RAG Engineering Patterns — topic-agnostic search + instrument-aware indexing

Patterns distilled from a multi-session build of a 500+ doc literature RAG. The recurring,
expensive mistake was **hardcoding the user's domain** (nurses / Malaysia / stress) into the
search engine. The catalog is GENERAL; the engine must stay general.

## Pattern 1 — Never hardcode population/geo/topic in executable logic
Population, geography, and domain vocabulary must be QUERY-DERIVED, never baked in.
- Detect population/geo from the query via maps (`POP_DETECT`, `GEO_DETECT`), applied as
  OPTIONAL filters only when the query contains those words.
- A query "diabetes self-management" searches the whole catalog; "nurses in Malaysia"
  auto-filters to nurses+Malaysia because those words are IN the query — not because of a gate.
- Public/sharable version ships `DEFAULT_POPULATION=None`, `DEFAULT_GEO=None`.
- If you must support a personal bias, set those two constants locally — do NOT add `if
  population=='nurse'` branches.

### Pitfalls caught in review (do NOT reintroduce)
- `re.escape(population)` + `\b` boundaries FAILS on plurals/derivatives:
  `"nurse"` won't match `"nurses"`; `"malaysia"` won't match `"malaysian"`.
  Use `re.escape(pop) + r'[a-z]*'` or explicit stem handling.
- `REF_INTENT` regex containing bare `scale`/`measure` flips "Nursing Stress Scale" queries
  into reference mode (the single instrument/reference doc then leads results). Keep ref-intent
  to explicit object words: ebook, book, instrument, questionnaire, guideline, manual, tool.
- Query-expansion / ranking-weight dictionaries with domain words (workload, burnout, icu)
  are only OK if applied ONLY when a query term matches a key — otherwise they're silent bias.
  Mark them OPTIONAL domain-tuning; a general instance can empty them.

## Pattern 2 — Index instruments, then make queries instrument-aware
A query "NSS among nurses in Malaysia" should return studies that USED the Nursing Stress Scale,
not generic stress studies. Text-substring matching misfires ("nurses"⊂"nursess…", ENSS vs NSS
confusion). The fix:
1. **Scan each full-text PDF once**; populate a per-study `measures` / `instrument` field with
   the scales actually used. Use a heuristic instrument dictionary (canonical name → phrase
   variants, e.g. `Nursing Stress Scale (NSS)`: ["nursing stress scale", r"\bnss\b"]).
   See `references/instrument-indexing.md` for the exact approach and the canonical list.
2. **Detect instruments named in the QUERY** (`INSTRUMENT_DETECT`). Boost/filter results whose
   `measures` contain a queried instrument so instrument users rank first.
3. **judge_results is a FIRST-PASS heuristic only.** The final relevance call is the LLM
   reading each item's `evidence` block (title, year, population, measures, abstract snippet,
   full-text flag). Never let the regex be the final authority.

## Pattern 3 — Verify every record against an external source before merge
Every added/merged catalog entry must be confirmed via Crossref / Semantic Scholar / OpenAlex
(or web search). Persist `verified_at` so re-verification is skipped within ~30 days.
Duplicate detection needs TWO paths: exact DOI match, AND (for `local:` pseudo-IDs that hash
the file PATH, not content) Jaccard title-similarity ≥ 0.6 so the same paper under a different
filename is caught.

## Pattern 4 — Staleness re-scan on ingestion
Re-running ingestion on a folder should detect changed source files (mtime/size) and refresh
the entry, not silently skip as "duplicate by DOI".

## When reviewing a RAG skill for "is it actually general?"
Ask: if I query "diabetes" or "wound care", does it (a) return those results without a
nurse/Malaysia filter, and (b) NOT pollute with stress-expansion terms? If either fails, the
skill is domain-leaking and needs the Pattern-1 fixes.



<!-- ===== Merged from: research/rag-catalog-audit ===== -->

# RAG Catalog Audit & Maintenance

## When to use
- User asks to verify/audit catalog records, check for errors, or "randomly check records".
- After any bulk ingest, enrichment pass, or metadata fix — to catch drift before it compounds.
- Recurring maintenance: the user wants ongoing random-record verification of the index.

## Core discipline (load-bearing — these prevent the exact errors found this session)
1. **Random-sample, then verify against the ACTUAL full text** — not against keywords or titles alone. Sample ~10 full-text records per pass; for each, confirm the indexed title, year, country, and `measures` are supported by the real body text.
2. **Never bulk-edit on keyword matches.** A keyword signal (e.g. "Jordan" in a title) is NOT proof of study country. Verify each flagged record individually via the authoritative source BEFORE changing it. This is the single most common catalog-corruption path (it produced 24 false-positive country flags in one pass; only 4 were real).
3. **Authoritative order for verifying a field:**
   - *Metadata (title/authors/year/DOI):* Crossref API (`https://api.crossref.org/works/<DOI>`). Trust Crossref over OpenAlex / Semantic Scholar / PubMed / full-text snippets. Never judge a DOI wrong from fallback text.
   - *Country:* (a) Crossref `author[].affiliation` (most reliable); (b) full-text sentence "conducted in X" / "hospitals in X"; (c) NEVER infer from a country name merely appearing in title/abstract (comparison studies, cited locations) or from a publisher download/access IP (e.g. "Downloaded by NIH Malaysia" ≠ Malaysian study).
   - *Instrument / `measures`:* only record an instrument if it appears in the paper's methods/full text. If the indexed `measures` is a guess (e.g. "stress scale (unspecified)"), correct it from the body (e.g. the Saudi study actually used PSS-10 + ENSS).
4. **Enrich only when it adds value — do NOT pad `keywords_llm` for its own sake.** Add keywords only when the full text/abstract reveals genuinely missing, high-value terms (a real instrument name, the true country). Off-topic or thin records (e.g. a pediatric paper sitting in a nursing-stress catalog) should be LEFT AS-IS, not padded. User explicitly: "don't simply add more keywords just for the sake of doing it."
5. **Ad-hoc verification of any script you write.** Before declaring a fix done, run a read-only check that the catalog JSON still loads, the intended edits persisted, and the script executes without error (see `scripts/audit_random_records.py` — it self-verifies catalog validity).

## Workflow
1. Run `scripts/audit_random_records.py` (read-only) to get a flagged list.
2. For each flag, open the full text and decide: true issue vs false positive.
   - FALSE POSITIVES to ignore: review / meta-analysis / multi-country studies (many country names in text); download-watermark IPs; translated reprints (e.g. German reprint of a US classic → country stays None); `local:` tool docs (PRISMA checklist, consent forms) — exclude these from sampling.
3. Fix only genuine issues: correct `country` (with `country_note` + `country_corrected: true`), correct `measures`, or add a few high-value `keywords_llm`.
4. Save catalog; push to the GitHub backup (if configured) with a descriptive commit.

## Pitfalls (from real session failures)
- **Country keyword = false friend.** "Leadership style & turnover — Jordan" was actually Universiti Tenaga Nasional (Malaysia); "Despotic leadership — Pakistan" was Universiti Utara Malaysia. Both were over-flagged by a title scanner and confirmed MY via Crossref affiliation. See `references/country-verification.md`.
- **Download IP ≠ study country.** A Wiley "Downloaded by National Institutes of Health Malaysia" watermark is NOT evidence the study is Malaysian.
- **`measures` guesses rot.** An earlier enrichment pass left `"stress scale (unspecified)"` on a Saudi study that actually used PSS-10 + ENSS. Always read the methods.
- **Don't re-guess what you just corrected.** Once `measures` is verified from text, leave it.
- **Title-check false negatives:** non-breaking hyphens / em-dashes (e.g. "App‑Based") make naive substring checks fail even when the title IS present. Normalize whitespace/dashes before comparing.

## References
- `references/country-verification.md` — detailed country-disambiguation examples and the authoritative-check order.
- `scripts/audit_random_records.py` — read-only random-sample auditor (reports flags, mutates nothing; self-checks catalog validity).

## Relationship to other skills
Companion to `general-purpose-rag` (ingestion/search) and `rag-verification-protocol` (DOI + content verification). This skill covers *ongoing catalog quality maintenance* after ingest. NOTE: those two are user-owned — if you need to extend them, recommend `hermes curator adopt <name>` rather than patching directly.



<!-- ===== Merged from: research/rag-catalog-discipline ===== -->

# RAG Catalog Discipline (user-mandated)

Rules learned and corrected repeatedly during the Malaysian-nursing catalog build
(2026-08-03). NON-NEGOTIABLE for this user's catalogs. Companion skills
`general-purpose-rag` (search engine) and `pdf-processing` (PDF extractor) are
user-owned here — run `hermes curator adopt general-purpose-rag pdf-processing` to
merge the broader class-level rules. This skill carries the workflow discipline
independently so it is never lost.

## The 8 hard rules
1. **FIND ALL, never silently drop.** On "list all studies on X", return EVERY matching
   entry — full text OR abstract-only OR metadata-only. Rank them, don't exclude. A record
   with abstract+metadata but no PDF is a VALID result (flag `[ABS]`/`[META]`).
2. **FILTER BEFORE ADDING NEW, never drop existing.** When EXPANDING from a fresh search,
   screen candidates to on-topic + recent (e.g. 2018+) BEFORE committing. User rejected a
   220-study unfiltered bulk-add; filter first, then add survivors. Applies to NEW records
   only — never prune what's already in the catalog.
3. **LINE-BY-LINE AUDIT BEFORE EXPANDING / on request.** Walk every entry: (a) does the
   referenced file exist? (b) if yes, open it and confirm indexed title/authors/year/
   abstract align with actual content; (c) on discrepancy fix ASAP; if unfixable mark
   `full_text_status: pending`; if clearly wrong AND unresolvable, mark `wrong` or remove
   ONLY if no verified metadata AND provably non-existent.
4. **METADATA COMPLETENESS IS PRIORITY #1.** A study missing title/year/abstract/
   keywords/tags is a defect. A study MAY be added with metadata+abstract even without full
   text, but it MUST be verified (DOI resolved or user-confirmed) and flagged `pending` for
   full text — never left as a silently broken path.
5. **PRESERVE THESIS / USER-VERIFIED RECORDS.** User's thesis bibliography, references.txt,
   and manually-uploaded PDFs are manually verified — KEEP them. Web/org/gov/tool entries
   (HSE, ILO, OECD, WHO, MOH, Raosoft, hospital sites) are legitimate non-study references
   with no abstract by design — reclassify as `web_reference`, don't flag as broken.
6. **SCOPE AUDITS TO `study` DOCS.** When completing/verifying metadata, iterate
   `doc_type=='study'` only. Skip ebook/website/policy/instrument/org_doc/gov_doc/tool.
7. **DON'T DELETE ON A HUNCH.** Only remove if confirmed non-existent AND obviously wrong
   AND no verified metadata. Otherwise keep + flag `pending`/`needs_review`.
8. **RANK FROM THE FIRST REPLY.** On "list all studies on X", output a ranked list
   immediately (score = 0.6*relevance + 0.4*significance; see general-purpose-rag Result
   Ranking), top ~25, with full-text status.

## Standard verification pass (run when asked to "verify / audit the index")
1. Load `UNIVERSAL_CATALOG.json`.
2. For each `doc_type=='study'`: identifier (doi/url) present? metadata complete (title +
   year + abstract>50 OR authors OR keywords OR tags)? `files.*` path exists if claimed?
3. Count + list: incomplete-metadata studies, full-text-claimed-but-missing, duplicate
   DOIs, broken paths.
4. Recover missing metadata: Crossref/OpenAlex (DOI known) → PDF extracted text (see
   `pdf-processing`) → user citation note → filename.
5. Reclassify mis-typed non-studies (`study` entries that are checklists/guides/theory/
   courseware) to `instrument`/`other` — KEEP in catalog, correct the type.
6. Merge exact-DOI duplicates (keep user-verified/thesis copy, fold in its full text).
7. Mark genuinely-unfetchable items `full_text_status: pending` — never leave a broken path.
8. Report: total docs, studies, complete-metadata %, full-text count, pending, broken, dups.

## The 8 hard rules (summary for routing)
Audit/build RAG literature catalogs: find all studies, filter new before adding, verify
line-by-line, complete metadata, keep thesis-verified records, scope to study docs.

## CORRECTION (2026-08-03): deliver the ranked list on the FIRST reply
When the user asks "how many Malaysian studies on X, make a list" they expect the
**full ranked list immediately** — not a staged "I'll search, then next turn I'll list".
A prior session returned the count + a few examples and stopped; the user had to ask
again. Fix: run the search/rank in ONE turn and output the complete table (top ~25 with
score + full-text status) in that same reply. Background batch jobs (OA fetch, paper-fetch)
may still run async, but the *answer to the question* must not wait for them.

## CORRECTION (2026-08-03): AUDIT BEFORE EXPAND (mandatory sequence)
When the user says "verify the index line by line, then expand", the order is NOT
optional: (1) walk EVERY study entry — does the referenced file exist? if yes, open it
and confirm indexed title/authors/year/abstract align with actual content; (2) on
discrepancy fix ASAP; if unfixable mark `full_text_status: pending`; if clearly wrong and
unresolvable mark `wrong` or remove only if no verified metadata AND provably
non-existent; (3) ONLY after the audit is clean, proceed to fresh search/expansion. Do not
interleave expansion with the audit. Use `scripts/audit_studies.py` (read-only checker)
as the first step of any "verify the index" request.

## Reusable audit script
`scripts/audit_studies.py` — counts studies with no identifier, incomplete metadata,
broken full-text paths, pending-but-file-present, and duplicate DOIs. Report-only by
default; `--fix-meta` is additive-only (fills a missing abstract from extracted_text,
never overwrites existing data). Mirrors rules 3 & 8.



<!-- ===== Merged from: research/rag-workflow-discipline ===== -->

# RAG Workflow Discipline (user-specific, class-level)

These are workflow corrections the user issued during real catalog work (2026-08-03).
They are NOT in the base general-purpose-rag skill and must be followed for this user.
Several also belong in `general-purpose-rag`/master `rag` SKILL.md — see
`references/general-purpose-rag-patch.md` for ready-to-apply text (those skills are
user-owned; run `hermes curator adopt general-purpose-rag` first, then apply).

## 1. Thesis-first / citation-driven scope
When the user has a thesis or bibliography, **read it FIRST** and harvest its reference
list (DOIs). Then only fetch / enrich the *cited* studies. Do NOT blindly open the whole
catalog (e.g. 300+ PDFs). The cited subset is the correct unit of work — it avoids wasted
retrieval and keeps enrichment on-topic.
- Practical: parse the FYP/reference section for DOIs, cross-check against the catalog,
  and only run acquisition/enrichment on the gap (cited-but-no-full-text).

## 2. Extraction ≠ Enrichment (never claim "complete")
Downloading + text-extracting a PDF only puts bytes on disk. The index is NOT enriched
until the LLM has READ the text and written `keywords_llm` / `brief_abstract` /
`measures`. Before reporting "all full texts extracted/complete", check the
`keywords_llm` population — empty `keywords_llm` means unenriched.
- Real failure this session: 314 files were "extracted" but wrongly called complete;
  55 thesis-cited studies still lacked real text and 52 lacked `keywords_llm`. The fix was
  a per-doc LLM read in batches, writing content-derived keywords.

## 3. Prefer reviews for global / gap-fill evidence
When gathering *additional* or *global* evidence — especially to fill catalog gaps beyond
the user's own thesis — lead with REVIEWS (systematic review / meta-analysis / umbrella
review) over primary studies. The user explicitly stated this after praising web-found
reviews. Surface reviews first in global-evidence answers.

## 4. Use the web-acquisition skills, not ad-hoc web_search
For gap-fill discovery/acquisition, load and use `openalex-skill` (OpenAlex = primary
discovery), `semanticscholar-skill` (S2 paperId for paywalled), `arxiv` (preprints),
`paper-fetch`. Do NOT fall back to bare `web_search`. The skills encode the verified legal
OA chain (fulltext-retrieval-priority.md).

## 5. Crossref is the citation/metadata authority (reminder)
Resolve every DOI via Crossref (`https://api.crossref.org/works/<DOI>`) and trust its
title/authors/year over OpenAlex/S2/PubMed/full-text snippets. Never judge a DOI wrong
from retrieved fallback text (S2/PubMed can return a wrong record for old/non-biomedical
DOIs). For foundational/seminal works, an abstract or secondary snippet is sufficient —
store `full_text_status: meta_only`/`abstract_only`, don't chase the full body.

## Shared References
- `references/general-purpose-rag-patch.md` — exact patch text to fold rules 1-4 into
  `general-purpose-rag` SKILL.md (apply after `hermes curator adopt general-purpose-rag`).



<!-- ===== Originating umbrella: research/rag-catalog-auditing ===== -->

# RAG Catalog Auditing

A class-level skill for **verifying the integrity of an existing research-paper RAG / citation
catalog** (a JSON index of papers + associated TEXT_/PDF_ files) before you trust it or make
bulk edits. Born from a real session where an auto-importer had silently corrupted a 700+ entry
catalog by stamping DOIs from *citations inside* files onto the files themselves.

This skill complements (does not replace) the search/retrieval skill `general-purpose-rag`.
If that skill is present and you are its curator, fold this content into it.

## When to use
- User says "audit the index", "is this catalog dependable", "check every entry against the file",
  "verify before indexing", or suspects mislabeled citations / wrong metadata.
- You are about to bulk-edit a catalog and must first establish a reversible baseline.
- After any auto-import, before treating entries as trusted literature.

## The #1 integrity rule: DOI-of-paper ≠ DOI-in-reference
A catalog entry's `doi` field may be a DOI **cited inside** the file (an assignment or
instrument PDF that *mentions* a paper), NOT the file's own DOI. The auto-importer that built
the audited catalog did exactly this.
- **Open the file's title page and confirm its OWN DOI matches the index `doi`.**
- Real published papers print their own DOI on the first page. Verify `index_doi[:16] in first_page_text`.
- If the file reads like a student work ("final year project", "submitted in fulfilment",
  "partial fulfilment", "this assignment/thesis") or an instrument ("questionnaire",
  "validity and reliability", "user manual", "kuesioner", "instrument was developed"), it is
  almost certainly NOT the paper its DOI claims — **quarantine it, do NOT trust its DOI.**

## Systematic instrument / population over-assignment
Auto-indexers over-apply instrument tags. In the audited catalog, ERI (Effort-Reward Imbalance)
was auto-assigned to ~544 entries but only ~48 actually used it; MBI/NWSQ/STAI/JDI similarly
over-tagged. Population fields get inflated too (a general racism scoping review mislabeled
"ICU nurses").
- **Re-derive instruments from "used as a tool" phrases in the full text**, never from bare
  substrings in the references. e.g. require "maslach burnout inventory" / "spielberger" (STAI),
  not just "mbi"/"jdi" which appear in citations.
- Same for population: confirm the studied group is actually in the methods/results, not inferred
  from a cited paper.

## User workflow preference (this user — NON-NEGOTIABLE)
1. **Reversible & read-only first.** Backup the catalog JSON (copy to `backups/`) BEFORE any write.
   Prefer additive edits (add `extracted_text`, add `flags`) over destructive ones.
2. **File-by-file, not blind bulk.** Open the actual file; check **title / authors / year /
   keywords / DOI / abstract** against the index entry. Present a per-entry table; let the user
   disposition suspect entries (Keep / Reclassify-as-working-file / Drop).
3. **Flag, don't overwrite.** Mark suspect/missing via a `flags` array; never silently replace
   metadata. The user explicitly worried about the index being destroyed — earn trust by showing
   the table before acting.
4. **Separate working files from literature** with a `doc_class` field
   (literature / working_study / working_file). Exclude working_file and ebooks/assignments from
   any "published study" audit.

## Workflow
1. Load catalog; make a timestamped backup.
2. For each entry with a real `10.` DOI (skip `local:` and `bad_doi` flags):
   - Get its text: prefer existing `TEXT_` file; else extract the PDF (see below).
   - Classify: `PAPER(own DOI)` / `NO_TEXT` / `INSTRUMENT/TOOL?` / `ASSIGNMENT/THESIS` / `PAPER?`.
   - Re-derive instruments via tool phrases; compare to index `instrument`.
3. Write a **read-only JSON report**; present suspect + uncertain entries to the user as a table.
4. Only after the user dispositions them, apply edits (and only additive/flag-based where possible).

## PDF text extraction in constrained environments
`fitz`/PyMuPDF may not import inside the `execute_code` Python sandbox. Use the `pdftotext`
binary via the **terminal**: `/mingw64/bin/pdftotext -layout file.pdf -` (try `/usr/bin/pdftotext`
too). The 58 PDF-only entries in the audited catalog had `full_text_pdf` paths that were never
copied into the RAG folder; their true originals sat on an external drive under `original_source`.
Read those, never mutate.

## Support files
- `scripts/audit_integrity.py` — read-only per-entry classifier + instrument re-derivation.
  Writes `FILE_BY_FILE_VERIFICATION.json`, never mutates the catalog.
- `references/catalog_integrity_audit.md` — full corruption taxonomy and the verified-safe vs
  suspect patterns observed in the audit that motivated this skill.
- `references/instrument_usage_verification.md` — the ENSS case study (Vietnam/Greece/Ethiopia
  were wrongly excluded by a keyword-only search) + ready-to-run deep-scan recipe. Read before any
  "which studies used instrument X" request.
- `scripts/find_instrument_usage.py` — deep full-text scan for an instrument; reports
  ADMINISTERED (used as tool) vs CITED-ONLY, so you never exclude a real user.

## Relevance, instrument-usage & external-review verification (added 2026-08)

These extend the audit beyond metadata to *whether the record actually belongs and is
findable*. All emerged from a session where a keyword/title-only search silently dropped
genuine studies and an external review described the wrong file.

### 1. Instrument-usage search MUST deep-scan full text — keyword/title-only EXCLUDES real studies
When the user asks "which studies used ENSS / NSS / PSS to measure stress", a search over
`keywords_llm` + `title` + `measures` is **insufficient and actively harmful**: it drops
studies whose instrument appears only in the methods/results body, and over-keeps studies
that merely *cite* the instrument in the literature review.
- **Deep-scan the full `extracted_text`** of every catalog record for the instrument name.
- **Distinguish ADMINISTERED vs CITED.** A study "used" the instrument only if the text shows
  it was administered/collected/measured via it:
  `regex: (administered|used|collected|measured|assessed|employ|utili[sz]ed|completed).{0,40}
   (expanded nursing stress scale|ENSS)` OR
   `(expanded nursing stress scale|ENSS).{0,40}(was (used|administered)|to measure|questionnaire|instrument)`.
  A bare "ENSS" inside a references section or lit-review sentence = CITED-ONLY → exclude from
  "studies that used it" (but keep the record).
- Worked failure: ENSS search returned 7 (keyword hits) then 37 (deep scan); only 8 were genuine
  users. Excluded-but-real: Vu 2024 (Vietnam), Sarafis 2016 (Greece), Werke 2023 (Ethiopia) — all
  had ENSS only in the body, not keywords. See `references/instrument_usage_verification.md`.

### 2. External reviews of the catalog LIE — verify the real file before acting
If the user pastes a review/audit from another agent (Claude, ChatGPT, a colleague) claiming N
docs / specific functions / specific field counts: **do not trust its numbers.** Open the ACTUAL
`UNIVERSAL_CATALOG.json` and measure yourself.
- Failure this session: external review claimed "722 documents, functions add_documents_from_folder()/
  verify_doi_metadata(), quality_score field, domain: OUM_Research" — NONE of which exist in this
  catalog (real: 526 docs, no such functions/fields). The reviewer had inspected a different or
  stale file. Actions based on those counts would have corrupted the real catalog.
- What WAS valid in that review (because it matched the real code): `official_keywords` ~85% empty
  (search code reads it) and `verified_at` missing (causes needless Crossref re-verification).
  Verify each claim against the real file; keep the true parts, discard the rest.

### 3. PRISMA-template swaps evade the title-overlap detector
A common corruption: the indexed paper's file actually contains a **PRISMA/scoping-review
reporting TEMPLATE** ("Tips for reporting this item", "Eligibility criteria with a rationale",
"Preferred Reporting Items…"), not the article. The title-overlap check misses it because the
template body does not contain the paper's title.
- Detection signature: `any(s in text.lower() for s in ["tips for reporting this item",
  "preferred reporting items", "data charting form", "eligibility criteria with a rationale"])`
  AND `not title_in_text` AND `len(text) < 8000`.
- Fix: re-fetch the real abstract via EPMC
  (`https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=DOI:<doi>&format=json`)
  and replace the template file. Do NOT keyword a template.

### 4. OUM / student learning-kit contamination
Bulk ingestion swapped OUM student assignment wrappers ("Open University Malaysia", "NBBS",
"NBNS", "learning kit", "matriculation no") and thesis-admin forms in place of the indexed
research article. These are real files but wrong content.
- Signature: `any(s in text.lower() for s in ["open university malaysia","oumk","nbbs","nbns",
  "learning kit","matriculation no","matrix no"])`.
- Tag as `doc_type: coursework` + `relevance: off_topic`; re-fetch the real article if a DOI exists.
  Do NOT keyword a coursework wrapper as if it were the research paper.

### 5. Cross-check the user's own thesis / reference list
The user's thesis (or any cited reference list in the catalog) is the authoritative seed for
"which studies should be here". Extract its DOIs and ENSS/keyword citations, then confirm each is
present AND correctly classified. This is how the Vietnam/Greece/Ethiopia gaps were caught — the
user said "see my thesis where I cite ENSS".

### 6. Keyword-enrichment discipline (user rule)
When backfilling `keywords_llm`: **read each file → if mismatch, fix the file FIRST, then keyword
the real content → if off-topic, tag `relevance: off_topic` → never keyword a corrupted file.**
Instruments/checklists/thesis-support docs DO need keywords (user searches for instruments later)
— add concise title-based + instrument-type keywords, not a frequency dump. Per-study, topic-agnostic.
