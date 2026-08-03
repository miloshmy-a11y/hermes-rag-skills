# Citation Enrichment & Pedigree via Semantic Scholar (proven patterns)

The `semanticscholar-skill` (installed at `skills/research/semanticscholar-skill`, `s2.py` + SKILL.md)
provides the **citation-intelligence layer** that Crossref and web_extract do NOT: citation counts,
forward citations, and recommendations. Install it if not present (`hermes skills install` or copy from
github.com/Agents365-ai/semanticscholar-skill). Patterns below are confirmed working this session.

## 1. Bulk citation-count enrichment of an existing catalog (fastest — one POST)
Crossref has no citation data. S2's `batch_papers` posts up to 500 IDs in ONE request — the only way to
avoid per-call anonymous throttling (5s gap).
```python
import os, sys, glob, json
sys.path.insert(0, r"C:\Users\Milos\AppData\Local\hermes\skills\research\semanticscholar-skill")
from s2 import *
BASE=r"C:\Users\Milos\AppData\Local\hermes\cache\web\universal_rag"
cat=json.load(open(BASE+"/UNIVERSAL_CATALOG.json",encoding='utf-8'))
docs=cat['documents']
dois=[d['doi'] for d in docs if d.get('doi','').startswith('10.')]
ids=["DOI:"+d for d in dois]
domap={d['doi'].lower():d for d in docs if d.get('doi','').startswith('10.')}
cc={}
for i in range(0, len(ids), 400):                 # stay under 500
    for p in batch_papers(ids[i:i+400], fields="title,year,citationCount,referenceCount,influentialCitationCount,externalIds"):
        if not p: continue                        # S2 returns null for unresolvable IDs — skip, don't crash
        doi=(p.get("externalIds") or {}).get("DOI","").lower()
        if doi and "citationCount" in p and doi in domap:
            cc[doi]=(p.get("citationCount",0), p.get("influentialCitationCount",0), p.get("referenceCount",0))
for d in docs:
    if d.get('doi','').lower() in cc:
        c=cc[d['doi'].lower()]; d['citation_count']=c[0]; d['influential_citation_count']=c[1]; d['reference_count']=c[2]
json.dump(cat, open(BASE+"/UNIVERSAL_CATALOG.json",'w',encoding='utf-8'), indent=2, ensure_ascii=False)
```
Proven: **234/242** catalog DOIs enriched in one pass. Top-cited in a nursing-stress catalog:
Cohen PSS 1983 (31k), Karasek JDCS 1979 (12k), Siegrist ERI 1996 (5.4k), JCQ 1998 (4.1k), Selye 1936 (4k).

## 2. Forward-citation / citation pedigree (for scale papers)
```python
for c in get_citations("DOI:10.1891/1061-3749.8.2.161", max_results=30):   # ENSS French 2000
    p=c.get("citingPaper") or {}
    print(p.get("year"), p.get("citationCount"), p.get("title"))
```
Surfaces who cited your scale — e.g. Pavek 2024 *Revised NSS* (already in catalog). Strong "established
lineage" evidence for the Discussion.

## 3. Recommendations (related-work discovery) — SEED-MATCHING, NOT gap analysis
```python
recs = recommend(positive_ids=["DOI:10.1891/1061-3749.8.2.161","DOI:10.1007/bf01321348"], limit=10)
```
Returns papers similar to your seeds. **Do NOT present this as evidence of a literature gap** — if seeds are
ENSS+NSS and no Malaysian papers appear, that is the algorithm's seed-matching, not a finding. The user's
own stated knowledge (e.g. "my thesis is the Malaysian ENSS study I know of") is the ground truth; never
contradict it or dress seed-matching silence up as a discovered gap.

## Rate-limit reality
- **API key is now configured** in Hermes `.env` (`S2_API_KEY`). `s2.py` reads it and
  enforces a **1.8s gap** (safe margin under S2's 1 req/s dedicated quota). Without a
  key it falls back to the anonymous shared pool at a 5s gap. Invalid/expired keys
  (401/403) auto-drop to anonymous mode.
- `batch_papers` (one POST, up to 500 IDs) is the cheapest call — prefer it for catalog
  citation enrichment. Per-paper loops (get_citations etc.) are slower but work.
- Even with a key, S2's shared backend can return transient 429s under peak load;
  `s2.py` auto-retries with exponential backoff (2s→60s, 5 retries) and returns data
  once the pool clears. Expect occasional multi-second delays — this is normal, not a bug.
- `batch_papers` returns a list aligned to input order with `null` entries for unresolved IDs — always
  `if not p: continue`.
- Run from `execute_code` (NOT terminal) so it can combine with `hermes_tools` if needed; `requests` is the
  only pip dependency.
