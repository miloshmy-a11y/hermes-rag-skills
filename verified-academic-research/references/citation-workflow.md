# Citation Management & Hallucination Prevention (adapted)

Adapted from the NousResearch hermes-agent `research-paper-writing` citation-workflow,
trimmed for our RAG/thesis pipeline. Core principle: **never generate citations from
memory — always verify programmatically.** AI-generated citations have a ~40% error
rate in the literature; the fix is API-verified metadata + 2-source confirmation.

## Why this matters
- ~40% of AI-generated citations contain errors (fabricated titles, wrong venues/years, bad DOIs).
- NeurIPS 2025 found 100+ hallucinated citations slipping through review.
- Consequence for a thesis: desk rejection, lost credibility, wasted time.
- **Solution**: verify every DOI via Crossref; confirm existence in ≥2 sources before citing.

## Verified Citation Workflow (5 steps)
```
1. SEARCH    → Semantic Scholar / OpenAlex / Crossref with specific keywords
2. VERIFY    → Paper exists in ≥2 sources (e.g. S2 + Crossref)
3. RETRIEVE  → Get authoritative BibTeX via DOI content negotiation
4. VALIDATE  → Confirm the claim appears in the source (abstract/full text)
5. ADD       → Add verified entry to catalog / .bib file
```

## API selection (which to use)
| API | Coverage | Rate limit | Best for |
| --- | --- | --- | --- |
| **Semantic Scholar** | 214M papers | 1 req/s (free key in `.env` as `S2_API_KEY`) | citation graphs, abstracts |
| **Crossref** | 140M+ DOIs | polite pool (add `mailto`) | DOI→metadata, BibTeX |
| **OpenAlex** | 240M+ works | 100K/day, 10 RPS | open, no key, country filters |
| **arXiv** | preprints | 3s delay | ML preprints, PDF |

**No official Google Scholar API** — scraping violates ToS. Use S2/OpenAlex instead.

## Step 3 — Retrieve authoritative BibTeX (KEY TRICK)
Use DOI content negotiation. This returns the publisher-of-record BibTeX (more accurate
than generating from metadata):
```python
import urllib.request
def doi_to_bibtex(doi: str) -> str:
    req = urllib.request.Request(
        f"https://doi.org/{doi}",
        headers={"Accept": "application/x-bibtex"})
    return urllib.request.urlopen(req, timeout=20).read().decode('utf-8', 'replace')

# Example (French 2000 ENSS):
print(doi_to_bibtex("10.1891/1061-3749.8.2.161"))
# -> @article{French_2000, title={An Empirical Evaluation of an Expanded
#    Nursing Stress Scale}, journal={Journal of Nursing Measurement},
#    author={French, Susan E. and Lenton, Rhonda and ...}, year={2000}, ...}
```
Also works for APA via `Accept: text/x-bibliography; style=apa` (some DOIs).

## Step 2 — Verify existence in 2 sources
```python
import urllib.request, json
def verify_paper(doi: str) -> tuple[bool, list]:
    sources = []
    # Crossref
    try:
        r = urllib.request.urlopen(
            f"https://api.crossref.org/works/{urllib.parse.quote(doi)}", timeout=15)
        if r.status == 200: sources.append("Crossref")
    except Exception: pass
    # Semantic Scholar (via s2.py or semanticscholar lib)
    # if S2 returns the paper -> sources.append("Semantic Scholar")
    return len(sources) >= 2, sources
```

## Citation key format
Use `author_year_firstword` (BibTeX conventional):
```
french_2000_expanded
karasek_1979_job
cohen_1983_global
```

## APA 7th (for inline thesis text)
Author, A. A., & Author, B. B. (Year). Title of article. *Journal Name*, *Vol*(Issue), pages. https://doi.org/xx.xxxx/xxxxx
For our catalog we store `apa_citation` generated from Crossref metadata + `bibtex`
retrieved via content negotiation (preferred for LaTeX theses).

## Integration with our skills
- `semanticscholar-skill` (`s2.py`) — S2 search/abstract/verify, uses `S2_API_KEY`.
- `openalex-skill` (`oa.py`) — bulk OA discovery, country_code:MY filter, no key.
- `pdf-processing` — full-text extraction; for paywalled PDFs, extract S2 paper-page
  HTML (`https://www.semanticscholar.org/paper/<paperId>`) as full text.
- This reference — BibTeX + 2-source verification + hallucination prevention.

## Verification checklist (before any citation is "done")
- [ ] DOI resolves via Crossref
- [ ] Paper found in ≥2 sources
- [ ] BibTeX retrieved via content negotiation (not from memory)
- [ ] Entry type correct (@article / @inproceedings / @misc)
- [ ] Author names complete, year + venue verified
- [ ] Citation key follows `author_year_firstword`
