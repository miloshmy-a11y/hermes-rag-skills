# Catalog Integrity Audit — Corruption Taxonomy & Patterns

Observed while auditing a 717-entry `UNIVERSAL_CATALOG.json` (universal_rag, nursing
work-related-stress collection) during a single session. These are the real failure modes
a future audit must look for, plus the verified-safe vs suspect split that emerged.

## Corruption classes found

### 1. DOI-of-paper ≠ DOI-in-reference (MOST DAMAGING)
The auto-importer stamped DOIs from *citations inside* files onto the files themselves.
- An assignment/thesis draft or an instrument PDF (e.g. `ENSS asli_appendix thesis.pdf`,
  `JS-Q.pdf`, `Hoonakker-2011-NASA-TLX-6.pdf`, `Kuesioner ENSS Indonesia.pdf`) got a
  referenced paper's DOI as its own `doi`.
- Tell: the file's title page does NOT contain its own DOI; instead the DOI appears only in
  the reference list, or the file is clearly student-work / a scale.
- User caught this explicitly: "what is actual DOI of the paper and what is DOI for reference
  used within the text." This is the canonical integrity trap for imported RAG catalogs.

### 2. Instrument over-assignment (systematic)
- ERI (Effort-Reward Imbalance) auto-assigned to **538** entries; only ~30 actually use it.
- MBI/NWSQ/STAI/JDI likewise over-tagged (bare substring match in references section).
- Fix: require "used as a tool" phrases ("maslach burnout inventory", "spielberger",
  "job descriptive index"), not bare "mbi"/"jdi"/"eri" which appear in citations.
- Garbage tokens (single letters: `i`, `a`, `e`, `s`) also present in `instrument` field —
  202 removed; keep only canonical short names (ENSS/NSS/PSS/ERI/MBI/NASA-TLX/NWSQ/STAI/JCQ/JS-Q/JDI).

### 3. Population over-assignment
- A general "Racism in healthcare: a scoping review" was tagged population "ICU nurses".
- A nurses job-satisfaction *review* (Al Maqbali 2024) was tagged "ICU Nurses; Doctors;
  Public Health Workers; Indonesia; China; Australia; Italy" — inflated from cited papers.
- Fix: confirm the studied group is in methods/results, not inferred from references.

### 4. Malformed / placeholder DOIs
- `10.1155/2023`, `10.1186/s12889-025-`, `10.1093/humupd`, `10.1016/b978-` — truncated
  fragments, not resolvable. Flag `bad_doi`; do NOT treat as verified.

### 5. Working-file / literature contamination
- `OUM_Research` domain held 584 entries that were drafts, proposals, CASP checklists,
  TLX questionnaires, supervisor forms, presentation scripts — NOT published literature.
- Add `doc_class` (literature / working_study / working_file) and exclude working_file +
  ebooks/assignments from any "published study" audit.

## Verified-safe vs suspect (the 187 real-DOI studies)
- **90** `PAPER(own DOI)` — genuine papers, own DOI on title page. Safe.
- **58** `NO_TEXT` — `full_text_pdf` never copied into RAG; originals on external `D:\`
  under `original_source`. Read-only verify from `D:\`; do not mutate.
- **31** `PAPER?` — text exists but DOI not on first page (likely fine; DOI printed deeper).
- **6** `INSTRUMENT/TOOL?` + **2** `ASSIGNMENT/THESIS` — confirmed non-papers. Quarantine.
=> ~39 entries needed human disposition; only the 8 clear non-papers were unambiguous.

## Reversible-edit discipline that earned user trust
1. Backup `UNIVERSAL_CATALOG.json` to `backups/` BEFORE any write.
2. Prefer additive edits (`extracted_text`, `flags`) over destructive.
3. Flag (add to `flags` array) rather than overwrite metadata.
4. Present per-entry table; let user disposition (Keep / Reclassify / Drop).
5. Never silently relabel or delete; user was explicitly worried about index destruction.

## Environment note (tooling, not a durable rule)
`fitz`/PyMuPDF did not import inside the `execute_code` sandbox; `pdftotext` binary
(`/mingw64/bin/pdftotext`) worked from the terminal. Use terminal for PDF extraction.
