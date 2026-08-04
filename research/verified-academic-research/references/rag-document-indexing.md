# Document Indexing & RAG System for Research Collections

## Problem
When working with large sets of research papers (dozens of DOIs, PDFs, abstracts), agents need a lightweight, queryable index to avoid repeated API calls and enable full-text search across extracted content.

## Solution: Lightweight JSON-based RAG Index

### Index Structure (Single Collection)
```json
{
  "metadata": {
    "source_document": "original source description",
    "total_studies": 79,
    "indexed_documents": 79,
    "pdf_documents": 25,
    "text_documents": 25
  },
  "documents": [
    {
      "doi": "10.1891/1061-3749.8.2.161",
      "title": "Study title",
      "authors": "Author, A. A, Author, B. B.",
      "year": "2018",
      "journal": "Journal Name",
      "abstract": "Abstract text...",
      "official_keywords": ["Stress", "Burnout"],  // From publication
      "tags": ["ENSS", "Nursing", "PDF-Available"], // Inferred by system
      "files": {
        "metadata_json": "2018_Study.json",
        "full_text_pdf": "PDF_10.1891_1061-3749.8.2.161.pdf",
        "extracted_text": "TEXT_10.1891_1061-3749.8.2.161.txt"
      }
    }
  ],
  "search_index": {
    "stress": ["doi1", "doi2"],
    "nurse": ["doi1", "doi3"]
  }
}
```

### Index Structure (Multi-Domain / Universal Catalog)
```json
{
  "metadata": {
    "catalog_name": "Universal Research Catalog",
    "version": "3.1",
    "total_documents": 102,
    "domains": ["ENSS", "Selected Studies", "New Topic"],
    "last_updated": "2024-..."
  },
  "documents": [
    {
      "doi": "10.1038/s41598-025-05253-0",
      "title": "Study title",
      "domain": "ENSS",
      "instrument": ["ENSS (Expanded Nursing Stress Scale)", "PSS"],
      "official_keywords": ["Burnout", "Stress"],
      "inferred_tags": ["Workload", "Supervisor Conflict"],
      "files": {
        "base_path": "C:/path/to/ENSS_research", // CRITICAL for multi-folder
        "full_text_pdf": "PDF_10.1038_....pdf",
        "extracted_text": "TEXT_10.1038_....txt"
      }
    }
  ],
  "search_index": { "term": [{"doi": "...", "domain": "ENSS"}] }
}
```

**Key differences for multi-domain catalogs:**
1. **Always store `base_path`** in files dict - enables searching across multiple source folders
2. **Use `domain` field** to tag studies by topic domain
3. **Always separate `official_keywords` from `inferred_tags`**
4. **Use `--add-folder` pattern** to incrementally add new collections

### Workflow Steps

#### Step 1: Extract DOIs from source document
```python
# Extract DOIs from a Word document
import zipfile, re

with zipfile.ZipFile('document.docx', 'r') as zip:
    xml = zip.read('word/document.xml').decode('utf-8')

dois = re.findall(r'10\.\d{4,}/\\S+', xml)
dois = [d.strip('.,;\\s') for d in dois]
```

#### Step 2: Verify DOIs and collect metadata via Crossref
```bash
# Verify single DOI
curl -s "https://api.crossref.org/works/10.1891/1061-3749.8.2.161"

# Extract metadata: title, authors, year, journal, abstract
```

#### Step 3: Download PDFs where available
```bash
# Get PDF links from Crossref metadata
curl -s "https://api.crossref.org/works/{DOI}" | python3 -c "
import sys, json
d = json.load(sys.stdin)
links = d.get('message',{}).get('link', [])
for link in links:
    if 'pdf' in link.get('content-type', ''):
        print(link.get('URL'))
"
```

#### Step 4: Extract text from PDFs
Use PyMuPDF (import fitz):
```python
import fitz
with fitz.open('PDF_file.pdf') as pdf:
    text = ""
    for page in pdf[:5]:  # First 5 pages
        text += page.get_text()
```

**Python path note:** PyMuPDF (fitz) is typically in user site-packages, not venv.
- Windows: `C:\Users\\AppData\Roaming\Python\Python314\site-packages`
- Linux/macOS: `/c/Users/<user>/AppData/Roaming/Python/Python314/site-packages` or similar
- Run with system Python: `C:\Python314\python.exe`

#### Step 5: Build search index
```python
# For each study, index keywords from title, abstract, journal, tags
search_terms = ['stress', 'nurse', 'malaysia', 'ENSS', 'burnout', ...]
for term in search_terms:
    for doc in documents:
        text = doc['title'] + ' ' + doc.get('abstract', '') + ' '.join(doc.get('tags', []))
        if term in text.lower():
            search_index[term].append(doc['doi'])
```

