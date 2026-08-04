# Defuddle HTML Extraction for RAG

## Overview
Defuddle (`npx defuddle parse <URL> --markdown`) extracts clean article text from HTML pages, removing navigation, ads, sidebars, and boilerplate.

## When to Use

- PDF download fails but HTML version is available
- Publisher page allows direct HTML access
- Need clean text for faster full-text search

## Workflow

### 1. Try defuddle on publisher URL
```bash
npx defuddle parse "https://publisher-url.com/article" --markdown
```

### 2. If defuddle blocked (Cloudflare/Sci-Hub)
Fall back to web_extract or manual HTML parsing:
```bash
# Use Hermes web_extract tool
web_extract urls=["<URL>"]
```

### 3. Check output quality
- Valid: Article body text (1000+ chars)
- Invalid: "Checking your browser..." / Cloudflare challenge (skip)

## Defuddle-Friendly Publishers
- opennursingjournal.com
- www.hindawi.com
- www.frontiersin.org
- www.mdpi.com
- journals.plos.org

## Defuddle-Blocked Publishers (use fallback)
- pmc.ncbi.nlm.nih.gov (Cloudflare)
- www.ncbi.nlm.nih.gov (Cloudflare)
- link.springer.com (challenge page)
- www.nature.com
- onlinelibrary.wiley.com
- www.sciencedirect.com

## Integration with acquire_fulltext.py
The `acquire_fulltext.py` script implements the full fallback chain:
1. Crossref oa_url → PDF download
2. Europe PMC → repository PDF
3. Unpaywall → repository OA
4. Defuddle on publisher page (HTML → clean text)
5. Defuddle on PMC page (if publisher blocked)
6. web_extract fallback (Hermes tool)

## Example usage
```python
from defuddle_extractor import extract_with_defuddle

result = extract_with_defuddle(
    "https://opennursingjournal.com/VOLUME/15/PAGE/204/ABSTRACT/",
    "10.2174/1874434602115010204"
)
# Returns: {"doi": "...", "title": "...", "content_length": 1832, "text_file": "TEXT_10.2174_..."}
```
