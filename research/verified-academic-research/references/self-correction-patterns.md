# Self-Correction Patterns for RAG Catalog

## Patterns That Trigger Auto-Verification

| Pattern | Detection | Action |
|---------|-----------|--------|
| `Authors: []` or `["."]` | Empty or placeholder author list | Query Crossref API immediately |
| `abstract_preview: "N/A"` | Missing abstract | Extract first paragraph from TEXT_ file |
| `verification_status: null` | DOI not verified | Crossref DOI resolution |
| `10.6007/...`, `10.1155/20NN` | Placeholder DOIs | Flag as `local_only` |
| `journal: ""` | Missing journal | Crossref `container-title` field |
| `year: None` | Missing year | Crossref `published.date-parts` |

## Quality Issues Found During This Session

### 1. Placeholder Authors (16 entries)
**Problem:** 508 entries (mostly `local:` DOIs) have empty author lists.
**Fix:** For real DOIs, Crossref API enhancement fetches authors automatically.
**For local entries:** Cannot be verified via Crossref — marked as `quality_score: 0.3`.

### 2. Empty Abstracts (717 entries)
**Problem:** 99% of entries have `abstract_preview: "N/A"`.
**Fix:** When full-text TEXT_ file is available, extract first 2 paragraphs as fallback abstract.

### 3. Non-Resolving Placeholder DOIs
**Problem:** DOIs like `10.1155/nuf`, `10.1155/2023`, `10.1037/0000165-000` don't resolve to real papers.
**Fix:** `data_quality.status = local_only`, flagged with `issues: ["local_doi_not_verified"]`

## Self-Correction Code Pattern

```python
# In universal_rag.py — auto-enhance during search:
def _enhance_from_crossref(self, doc):
    """Auto-enhance entry with missing metadata from Crossref."""
    doi = doc.get('doi', '')
    if doi.startswith('local:') or not doi:
        return doc  # Can't verify local entries
    
    try:
        url = f"https://api.crossref.org/works/{doi}"
        req = urllib.request.Request(url, headers={'User-Agent': 'RAG-System/4.5'})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
        item = data['message']
        
        # Fill missing fields
        if not doc.get('authors') or doc.get('authors') == ['']:
            doc['authors'] = [f"{a.get('family','')}, {a.get('given','')[:1]}."
                             for a in item.get('author', [])]
        
        if not doc.get('journal'):
            journals = item.get('container-title', [])
            if journals:
                doc['journal'] = journals[0]
        
        if not doc.get('year'):
            dates = item.get('published', {}).get('date-parts', [[None]])
            if dates and dates[0][0]:
                doc['year'] = str(dates[0][0])
        
        if doc.get('abstract_preview') == 'N/A':
            abstract = item.get('abstract', '')
            if abstract:
                import re
                clean = re.sub(r'<[^>]+>', '', abstract)
                doc['abstract_preview'] = clean[:500]
        
        # Update quality score
        doc['data_quality'] = {
            'status': 'enhanced',
            'quality_score': 0.85,
            'issues': [],
            'enhanced_at': datetime.now().isoformat()
        }
        
    except Exception:
        doc['data_quality']['issues'].append('crossref_enhancement_failed')
    
    return doc
```
