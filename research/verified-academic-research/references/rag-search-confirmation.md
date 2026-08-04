# RAG Search Confirmation Pattern

## Problem
Keyword-only search in research catalogs can produce false positives - studies that merely mention a term (e.g., "Malaysia") without actually studying Malaysian nursing stress. Users need confirmed matches, not keyword overlaps.

## Solution: Index-First Discovery with Full-Text Confirmation

### Core Workflow
1. **Index scan** (fast): Use catalog metadata to identify candidates
2. **Full-text confirmation** (accurate): Re-open TEXT_[DOI].txt files to verify terms appear in context
3. **Confidence ranking**: Rate results by evidence strength
4. **Present only confirmed matches**

### Implementation
```python
def search_and_confirm(query_terms, catalog, base_dir):
    """Search index first, then confirm against full text"""
    # Step 1: Index scan - find candidates
    candidates = []
    for doc in catalog['documents']:
        searchable = (doc.get('title','') + ' ' + doc.get('abstract','') + ' ' +
                     ' '.join(doc.get('inferred_tags', [])) + ' ' +
                     ' '.join(doc.get('official_keywords', [])))
        if any(term.lower() in searchable.lower() for term in query_terms):
            candidates.append(doc)
    
    # Step 2: Full-text confirmation
    confirmed = []
    for doc in candidates:
        # Get base_path for multi-domain catalogs
        base_path = doc.get('files', {}).get('base_path', base_dir)
        text_file = doc.get('files', {}).get('extracted_text', '')
        
        full_text = doc.get('abstract', '')
        if text_file:
            text_path = os.path.join(base_path, text_file)
            if os.path.exists(text_path):
                with open(text_path, 'r', encoding='utf-8') as f:
                    full_text += ' ' + f.read()[:5000]
        
        evidence = []
        score = 0
        
        for term in query_terms:
            count = full_text.lower().count(term.lower())
            if count > 0:
                score += count
                evidence.append(f"'{term}' found {count} times in content")
        
        # Boost score for instrument/population matches
        for term in query_terms:
            for instr in doc.get('instrument', []):
                if term.lower() in str(instr).lower():
                    score += 5
                    evidence.append(f"Instrument match: {instr}")
        
        # Tag matches
        for term in query_terms:
            for tag in doc.get('inferred_tags', []):
                if term.lower() in tag.lower():
                    score += 2
                    evidence.append(f"Tag match: {tag}")
        
        # Only include if score >= 2 (not single-keyword-only matches)
        if score >= 2:
            confidence = "exact" if score >= 5 else "high" if score >= 3 else "medium"
            confirmed.append({
                'doi': doc.get('doi', ''),
                'title': doc.get('title', ''),
                'score': score,
                'confidence': confidence,
                'evidence': evidence,
                'domain': doc.get('domain', 'general'),
                'population': doc.get('population', 'Not specified')
            })
    
    return sorted(confirmed, key=lambda x: x['score'], reverse=True)
```

### Multi-Domain Search Extension
For catalogs spanning multiple research domains:
```python
def search_cross_domain(query, catalog, domains=None, tags=None, base_dirs=None):
    """
    Search across all domains with optional filtering
    """
    # domain filter
    if domains:
        docs = [d for d in catalog['documents'] if d.get('domain') in domains]
    else:
        docs = catalog['documents']
    
    # tag filter
    if tags:
        docs = [d for d in docs 
                if any(t.lower() in [tag.lower() for tag in d.get('inferred_tags', [])] 
                       for t in tags)]
    
    results = []
    for doc in docs:
        confidence, evidence, score = confirm_match(doc, query_terms, base_dirs)
        if confidence != "low":
            results.append({...})
    
    # Group results by domain for presentation
    by_domain = group_by_domain(results)
    return by_domain
```

### Confidence Rating System

| Confidence | Criteria |
|------------|----------|
| 🎯 Exact | Instrument explicitly stated + multiple content matches (score ≥ 5) |
| ✅ High | Strong content match with verified DOI (score 3-5) |
| ⚠️ Medium | Keyword present with some context (score 1-3) |
| ❓ Low | Keyword-only match (should be excluded) |

### Key Techniques

#### Multi-Pass Analysis
1. **Shallow pass**: Check titles, abstracts, journal names, tags
2. **Deep pass**: Scan full extracted PDF text + metadata JSON files
3. **Keyword expansion**: Include institutional names, locations, methodology terms

#### Tag Deduplication
After multiple analysis passes, tags accumulate duplicates:
```python
doc['inferred_tags'] = list(set(doc['inferred_tags']))  # Remove exact duplicates
# Normalize case
doc['inferred_tags'] = list({t.lower(): t for t in doc['inferred_tags']}.values())
```

#### Incremental Updates
Don't rebuild entire index. Instead:
1. Check for duplicate DOIs before adding new entries
2. Append to existing documents array
3. Run selective re-tagging scripts
4. Clean up duplicates afterward

### Fallback When Local Results Insufficient
When searches return fewer than 5 results:
1. System flags: "Only N local results found. Web search recommended"
2. User manually searches academic databases
3. User downloads PDFs, verifies DOIs
4. User adds to catalog via `--add-folder` command
5. **System does NOT auto-download** - always wait for user action

### Pitfalls
- **Keyword inflation**: "Malaysia" mentioned once ≠ Malaysian study. Require multiple mentions or explicit population focus
- **Index-only bias**: Never present index matches as final results without full-text confirmation
- **Path escaping**: On Windows, use forward slashes (`/c/Users/...`) in Python paths, NEVER escaped backslashes
- **Python version mismatch**: PyMuPDF may be in system Python user site-packages, not venv
- **File detection failures**: When files exist but aren't found, check (1) working directory, (2) DOI-safe naming convention, (3) `base_path` field in multi-domain catalogs
- **Tag accumulation**: After multi-pass analysis runs, tags accumulate duplicates. Always run deduplication after each pass
- **Base path confusion**: In multi-domain catalogs, always use `doc['files']['base_path']` instead of assuming files are in the catalog's directory
- **Instrument field variations**: Some documents may have `["Not specified"]` as instrument - distinguish from missing field
- **Query term expansion**: When searching for "supervisor conflict", both terms must appear in the same document (not just different documents) for confirmation
- **Tag invalidation after DOI resolution**: After fetching corrected metadata from Crossref, existing inferred_tags may no longer match the study's actual content. Tags must be re-inferred from the verified title/abstract. See `references/catalog-deduplication.md` for the re-inference pattern and a real-world example where 12 studies had incorrect tags after Crossref resolution.