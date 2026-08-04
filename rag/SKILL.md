---
name: rag
description: "Master entry point for ALL RAG / literature-catalog work: searching the user's paper catalog, indexing/adding new PDFs, verifying citations (DOI + Crossref/Semantic Scholar/OpenAlex), auditing or repairing a corrupted catalog, fetching open-access full text, and enrichment. Routes to the correct sub-skill (general-purpose-rag, openalex-skill, paper-fetch, verified-academic-research, rag-catalog-audit-rebuild). Use for ANY request about the research paper collection, literature review, citation checks, or PDF ingestion. Audit/dedup/rebuild sub-skills now live under research/ (e.g. research/rag-catalog-auditing, research/rag-catalog-audit-rebuild, research/rag-corpus-integrity)."
version: 1.1.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [RAG, literature-review, catalog, citation, research, orchestration]
    category: research
    related_skills: [general-purpose-rag, openalex-skill, semanticscholar-skill, paper-fetch, verified-academic-research, rag-catalog-audit-rebuild, rag-catalog-discipline, pdf-processing, research-fulltext-retrieval]
---

# RAG Master Skill — the single entry point

## STABILITY / DO-NOT-DRIFT (load-bearing rules — any session editing the catalog or sub-skills MUST follow)

Hardened 2026-08-03 after real errors. Do NOT bypass even if asked to "just add" a record:

1. **Crossref is the authoritative citation/metadata source.** Verify every DOI via
   `https://api.crossref.org/works/<DOI>`; trust Crossref over OpenAlex/S2/PubMed/full-text
   snippets. Never judge a DOI wrong from fallback text.
2. **Verify-before-merge** — no record added without Crossref (or 2-source) verification.
3. **Abstract/snippet sufficient for foundational & frequently-cited works** (Karasek 1979,
   Selye 1936, Siegrist ERI, NSS, French 2000 ENSS): `meta_only`/`abstract_only` is enough.
4. **Never guess `measures`/instrument fields** — only from the paper's actual methods/full text.
5. **NSS ≠ ENSS** — distinct instruments, tag separately.
6. **Catalog is general / topic-agnostic** — never hardcode population/geo in logic.

This skill is a **router**. It does not re-implement search/ingestion/verification —
it tells the agent which specialized sub-skill to load for the user's actual request,
and how to call it. Load the sub-skill named in the routing table below with
`skill_view(name=...)` before doing the work.

> **Recurring footguns (paths, interpreters, script entry points, result schema):**
> see the dedicated skill **`hermes-rag-pitfalls`** — every pattern below is
> cross-referenced there with copy-paste commands. Read it before any RAG terminal work.

## The catalog (one source of truth)
- **Location:** `<HERMES_CACHE>/web/universal_rag/UNIVERSAL_CATALOG.json`
  (local: `C:\Users\Milos\AppData\Local\hermes\cache\web\universal_rag\UNIVERSAL_CATALOG.json`)
- A JSON `{"documents": [...]}` list. Each doc has `doi`, `title`, `year`, `authors`,
  `journal`, `abstract`, `official_keywords`, `inferred_tags`, `verification_status`,
  `verified_at`, `files` (pdf + extracted text), `doc_type`, `paper_category`, etc.
- **This catalog is GENERAL / topic-agnostic** — it is NOT limited to nursing or stress.
  Population/geography are query-derived, never hardcoded. A query about "diabetes" or
  "wound care" is searched as-is; "nurses in Malaysia" auto-filters to nurses+Malaysia.
- Note: the collection *currently skews* toward Malaysian-nurse / occupational-health
  literature because that is the user's thesis domain — but the engine logic is universal.

## Routing table — load the matching sub-skill
| User wants to… | Load sub-skill | Primary entry point |
|---|---|---|
| **Search the catalog** (find studies, ebooks, instruments, theses) | `general-purpose-rag` | `precise_search.staged_search(docs, query=...)` or `universal_rag.UniversalRAG().search(...)` |
| **Add / index new PDFs from a folder** | `general-purpose-rag` | `UniversalRAG().add_documents_from_folder(folder, domain=...)` |
| **Discover new papers (not yet in catalog)** | `openalex-skill` (primary), `semanticscholar-skill`, `arxiv` | `oa_search`, `oa_by_doi`, `oa_bulk_dois` |
| **Download / fetch a paper PDF by DOI or title** | `paper-fetch` | via DOI / arXiv id / title |
| **Get open-access full text (when paywalled)** | `research-fulltext-retrieval` | web_extract HTML (primary), Unpaywall/PMC/CORE/DOAJ for PDF |
| **Verify a citation / DOI is real & matches content** | `verified-academic-research` + `rag-verification-protocol` | Crossref/S2 + content match |
| **Audit a catalog for corruption / misattribution** | `rag-catalog-audit-rebuild` (or `rag-catalog-auditing`) | audit script |
| **Repair / rebuild a corrupted catalog from source PDFs** | `rag-catalog-audit-rebuild` | rebuild script |
| **Enforce the user's catalog-discipline rules** (e.g. verify-before-merge, no bulk-dump) | `rag-catalog-discipline` | rules reference |
| **Extract text from a PDF** (standalone) | `pdf-processing` | `pdf_extract.py` |
| **Build a searchable index from scratch** | `rag-catalog-audit-rebuild` | rebuild script |

