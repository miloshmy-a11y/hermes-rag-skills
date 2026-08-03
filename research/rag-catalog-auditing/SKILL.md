---
name: rag-catalog-auditing
description: "Audit a RAG paper catalog for corruption before trusting it."
version: 1.0.0
author: Hermes Agent
license: MIT
---

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
