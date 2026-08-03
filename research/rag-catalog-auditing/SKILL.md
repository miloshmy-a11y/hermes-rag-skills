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
