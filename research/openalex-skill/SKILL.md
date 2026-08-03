---
name: openalex-skill
description: Use when searching academic papers, getting citation counts, finding open-access full-text PDFs, or enriching metadata — via the OpenAlex API. Free, no API key, no rate limit, CC0 data. Triggers on queries about research papers, academic search, citation counts, OA PDFs, or literature discovery.
license: MIT
homepage: https://openalex.org
compatibility: Requires python3 and the `requests` package. No API key needed. Set OPENALEX_MAIL (any email) to be a "polite" caller (recommended).
platforms: [macos, linux, windows]
metadata: {"hermes":{"tags":["openalex","academic","paper-search","citation","open-access","literature","research"],"category":"research","requires_tools":["python3"],"related_skills":["semanticscholar-skill","paper-fetch","verified-academic-research","general-purpose-rag"]},"author":"Hermes Agent (adapted for user RAG)","version":"1.0.0"}
---

# OpenAlex Skill

Free, open catalog of 250M+ scholarly works. **No API key, no rate limit, CC0 data** —
strictly better than Semantic Scholar for bulk work. Returns `cited_by_count`,
`open_access` (status + direct OA PDF URL), and `concepts` (auto-tags) on every record.
For citation-graph analysis (who-cites-who, recommendations) where OpenAlex is weaker,
use the `semanticscholar-skill` — it now has a configured API key (1 req/s, 1.8s gap).

Base URL: `https://api.openalex.org/`

## Critical rule
Set a polite-pool email: `export OPENALEX_MAIL=you@example.com` (or pass `email=` param).
Never make the caller's key/secret an argument. All calls are read-only GET.

## Functions (see oa.py)
- `oa_search(query, filters="", per_page=10, select=None)` — free-text search, returns works
- `oa_by_doi(doi, select=None)` — direct lookup by DOI → citation count + OA PDF + concepts
- `oa_bulk_dois(dois, select="cited_by_count,open_access")` — batch enrich up to 100 DOIs/request
- `oa_citations(openalex_id_or_doi, per_page=10)` — works that cite this one (forward citations)
- `oa_concepts(query)` — auto-extracted concepts for tagging

## Filter examples (passed as `filter=` string)
- `from_publication_date:2018-01-01`
- `type:article`, `type:review`
- `open_access.is_oa:true` (has any OA)
- `has_doi:true`
- `authorships.institutions.country_code:MY` (Malaysia!) — useful for your thesis
- `concepts.id:UZ5BRXPR" (Nursing)` — subject scoping

## Usage
```python
import sys, os
sys.path.insert(0, os.path.expanduser("~/AppData/Local/hermes/skills/research/openalex-skill"))
from oa import *
# Search Malaysian nursing stress, get OA PDFs
r = oa_search("nursing stress Malaysia", filters="from_publication_date:2018-01-01", per_page=5)
for w in r["results"]:
    print(w["publication_year"], w["cited_by_count"], w["open_access"].get("oa_url"), w["title"])
# Enrich catalog DOIs with citation counts
cc = oa_bulk_dois(["10.1891/1061-3749.8.2.161","10.1007/bf01321348"])
```

## Why this matters for the user's nursing-stress RAG
- **No throttling** → bulk citation enrichment of all 242 catalog DOIs in seconds (S2 needs a key).
- **OA PDF URLs** → direct legal full-text fetch, complements web_extract + paper-fetch.
- **`country_code:MY` filter** → find Malaysian nursing-stress studies S2 cannot scope.
- **`concepts`** → auto-keywords for better RAG search recall.

## ToS / safety
- OpenAlex data is CC0 — free to use, store, redistribute.
- Only fetch OA PDFs (gold/diamond/bronze) — never use the skill for paywalled circumvention.
- For paywalled DOIs, fall back to `paper-fetch` (with Sci-Hub DISABLED: `PAPER_FETCH_NO_SCIHUB=1`).
