# Catalog Deduplication Patterns for Research RAG Systems

> Session-specific reference: multi-layer deduplication strategy used to clean a 720-document
> universal RAG catalog across 5 domains (OUM_Research, ENSS, Mendeley Import, Selected Studies, OUM_Books).

## When to Run Deduplication

- After importing from a new source (Mendeley, OUM folders, Crossref downloads)
- When the same DOI appears across multiple domains
- When filenames are generic (e.g., `chatgpt.txt`, `essay.txt`) and may collide
- Periodically as part of catalog maintenance (recommend every 50+ new documents)

## Multi-Layer Detection Strategy

Run all three checks. Each catches a different failure mode:

### Layer 1: DOI Normalization (Primary)

DOIs are case-insensitive. The same paper can appear with different casing depending on extraction source.

```python
def normalize_doi(doi):
    """Normalize DOI for comparison"""
    if not doi or doi.startswith('local:'):
        return doi
    return doi.lower()
```

**Example**: `10.2478/fon-2023-0052` vs `10.2478/FON-2023-0052` are the same paper.

**Pitfall**: Some PDFs contain truncated DOIs (e.g., `10.1136/bmjopen-2021-` cut off by page boundary). These are NOT duplicates of each other — each represents a different paper. Keep truncated DOIs as `LOCAL` status.

### Layer 2: Title Normalization (Secondary)

Catches duplicates where DOI is missing or differs but title is identical.

```python
def normalize_title(title):
    t = title.strip().lower()
    t = t.rstrip('.')
    if t.startswith('the '):
        t = t[4:]
    return t
```

**Common student-file collisions:**
- `chatgpt.txt`, `chatgpt2.txt`, `ChatGPT.TXT` — multiple student submissions
- `essay.txt`, `essay2.txt`, `Essay2.INSTRUCTOR` — versioned drafts
- `ocp.txt`, `ocp1.txt`, `ocp2.txt` — different assignments with same filename pattern
- `gantt`, `q.txt`, `info.txt` — generic planning/checklist files

**Strategy**: Keep the copy with the most extracted text or best metadata.

### Layer 3: Full File Checksum (Tertiary)

When DOI and title don't match (truncated DOIs, differently-extracted titles), use full file content comparison:

```python
def get_file_checksum(filepath, chunk_size=8192):
    """Full MD5 checksum — catches identical files with different names"""
    if not filepath or not os.path.exists(filepath):
        return None
    try:
        h = hashlib.md5()
        with open(filepath, 'rb') as f:
            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                h.update(chunk)
        return h.hexdigest()
    except:
        return None
```

**Important**: Use full-file checksum, not partial. Partial checksums can collide when files share identical headers but different content.

## Quality-Based Retention Scoring

When a duplicate group is found, score each candidate and keep the highest:

```python
def doc_quality_score(doc):
    """Score document quality — higher = keep this one"""
    score = 0
    # Verified DOIs are highest priority
    if doc.get('verification_status') == 'VERIFIED':
        score += 100
    
    # Domain priority (academic rigor)
    domain_priority = {
        'ENSS': 10,          # Core nursing stress instrument studies
        'Selected Studies': 9,  # Curated academic papers
        'Mendeley Import': 8,   # Peer-reviewed imported papers
        'OUM_Research': 6,     # Course materials (lower priority)
        'OUM_Books': 5,        # Textbook materials
    }
    score += domain_priority.get(doc.get('domain', ''), 0)
    
    # Prefer documents with extracted text
    if doc.get('files', {}).get('extracted_text'):
        score += 5
    # Prefer documents with identified instruments
    score += len(doc.get('instrument', [])) * 2
    # Prefer documents with known authors
    score += len(doc.get('authors', [])) * 3
    # Prefer documents with year
    if doc.get('year'):
        score += 3
    
    return score
```

## Cross-Domain Duplicate Detection

A DOI may appear in multiple domains (e.g., same paper imported from both Mendeley and from the ENSS thesis collection). Detection:

```python
from collections import defaultdict
multi_domain_dois = defaultdict(set)
for doc in catalog['documents']:
    doi = doc.get('doi', '')
    if doi and not doi.startswith('local:'):
        multi_domain_dois[doi].add(doc.get('domain', ''))
```

When a DOI appears in multiple domains, keep the copy from the domain with higher academic priority (per the quality score above).

## File Cleanup After Deduplication

When removing a document, clean up its associated files:

