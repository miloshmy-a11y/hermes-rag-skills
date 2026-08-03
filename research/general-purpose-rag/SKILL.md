---
name: general-purpose-rag
description: "Topic-agnostic RAG search over the user's literature catalog. Smart query expansion, web fallback, APA output, auto-quality-control. Population/geography are QUERY-DERIVED (not hardcoded) — a query about 'diabetes' or 'wound care' is searched as-is; 'nurses in Malaysia' auto-filters to nurses+Malaysia. Catalog size is computed live from UNIVERSAL_CATALOG.json at query time — do NOT hardcode a count here. For a personal instance biased to one population/geo, set DEFAULT_POPULATION / DEFAULT_GEO in precise_search.py (the public skill ships with None = fully general)."
version: 4.6.0
author: Hermes Agent
license: MIT
parameters:
  - name: query
    type: string
    description: "Search query"
    required: true
  - name: max_results
    type: integer
    default: 20
  - name: domains
    type: array
    description: "Filter by catalog domain(s)"
  - name: tags
    type: array
    description: "Filter by specific tags"
  - name: fulltext_search
    type: boolean
    default: false
    description: "Read full text files during search (slower but higher recall)"
  - name: debug
    type: boolean
    default: false
    description: "Show search trace and exclusion reasons"
---

# General-Purpose RAG System v4.5.3

## Overview
Domain-tuned RAG system (currently nursing-stress / occupational-health) for indexing and searching the user's literature catalog. Features smart query expansion, automatic low-recall triggers, web fallback with content verification, defuddle HTML cleaning, and APA citation output. Ranking weights are domain-specific (see Result Ranking note).

## Metadata Authority vs Discovery Engine — two distinct roles

**RULE (user directive, 2026-08-03): metadata & citations are ALWAYS sourced from Crossref first.**
- For any DOI lookup, BibTeX/APA citation, author/journal/year/title correctness, or
  "does this DOI resolve to the paper it claims to be" check → **Crossref is the authoritative
  source.** Resolve the DOI via `https://api.crossref.org/works/<DOI>` (or DOI content
  negotiation for BibTeX) and trust Crossref's returned title/authors/year over any other source
  (OpenAlex, Semantic Scholar, PubMed, or a retrieved full-text snippet). Crossref registration
  agency data is the canonical citation record.
- **OpenAlex is the PRIMARY DISCOVERY engine** (NOT a metadata authority): use it for
  search/discovery, OA PDF URLs (`oa_url`), `cited_by_count`, `concepts` auto-tags, and
  `country_code:MY` geo-scoping (Semantic Scholar CANNOT do country scope). Pull citation counts
  and OA links from OpenAlex, but pull the *citation/bibliographic metadata* from Crossref.
- **Do NOT judge a DOI's correctness from retrieved full-text content.** Lesson (2026-08-03):
  the S2-page/PubMed fallback can return a WRONG record for old/non-biomedical DOIs; the DOI
  itself was correct. Always verify the DOI via Crossref, not by trusting fallback text.

OpenAlex (`skills/research/openalex-skill`, `oa.py`) is free, no key, no rate limit, CC0.
It returns `cited_by_count`, `open_access` (status + direct OA PDF URL), and `concepts`
(auto-tags) on every record, and supports `filter=authorships.institutions.country_code:MY`
for country-scoped search (Semantic Scholar CANNOT do this).
- `oa_search(q, filters="from_publication_date:2015-01-01,has_doi:true,type:article")` → works
- `oa_by_doi(doi)` → citation count + OA PDF URL + concepts
- `oa_bulk_dois([...])` → batch enrich up to 45 DOIs/request (fast, no throttle)
- Malaysia scope: `filters="authorships.institutions.country_code:MY,..."`
- Relevance filter: keep only titles/abstracts mentioning nurse/nursing/staff nurse/ward/ICU.

## Key Features
1. **Smart Query Expansion** - Dynamically expands queries with related terms; if <5 results, generates contextually appropriate expansion terms for any topic
2. **Low-Recall Trigger** - When local results are thin (<5), triggers deeper full-text search + additional dynamic expansion terms
3. **Web Fallback** - Searched when local coverage is insufficient; results clearly labeled "NOT IN LOCAL COLLECTION"
4. **DOI Verification** - All DOIs verified via Crossref API (30-day cache for verified entries)
5. **Content Verification** - Each result checked for population match (nurses) AND finding relevance (workload as significant factor, not just keyword)
6. **Defuddle Integration** - Clean HTML extraction from publisher sites (removes nav, ads, citations, boilerplate); automatically falls back to web_extract for Cloudflare-blocked sites
7. **Duplicate Detection** - DOI (case-insensitive), Jaccard title similarity (0.85 adaptive threshold), and checksums
8. **Automated Backups** - Timestamped backups, keeps last 5 versions
9. **Result Labeling** - Source (local/web), match type (literal/expansion), verification status

