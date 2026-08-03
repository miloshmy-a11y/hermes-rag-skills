---
name: enss-rag-research
description: "Query RAG-indexed research with confirmed matches - search index first, verify against full text"
version: 3.0.0
author: Hermes Agent
license: MIT
platforms: [windows]
metadata:
  hermes:
    tags: [Research, RAG, ENSS, Indexing, Search, Catalog]
    related_skills: [verified-academic-research]
---

# Working with the ENSS Research Catalog System

## Trigger
User wants to query, search, or expand the catalog-indexed collection of research papers. The system uses a structured catalog with verification-based retrieval.

## Core Principle
**Search index first, then confirm against full text before presenting.** The system follows Claude's workflow requirement:

1. **Index-first discovery**: Use the catalog index to quickly find candidate studies
2. **Full-text confirmation**: Re-open actual files and confirm instrument, population, and scope genuinely match
3. **Confidence ranking**: Group results by confidence (exact → high → medium → low)
4. **Never present index-only matches as final results**

## Workflow

### 1. Search Using the Enhanced Catalog
```bash
# Basic search (searches index, then confirms against full text)
python3 catalog_search.py "supervisor conflict"

# Search with confidence filtering
python3 catalog_search.py "ENSS"
python3 catalog_search.py "malaysian nursing stress" --max 5

# List studies by verification status
python3 catalog_search.py --list --confidence VERIFIED

# List studies by tag
python3 catalog_search.py --list --tag "Supervisor Conflict"
```

### 2. Result Confidence Ranking
Results are ranked and labeled with confidence indicators:

| Symbol | Confidence | Meaning |
|--------|------------|---------|
| 🎯 | Exact | Instrument + content match confirmed |
| ✅ | High | Strong content match, verified |
| ⚠️ | Medium | Some content match, needs review |
| ❓ | Low | Keyword match only, not confirmed |

### 3. ENSS Subscale-Specific Queries
The system indexes studies by ENSS subscales:

```bash
# Search by ENSS subscale tags
python3 catalog_search.py "workload"
python3 catalog_search.py "supervisor"
python3 catalog_search.py "discrimination"
python3 catalog_search.py "death and dying"
```

### 4. Malaysian Nursing Stress Queries
Studies specifically about Malaysian nurses are identified through deep text analysis:

```bash
# List all Malaysian nursing stress studies
python3 catalog_search.py --list --tag "Malaysian Nursing Stress"

# List by confidence level
python3 catalog_search.py --list --tag "Malaysia-Nursing-Stress-High"
```

**Coverage**: 60 Malaysian nursing stress studies identified
- **High confidence**: 28 studies explicitly focused on Malaysian nurses
- **Medium confidence**: 32 studies mentioning Malaysia + stress topics

### 5. When Index Is Insufficient
If initial searches don't return enough results:

1. **Try more specific search terms**:
   ```bash
   python3 catalog_search.py "new graduate nurse stress supervisor malaysia"
   ```

2. **Browse by category**:
   ```bash
   python3 catalog_search.py --list --tag Burnout
   python3 catalog_search.py --list --tag ICU
   ```

3. **View complete study details**:
   ```bash
   python3 catalog_search.py --doc 10.1038/s41598-025-05253-0
   ```

## Index Structure (CATALOG_INDEX.json)

The catalog uses a **structured format** with clearly separated fields:

```json
{
  "doi": "10.1038/s41598-025-05253-0",
  "official_url": "https://doi.org/10.1038/s41598-025-05253-0",
  "title": "Quantifying the magnitude of stress among new graduate nurses...",
  "authors": ["Author1", "Author2"],
  "year": "2025",
  "journal": "Scientific Reports",
  "official_keywords": ["Burnout", "Stress"],  // From publication
  "population": "Nurses (New graduates, ICU nurses, Pediatric nurses)",
  "instrument": ["ENSS (Expanded Nursing Stress Scale)", "PSS"],
  "verification_status": "VERIFIED",
  "inferred_tags": ["New Graduate", "Supervisor Conflict", "ENSS-Problems_with_Supervisors"],
  "scope_note": "Uses ENSS (Expanded Nursing Stress Scale) to study stress among Nurses...",
  "confidence_note": "Discusses supervisor relationships, Focus on Malaysian context",
  "files": {
    "metadata_json": "2025_study.json",
    "full_text_pdf": "PDF_10.1038_s41598-025-05253-0.pdf",
    "extracted_text": "TEXT_10.1038_s41598-025-05253-0.txt"
  }
}
```

### Key Separation Principles
- **Official keywords**: As listed in the original publication (unverified)
- **Inferred tags**: Added by the indexing system (clearly labeled as inferred/unverified)
- **Instrument detection**: Explicitly identified from text (e.g., ENSS vs NSS vs ERI)
- **Population inference**: Inferred from abstract content

## Best Practices

### Keeping Index Concise
- ✅ Store abstracts/snippets (usually 200-500 chars)
- ✅ Store first 5 pages of PDF text for keyword confirmation
- ✅ Keep structured metadata in catalog only
- ❌ DON'T store full PDF text in the index
- ❌ DON'T duplicate content across files

### Updating the Index
When new information is found:
1. Add new study metadata to CATALOG_INDEX.json
2. Extract PDF text if available
3. Add/update tags based on content analysis
4. Run `python3 build_catalog_v2.py` to rebuild catalog
5. Run `python3 map_enss_subscales.py` to update subscale mapping

### Search Confirmation Workflow
1. **Query**: `python3 catalog_search.py "your query"`
2. **Index scan**: System identifies candidates from catalog
3. **Full-text check**: Re-opens TEXT_ files to confirm terms
4. **Confidence rating**: Results ranked by match evidence
5. **Present confirmed results**: Only studies with real matches

## Commands Reference

| Command | Purpose |
|---------|---------|
| `catalog_search.py --stats` | Show collection statistics |
| `catalog_search.py --list` | List all documents |
| `catalog_search.py --list --tag TAG` | List by specific tag |
| `catalog_search.py --list --confidence VERIFIED` | List verified studies |
| `catalog_search.py "search terms"` | Search with confirmation |
| `catalog_search.py --doc [DOI]` | View specific study details |
| `build_catalog_v2.py` | Rebuild structured catalog |
| `map_enss_subscales.py` | Update ENSS subscale mapping |
| `find_malaysian_studies.py` | Find Malaysian nursing stress studies |

## File Locations
- **Base directory**: `C:\Users\Milos\AppData\Local\hermes\cache\web\ENSS_research\`
- **Catalog index**: `CATALOG_INDEX.json` (structured format)
- **Old index**: `RAG_INDEX.json` (legacy, still used for supplementary data)
- **Quick lookup**: `QUICK_FIND_INDEX.md`
- **Search script**: `catalog_search.py` (enhanced with confirmation)
- **PDFs**: `PDF_[DOI].pdf`
- **Extracted text**: `TEXT_[DOI].txt`
- **Metadata**: Individual JSON files per study
- **Build scripts**: `build_catalog_v2.py`, `map_enss_subscales.py`, `find_malaysian_studies.py`