```python
for doc in docs_to_remove:
    files = doc.get('files', {})
    for field in ['full_text_pdf', 'extracted_text']:
        fname = files.get(field)
        if fname:
            fpath = os.path.join(files.get('base_path', '.'), fname)
            if os.path.exists(fpath):
                os.remove(fpath)
```

## Verification Checklist

After deduplication:

```python
from collections import Counter

# 1. No duplicate DOIs (case-insensitive)
doi_counts = Counter(normalize_doi(d.get('doi', '')) for d in docs if d.get('doi', ''))
assert len([d for d, c in doi_counts.items() if c > 1]) == 0

# 2. No exact title duplicates (normalized)
title_counts = Counter(normalize_title(d.get('title', '')) for d in docs if d.get('title', ''))
assert len([t for t, c in title_counts.items() if c > 1]) == 0

# 3. No identical file checksums
# (recompute and verify)
```

### Critical: Full-Text Re-Verification After Deduplication

**Key lesson from production use**: Deduplication by DOI/title/checksum is necessary but **not sufficient**. After dedup, always re-verify search results by reading actual file content:

```python
def thorough_search_verification(docs, query_terms, required_content_terms):
    """
    After deduplication, re-verify that documents actually contain the
    content they're tagged with. Catalog metadata (tags) may be inaccurate
    from prior indexing runs.
    
    Returns the TRUE count of documents, which may differ significantly
    from tag-based counts.
    """
    verified_results = []
    for doc in docs:
        # Read the actual TEXT_ file (not just catalog metadata)
        txt_path = os.path.join(doc['files']['base_path'], 
                                doc['files'].get('extracted_text', ''))
        if os.path.exists(txt_path):
            with open(txt_path, 'r', errors='ignore') as f:
                text = f.read(10000)  # First 10k chars
            
            # Verify terms exist in ACTUAL content, not just tags
            content_lower = text.lower()
            all_present = all(term.lower() in content_lower 
                            for term in required_content_terms)
            if all_present:
                verified_results.append(doc)
    
    return verified_results
```

**Real-world example**: A search for "workload among Malaysian nurses" found:
- 19 studies by full-text verification (checking TEXT_ files)
- Only 5 studies by tag matching alone
- The 14 additional studies had "Workload" as an inferred tag from prior indexing but "workload" wasn't prominent in their actual text
- Conversely, 4 studies had "workload" in text but NOT in their tags
- **Conclusion**: Always validate against actual file content, not just catalog metadata

### Tag Propagation After DOI Resolution

**Critical pitfall**: When DOI metadata is fetched from Crossref, the existing inferred tags may not match the study's actual content. Tags must be re-inferred from the corrected title and abstract after metadata verification.

```python
# After fetching Crossref metadata, ALWAYS re-infer tags
doc['title'] = crossref_data['title']
doc['abstract'] = crossref_data.get('abstract', '')

# Re-run tag inference on the corrected content
# DO NOT keep old tags blindly - they may reference old (incorrect) content
doc['inferred_tags'] = infer_tags(doc['title'] + ' ' + doc.get('abstract', ''), 
                                  doc.get('instrument', []), 
                                  doc.get('population', ''))
```

**Real-world impact**: 12 studies had Malaysia + Workload tags from prior indexing that were incorrect because the tags were propagated from a different version of the study's content. After re-inferring tags from the verified Crossref metadata, 5 additional studies gained the correct "Workload" and "Malaysia" tags that were previously missing.

### Cross-Domain Tag Consistency

**Critical pitfall**: When importing from multiple sources (Mendeley, ENSS, OUM), tags may be inconsistent across domains for the same DOI. Always normalize tags after deduplication:

```python
# After dedup, normalize tags for duplicate DOI groups
def normalize_tags_for_group(dup_group):
    """Merge tags from all copies of the same DOI"""
    merged_tags = set()
    for doc in dup_group:
        merged_tags.update(doc.get('inferred_tags', []))
    # Keep merged tags in the highest-priority doc
    best_doc = max(dup_group, key=doc_quality_score)
    best_doc['inferred_tags'] = list(merged_tags)
```

## Scripts

| Script | Purpose |
|--------|---------|
| `deduplicate_catalog_v2.py` | DOI/title/checksum deduplication with quality scoring |
| `final_cleanup.py` | Removes last edge-case title duplicates |
| `import_mendeley.py` | Imports with built-in checksum and DOI deduplication |
| `migrate_enss_data.py` | Migrates ENSS-specific metadata to universal catalog |

## See Also
- `references/claude-review-v44-feedback.md` — External review feedback from Claude with 7 improvement recommendations and their implementations