## Result Ranking (how to present findings to the user)
Rank results by a combined score so the most on-topic AND most significant studies surface first:
- **Relevance (weight 0.6):** sum of theme-term weights found in title+abstract+tags. Weights:
  
> **Domain tuning note:** The relevance weight dictionary below is tuned for the user's
nursing-stress / occupational-health thesis (stress, workload, burnout, quality of care,
patient safety, turnover). This skill is therefore *domain-tuned*, not literally general-purpose.
If searching a different domain, either adjust the weights to that domain's vocabulary or the
relevance term will effectively be zero with no warning. Weights live here, not in a hidden dict.

stress=3, workload=3, burnout=2.5, quality of care=2.5, patient safety=2, turnover=1.5,
  job_satisfaction=1.5, resilience=1.5, safety_culture=1.5, intention_to_leave=1.5,
  leadership=1, workplace_violence=1, compassion_fatigue=1.
- **Significance (weight 0.4):** log-scaled citation count → `min(5.0, log10(cites+1)*1.5)` (0.3 floor if uncited).
- **Final score = 0.6*relevance + 0.4*significance.** Show top ~25 with [score] rel= sig= and full text status (PDF/ABS/META).
- Always show ALL matching studies (don't silently drop), but rank so the user sees the closest + most-cited first.
- Metadata-only (no full text) entries are VALID results — never exclude them; just flag [META].

## Workflow
1. Local search with query + expanded terms (title/abstract/tags/keywords)
2. If <5 results: deeper full-text search + dynamic expansion terms (Claude decides appropriate terms per query)
3. If still <5: web fallback (clearly separated, not auto-indexed)
4. DOI verification via Crossref API
5. Content verification: confirm studied population matches query criteria
6. Metadata enhancement with Crossref data
7. For web-found studies: PDF download → text extraction → defuddle cleaning

## Precise Catalog Search (staged, progressive, relevance+recency ranked)

For scoped queries like "stress among Malaysian nurses since 2020", a naive filter
(`'nurs' in text AND ('stress' OR 'burnout' OR ...)`) returns 150-180 hits (book chapters,
healthcare-worker studies that mention nurses in passing, non-Malaysia papers). Use the
**staged** method in `scripts/precise_search.py`:

```python
from precise_search import staged_search
# Population/geo are OPTIONAL and QUERY-DERIVED — 'nurses' + 'Malaysia' in the
# query auto-filter; omit them for a general topic (e.g. query="diabetes policy").
out = staged_search(docs, query="stress among nurses in Malaysia since 2020",
                    min_results=3, targeted_cap=15, broad_threshold=25)
# out['core_results']      -> top targeted_cap studies (ranked)
# out['student_results']   -> nursing-student studies (less-relevant tier)
# out['reference_results'] -> books/ebooks/instruments (less-relevant tier; PRIMARY if query asks for them)
# out['ref_intent']        -> True if the query explicitly asked for an ebook/book/instrument
# out['broad'] / ['needs_narrowing'] -> True if match pool > broad_threshold
# out['web_candidates']    -> stage-4 web fallback (needs_indexing=True)
# out['total_core_available'] -> full pool size (report when broad)
```

**Staged expansion (follows old universal_rag.py philosophy):** — TOPIC-AGNOSTIC
1. **Targeted index search** — match on INDEX fields (title + brief_abstract + official_keywords
   + measures + paper_category). Population and geography are applied ONLY if the query names
   them (e.g. "nurses in Malaysia"); otherwise the whole catalog is searched. Topic = whatever
   the query says (stress, turnover, wound care, diabetes, ...).
2. **If < min_results (3)**: expand synonyms (e.g. `stress`→`occupational stress`,
   `work-related stress`, `burnout`→`compassion fatigue`), re-search index.
3. **If still < 3**: scan full-text files (slower, higher recall). Studies found this way
   get missing index **keywords backfilled** into their `tags` (non-destructive).
4. **If still 0**: web fallback — return candidates flagged `needs_indexing=True` so the
   user can decide to add them. Never auto-index web results.

**Presentation rules (per user spec) — DYNAMIC, not a hard cap:**
- The search judges its own breadth from the real match pool and reports it:
  - `narrow`   (pool ≤ 8): return ALL results; SAFE to open every full text and summarise.
  - `moderate` (9..25): return ALL results (or up to ~20); still openable.
  - `wide`     (> 25): return a PREVIEW of the top 15 only, set `open_fulltext=False`,
    and attach `suggested_actions` (narrow the query / filter by sub-population or year /
    open top-15 now / name specific DOIs). The agent MUST ask the user what to do next —
    it must NOT auto-open 45 full texts.
- There is NO fixed 15-cap on relevant results; when the pool is genuinely small, all
  studies are shown. The 15 figure is only a *preview* size for wide queries.
- **Do NOT discriminate by title alone.** Topic matching is stem-aware (`stress` matches
  `stressed`/`stressors`/`stressful`), and population/geography confirmed in the ABSTRACT
  counts fully (e.g. "Why so stressed?" has a casual title but a core Malaysian-nurse-stress
  abstract — it must surface, not be dropped). Ranking uses title + abstract + tags + keywords.
- **Students** (nursing students) are kept but split into a separate `student_results` tier,
  presented as less relevant.
- **`key_study: true`** flag in a record boosts it (+1.5) so user-flagged seminal studies
  (e.g. "Why so stressed?", DOI 10.1186/s12912-020-00511-0) rise near the top.

**Ranking score:** `pop(2 if nurse confirmed) + geo(2 if Malaysia confirmed) + title_bonus(0.3 each)
+ topic_w(min(Σweights,6)/2) + topic_title_bonus(1.0) + recency((year-2020)*0.1) + key_boost(1.5)`.

This method returns a focused, on-topic, relevance-ranked set — not "everything mentioning nurses".

## Legal Full-Text Retrieval Pipeline

Follow the consolidated chain in `references/fulltext-retrieval-priority.md` (SINGLE SOURCE OF TRUTH). Summary: OpenAlex `oa_url` → Unpaywall → Europe PMC → CORE → DOAJ → paper-fetch → **S2 paper-page HTML** (for paywalled papers that 403 on bot GET) → PubMed → web_search last resort. Sci-Hub is NOT used — direct tests confirm it is non-functional (anti-bot/CAPTCHA walls, 403s). The working pipeline is OpenAlex/Unpaywall/PMC/S2-page/PubMed only. Windows/MSYS path gotchas live in `pdf-processing/references/windows-environment-notes.md` (top-level in this repo) — or `software-development/pdf-processing/references/windows-environment-notes.md` in Hermes' category-organized local tree.

**Critical:** never present a login-wall/landing page as full text; verify real PDF or extracted-HTML, else mark `full_text_status: pending`. Metadata-only entries are valid results — flag `[META]`, never drop.

**Full-text sufficiency rule (user directive, 2026-08-03):** A complete PDF/body is NOT required
for every entry. For **foundational / seminal / frequently-cited** works (e.g. Karasek 1979
demand-control, Selye 1936 GAS, Siegrist ERI, Gray-Toft & Anderson NSS, French 2000 ENSS) that are
cited across hundreds of papers, **an abstract (or a snippet from a secondary source such as the
publisher landing page, PubMed abstract, or a citing paper's description) is sufficient.** Do NOT
spend retrieval effort chasing the full body of such widely-cited classics — store `full_text_status:
meta_only` (or `abstract_only`) and the citation verified via Crossref. The same applies to any
entry where only metadata + abstract is obtainable after a legitimate OA-tier attempt; mark it
`[META]`/`[ABS]` and move on. Only pursue full PDF/HTML body text for (a) the user's own thesis
citations that are primary studies being read for content, or (b) studies specifically queried for
their findings.

## Catalog Scope (INCLUSIVE — do not exclude)
The catalog legitimately holds more than peer-reviewed `study` PDFs. Include ALL of:
- `study` — journal articles, reviews, theses (incl. the user's own FYP)
- `instrument` — scales/questionnaires (ENSS, NSS, PSS, JCQ, ERI, MSQ, etc.)
- `ebook` — textbooks and monographs
- `org_doc` / `gov_doc` — WHO, OECD, ILO, HSE, NIOSH, MOH Malaysia, hospital sites
- `tool` — sample-size calculators, statistical software manuals
- `web` / non-DOI references from a thesis bibliography (dedup by `url`, store `url` in `files.full_text_html`)
**Search must not hard-filter to `doc_type=='study'` only** — support a `doc_type` filter param so theses,
ebooks and web docs are retrievable when the user asks. Dedup covers DOIs AND URLs.

---

## Defuddle Integration
When importing web-found studies:

1. **First attempt:** Use `npx defuddle parse <URL> --markdown` to extract clean article text
2. **If blocked (Cloudflare/Sci-Hub):** Fall back to `web_extract` HTML text extraction
3. **Always verify:** Extracted text is confirmed to contain real content (not redirect pages)

```bash
# Direct usage
python3 defuddle_extractor.py "https://opennursingjournal.com/article" "10.2174/xxx"

# The script automatically detects blocked publishers and falls back
```

**Defuddle-friendly domains:** opennursingjournal.com, frontiersin.org, mdpi.com, plos.org
**Defuddle-blocked domains:** pmc.ncbi.nlm.nih.gov, link.springer.com, sciencedirect.com

## Format Verification (before treating a hit as a comparable "prior study")
When a result has a short page range inside a **Supplement / "Suppl" / "S1" / "S2"** issue, or a
page count of 1-3, FLAG it for format-checking before citing it as a full peer-reviewed study:
- Open the actual PDF (or `web_extract` the publisher landing page / PDF) and confirm whether it is a
  **full article** (Abstract + Methods + Results + Discussion + References, multi-page) or a
  **conference abstract** (2-page summary, abstract-only findings).
- These carry different weight: a conference abstract is NOT a comparable "prior full study."
- Check whether the conference abstract was later expanded into a separate full-length article
  (search the author names + title); if so, cite the full article, not the abstract.
- State the distinction explicitly (e.g. "to our knowledge, the only prior Malaysian application of
  the ENSS is a conference abstract (Author et al., YYYY); no full peer-reviewed journal article
  using the ENSS among Malaysian nurses has been previously published"). Correct phrasing
  strengthens a 'first study' claim. Do NOT make a blanket 'first study' statement without this check.

## Quick Commands
```bash
# Basic search (searches all doc_types unless filtered)
python3 universal_rag.py --search "workload" --tag "Malaysia"

# Full-text search (slower, higher recall)
python3 universal_rag.py --search "burnout" --fulltext --max 15

# Filter by domain
python3 universal_rag.py --search "stress" --domain "Thesis_Bibliography_Web"

# Filter by doc_type (study/instrument/ebook/org_doc/gov_doc/tool/web)
python3 universal_rag.py --search "ENSS" --doc_type instrument

# Debug mode (shows search trace)
python3 universal_rag.py --search "query" --debug --max 10

# No query expansion (literal search only)
python3 universal_rag.py --search "query" --no-expansion
```

## Catalog Stats (update on each rebuild)
- LIVE: document count is computed at query time from `UNIVERSAL_CATALOG.json` — do NOT hardcode. As of 2026-08-03 the catalog holds 403 documents across domains (Malaysian_Nursing_Studies, Thesis_References, OUM_Research, Merged_OldRAG, Disk_Scan).
- Backup directory keeps last 5 timestamped versions (CAT_before_*.json).

## Self-Correction Workflow

The RAG system now includes automatic data quality control:

1. **Quality scoring** — Each entry gets a `data_quality` field with:
   - `quality_score` (0.1-1.0 based on completeness)
   - `issues` list (missing authors, no abstract, unverified, etc.)
   - `needs_verification` flag for entries with placeholder authors

2. **Crossref auto-enhancement** — When searching, entries with missing metadata
   (authors, journal, year, abstract) are auto-enhanced from Crossref API

3. **"Author unknown" trigger** — Any entry with empty/placeholder authors triggers
   immediate Crossref verification attempt. If DOI resolves, metadata is enhanced.
   If DOI doesn't resolve, entry flagged as `needs_review`.

4. **Placeholder DOI detection** — DOIs like `10.6007/IJARBSS` or `10.1155/nuf` that
   don't resolve to real papers are detected and flagged.

5. **Empty abstract handling** — If abstract is N/A, system attempts to extract
   text from the full TEXT_ file and use first paragraph as abstract.
- Backup directory keeps last 5 timestamped versions

## Key Process Decisions
1. **DOI verification ≠ Content verification** — both checked independently
2. **Dynamic query expansion** — Claude decides contextual expansion terms per search, not from a static dictionary
3. **Population/topic verification** — studied population (e.g., nurses) confirmed against methods/objective, not just keywords
4. **Web fallback never auto-indexed** — user must confirm before adding to catalog
5. **File safety** — original files never modified; always copy to RAG folder first

## Shared References
- `references/fulltext-retrieval-priority.md` — SINGLE SOURCE OF TRUTH for full-text acquisition chain (do not redefine per-skill).
- `pdf-processing/references/windows-environment-notes.md` (top-level in this repo) — or `software-development/pdf-processing/references/windows-environment-notes.md` in Hermes' category-organized local tree — shared Windows/MSYS path + interpreter gotchas.
