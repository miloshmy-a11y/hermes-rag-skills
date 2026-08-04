---
name: rag-catalog-discipline
description: RAG catalog audit and build rules for literature indexes.
---

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
