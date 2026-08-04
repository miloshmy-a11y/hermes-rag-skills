# Data Quality Control for RAG Catalog

## Overview
Each document in UNIVERSAL_CATALOG.json has a `data_quality` field for self-correction.

## Quality Scoring Algorithm
```
quality_score = max(0.1, 1.0 - (len(issues) * 0.15))
```

## Issues Tracked

### 1. Placeholder Authors
- **Detection:** Authors list is empty `[]` or all entries are `.` 
- **Action:** Auto-enhance from Crossref API
- **Example:** `{"authors": ["."]}` → flagged, Crossref lookup triggered

### 2. Missing Journal
- **Detection:** `journal` field is empty or None
- **Action:** Try Crossref `container-title` field

### 3. Missing Year
- **Detection:** `year` field is empty or None
- **Action:** Try Crossref `published.date-parts`

### 4. No Abstract
- **Detection:** `abstract_preview` is "N/A" or empty
- **Action:** Try Crossref `abstract` field, or extract from first paragraphs of TEXT_ file

### 5. Unverified DOI
- **Detection:** `verification_status` != "VERIFIED"
- **Action:** Flag for Crossref verification

### 6. Local DOI (not Crossref)
- **Detection:** DOI starts with `local:` or doesn't resolve via Crossref
- **Action:** Mark as `local_only`, cannot verify via Crossref

## Self-Correction Triggers

### "Author Unknown" Trigger
When any search result has empty/placeholder authors:
1. Immediately attempt Crossref DOI resolution
2. If DOI resolves: auto-enrich authors, journal, year, abstract
3. If DOI doesn't resolve: flag as `needs_review` for manual check

### Empty Abstract Trigger
When `abstract_preview` is "N/A":
1. Check if TEXT_ file exists for this DOI
2. Extract first 2 paragraphs as fallback abstract
3. Update `abstract_preview` field

## Quality Status Levels

| Status | Score | Description |
|--------|-------|-------------|
| `complete` | 1.0 | All metadata present, verified |
| `needs_review` | 0.7-0.85 | Some issues, can be enhanced |
| `local_only` | 0.3-0.5 | Local file only, no DOI verification |
| `placeholder` | 0.1-0.3 | Placeholder DOI, no real metadata |

## Implementation in universal_rag.py
```python
# In search() method, before presenting results:
for doc in results:
    if doc.get('data_quality', {}).get('issues'):
        # Auto-enhance from Crossref
        doc = self._enhance_from_crossref(doc)
```
