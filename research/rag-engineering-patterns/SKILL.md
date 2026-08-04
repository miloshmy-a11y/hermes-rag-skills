---
name: rag-engineering-patterns
description: "Topic-agnostic RAG search and instrument-aware indexing."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [RAG, search, indexing, topic-agnostic, instrument, patterns]
    category: research
    related_skills: [general-purpose-rag, rag, rag-catalog-discipline, verified-academic-research]
---

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
