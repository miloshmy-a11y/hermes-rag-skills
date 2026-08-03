---
name: general-purpose-rag
description: "Universal RAG - search 721+ papers, smart expansion, web fallback, APA output, auto-quality-control"
version: 4.5.3
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

# General-Purpose RAG System v4.5.2

## Overview
Universal RAG system for indexing and searching research papers on any topic. Features smart query expansion, automatic low-recall triggers, web fallback with content verification, defuddle HTML cleaning, and APA citation output.

## Primary Discovery Engine: OpenAlex (use INSTEAD of Crossref/Semantic Scholar for search)
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

## Legal Full-Text Retrieval Pipeline
OpenAlex is the PRIMARY discovery + metadata + OA-PDF source (free, no key, no rate
limit, CC0). For papers OpenAlex marks closed, use `paper-fetch` (Semantic Scholar →
Unpaywall → Europe PMC → Sci-Hub last-resort). User approved Sci-Hub as last resort for
non-profit personal use — so `PAPER_FETCH_NO_SCIHUB` is intentionally LEFT UNSET.
S2 now uses a configured API key (1 req/s, 1.8s gap enforced in `s2.py`) — prefer
`batch_papers`/`search_bulk` to stay under the limit.

**paper-fetch MSYS/PATH FIX (critical on Windows/git-bash):** Python mangles MSYS paths
(`/c/Users/...` → `C:\c\Users\...`). ALWAYS pass NATIVE Windows paths to paper-fetch:
  - skill script: `C:\Users\Milos\...\paper-fetch\scripts\fetch.py` (NOT `/c/Users/...`)
  - `--out`: `C:\Users\Milos\...\pf_out` (NOT `./pf_out` or `/c/...`)
  - feed DOIs via stdin: `cat file.txt | python3 <native-path> --batch - --out <native>`
  - Do NOT use `--batch <file>` with an MSYS path — the script can't resolve it.

**PRIMARY — `web_extract` HTML (highest success):** Resolve DOI → publisher landing URL (Crossref `URL`
field or `doi.org` redirect), then fetch with `web_extract` inside `execute_code`
(`from hermes_tools import web_extract`, batch ≤5 URLs/call, `char_limit=60000`). The HTML page holds the
FULL paper (~50–60k chars markdown). This retrieved 46/50 DOIs that failed PDF download in one session.
`web_extract` is NOT importable from terminal Python — run the fetch loop via `execute_code`.

Fallback chain (when web_extract returns a login wall / blocked page):
1. **Unpaywall API** — free open-access PDFs (`https://api.unpaywall.org/v2/{DOI}?email=YOUR_EMAIL`)
2. **PubMed Central (PMC)** — NIH-funded and deposited papers
3. **CORE** — repository-hosted copies (`core.ac.uk` API)
4. **DOAJ** — Directory of Open Access Journals
5. **Direct publisher PDF** — BMC/MDPI/PLOS/peerj (validate bytes start with `%PDF-` AND > 5 KB;
   publishers often return an HTML landing page instead of a PDF, e.g. BMC `track/pdf` now serves HTML)
6. **Browser tool** — only for JS/cookie-walled sites (BMJ Open, OUP, JSTOR, subscription scales)

```bash
# PDF route (terminal ok): python3 fulltext_retrieval.py "10.1177/23779608241245212"
# Returns: FOUND (via unpaywall) → PDF downloaded → text extracted
# If not found: NOT_ACCESSIBLE — abstract/citation only
```

**Always verifies:** Downloaded PDF is a real PDF (starts with `%PDF-`). Never uses header spoofing, proxies, or mirror sites.
**Login-wall false-positive guard:** if a fetch returns < 3 KB or a "log in / sign in" shell, do NOT mark
the entry as having full text — revert to metadata-only.

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
- Current: ~381 documents (259 study, 44 instrument, 18 ebook, 47 other, 6 org_doc, 2 gov_doc, 1 tool, 4 assignment)
- ~241 verified DOIs | 0 duplicates | Version 4.6+
- Backup directory keeps last 5 timestamped versions (CAT_before_*.json)

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
- 4 domains: Selected Studies, ENSS, Mendeley Import, OUM Research
- Backup directory keeps last 5 timestamped versions

## Key Process Decisions
1. **DOI verification ≠ Content verification** — both checked independently
2. **Dynamic query expansion** — Claude decides contextual expansion terms per search, not from a static dictionary
3. **Population/topic verification** — studied population (e.g., nurses) confirmed against methods/objective, not just keywords
4. **Web fallback never auto-indexed** — user must confirm before adding to catalog
5. **File safety** — original files never modified; always copy to RAG folder first