## Search — quick commands
```python
import json, sys
sys.path.insert(0, r"<SKILLS>/research/general-purpose-rag/scripts")
from precise_search import staged_search
docs = json.load(open(r"<CATALOG_PATH>", encoding="utf-8"))["documents"]
out = staged_search(docs, query="ENSS among nurses in Malaysia since 2020")
# REAL result-schema (each item in out["core_results"] has these keys — there is
# NO "match_type" or "source" key; do not print them):
#   doc, score, matched_terms, found_via ('index'|'fulltext'|...),
#   judgment ('ON_TOPIC'|'PERIPHERAL'|'DROPPED'), evidence
for r in out["core_results"][:10]:
    print(r["doc"]["title"], "|", r.get("found_via"), "|", r.get("judgment"), "|", r["doc"].get("year"))
```
- Population/geo are **optional and query-derived**. Just type them in the query
  ("nurses", "Malaysia"); do not pass hardcoded gates.
- Per-result fields that actually exist: `found_via` (how it matched, e.g. `index`)
  and `judgment` (`ON_TOPIC` / `PERIPHERAL` / `DROPPED`). There is **no** `match_type`
  or `source` key on results. Web-fallback candidates live in `out['web_candidates']`
  and carry `needs_indexing=True` (never auto-indexed — user confirms first).

## Ingestion — quick command
```python
sys.path.insert(0, r"<SKILLS>/research/general-purpose-rag")
from universal_rag import UniversalRAG
rag = UniversalRAG()
rag.add_documents_from_folder(r"<FOLDER_OF_PDFS>", domain="general", auto_verify=True)
```
What ingestion does (and what it persists):
- Copies PDFs (never touches originals), extracts full text, extracts DOI, verifies via Crossref.
- Persists `verified_at` (so re-verification is skipped within 30 days).
- Populates `official_keywords` (from the paper's explicit "Keywords:" line) and `scope_notes`.
- Records `file_mtime` / `file_size` for **staleness re-scan**: re-running on the same
  folder updates entries whose source file changed, instead of silently skipping.
- **Duplicate detection:** exact DOI match + (for papers without a real DOI) Jaccard
  title-similarity ≥ 0.6 — so the same paper under a different filename is caught.

## Verification discipline (non-negotiable for this user)
1. **Verify-before-merge:** every added/merged record must be confirmed via Crossref or
   web search. Never blindly copy an old record.
2. **Crossref is the authoritative citation/metadata source:** for any DOI→citation or
   "does this DOI resolve to the paper it claims" check, resolve via Crossref
   (`https://api.crossref.org/works/<DOI>`) and trust Crossref over OpenAlex/S2/PubMed/full-text
   snippets. OpenAlex is the *discovery* engine (search, OA PDF links, cited_by_count,
   country_code:MY scope); Crossref is the *citation record*. Never conclude a DOI is wrong
   from retrieved full-text content.
3. **Two-factor:** DOI resolves (via Crossref) AND content (title/abstract) actually matches the claim.
4. **No bulk-dump:** filter before adding (on-topic + recent); rank, never silently drop.
5. **Format check:** short/Supplement pages flagged for abstract-vs-full-article review
   before citing as a comparable prior study.
6. **Full-text sufficiency:** a full PDF body is NOT required for every entry. For foundational /
   frequently-cited works (Karasek 1979, Selye 1936, Siegrist ERI, Gray-Toft & Anderson NSS,
   French 2000 ENSS) and any entry where only metadata + abstract is obtainable after a
   legitimate OA-tier attempt, store `full_text_status: meta_only`/`abstract_only` and move on —
   do not burn retrieval effort chasing full bodies of widely-cited classics.

## Topic-agnostic rule (CRITICAL)
The engine must NEVER hardcode a topic, population, or geography in executable logic.
All such filtering is derived from the user's query. The public GitHub version ships with
`DEFAULT_POPULATION = None` / `DEFAULT_GEO = None` (fully general). For a personal instance
biased to one population/geo, those two constants can be set locally.

## Legacy / archived skills
The following were early iteration skills predating the consolidated `general-purpose-rag`
engine and have been **removed** (their logic is covered by the routing table above):
`enss-rag-research` (now just `general-purpose-rag` search), `rag-literature-build`
(merged into `rag-catalog-audit-rebuild`), `rhetorag-research-indexing` (merged into
`rag-catalog-audit-rebuild`). If you find a reference to them, treat it as historical.