#### Step 6: Provide RAG query interface
```python
class ResearchRAG:
    def search(self, query, max_results=10):
        # 1. Find candidates from search index
        # 2. CONFIRM matches against actual TEXT files
        # 3. Rank by confidence (exact/high/medium/low)
        # 4. Return only confirmed matches
        pass

    def add_documents_from_folder(self, folder_path, domain="general"):
        # Incremental addition with deduplication
        # Maps source folder format to catalog format
        pass
```

### File Naming Convention
- Metadata: `{year}_{short_title}.json`
- PDF: `PDF_{DOI_with_slashes_replaced_by_underscores}.pdf`
- Text: `TEXT_{DOI_with_slashes_replaced_by_underscores}.txt`

### Search Heuristics
1. **Title match** = highest weight (10+ points)
2. **Abstract match** = medium weight (5+ points)
3. **Extracted text match** = lower weight (3+ points + count of occurrences)
4. **Tag match** = bonus (1-2 points)
5. **Instrument match** = high weight (5+ points)
6. **Sort by score descending** for ranked results

### Multi-Pass Analysis Pattern
For comprehensive topic coverage:
1. **Shallow pass**: Search titles, abstracts, journal names, and tags
2. **Deep pass**: Scan ALL available text including:
   - Full extracted PDF text (first 5-8 pages)
   - Metadata JSON files (crossref responses)
   - Extended keyword sets (institution names, locations, methodology terms)
3. **Confidence scoring**:
   - **High**: Explicit mention in abstract/title (e.g., "Burnout among nurses in Malaysia")
   - **Medium**: Mentioned in full text but not explicit (e.g., "during a study in Malaysia")
   - **Low**: Single indirect mention
4. **Deduplication**: Always run tag deduplication after multi-pass tagging
5. **Validation**: Re-run stats to verify counts match expected values

### Pitfalls
- **Missing libraries**: Use system Python (`C:\\Python314\\python.exe`) with user site-packages, not venv
- **Path escaping**: Use raw strings or forward slashes in Python paths on Windows
- **Rate limits**: Crossref API is generally generous but add sleeps between bulk requests
- **Truncated abstracts**: Some DOIs may not have abstracts in Crossref metadata - fall back to PDF text extraction
- **Shallow vs. deep analysis**: Abstract-only keyword matching finds only ~10-20% of relevant studies. For comprehensive coverage, search ALL available text including full extracted PDF content and metadata JSON files. Initial shallow pass + deep text scan is more effective than either alone.
- **Tag duplication in multi-pass tagging**: When running multiple analysis scripts that re-tag documents, tags accumulate duplicates. Always run a deduplication step (`doc['tags'] = list(set(doc['tags']))` after each pass) and validate with stats before final indexing.
- **Python path management**: PyMuPDF (fitz) and other packages may be in user site-packages (`C:\\Users\\...\\AppData\\Roaming\\Python\\Python314\\site-packages`) rather than venv. Use `sys.path.insert(0, user_site)` if imports fail, or run with the system Python that has packages installed.
- **Index rebuild side effects**: Rebuilding CATALOG_INDEX.json from metadata JSON files can lose ENSS subscale mappings if not re-run. Always run subscale mapping AFTER rebuilding catalog.
- **Multiple index format confusion**: Avoid maintaining parallel RAG_INDEX.json and CATALOG_INDEX.json files. Standardize on CATALOG_INDEX.json for structured catalogs with verification status, instrument tracking, and inference separation.
- **Multi-domain file paths**: When merging collections from different folders, each document must carry its own `base_path` for file access. Never assume all files live in the same directory.
- **Tag field naming**: Use `inferred_tags` for system-added tags, never overwrite with generic `tags`. Keep `official_keywords` separate.
- **Domain field is required**: For multi-domain catalogs, always set the `domain` field on each document to enable domain-filtered searches.
- **Configurable domain tagging**: Instead of hard-coded keyword dictionaries, use `_load_domain_tags(domain)` that loads domain-specific keyword sets from `domain_tags.json`. This allows the same RAG system to work across any research domain (nursing, CS, psychology, etc.) without code changes. Default domains: `general`, `ENSS`, `OUM_Research`, `Selected Studies`, `Mendeley Import`.
- **Full-text search performance**: Default search uses metadata + keyword index only. Enable full-text body search with `fulltext_search=True` flag for higher recall when needed. This balances performance with thoroughness.

## See Also
- `references/rag-smart-search-v45.md` — Query expansion dictionary, low-recall trigger logic, result labeling convention, Crossref author extraction fix, DOI verification caching, and low-recall logging