# Web-Found Study Indexing Workflow

## When to Index Web Results
Only index studies the user confirms they want added. Follow these steps:

### 1. DOI Verification (Crossref)
```bash
curl -s "https://api.crossref.org/works/{DOI}" -H "Accept: application/json"
```
Verify: DOI resolves + metadata (title/authors/year) matches the web search result.

### 2. PDF Acquisition
Try in order:
1. Crossref oa-url (highest success rate) — see `references/fulltext-acquisition-pipeline.md` for full priority chain
2. Publisher direct PDF link (from Crossref `link` array with `content-type: application/pdf`)
3. Europe PMC repository PDF (`https://www.ebi.ac.uk/europepmc/...`)
4. Unpaywall (`https://api.unpaywall.org/v2/{DOI}`)
5. PMC free article PDF (`https://pmc.ncbi.nlm.nih.gov/articles/PMC{ID}/pdf/...`)
6. Preprint servers (arXiv, bioRxiv)
7. Institutional repositories

**Last resort (grey):** Use defuddle HTML extraction when PDF is unavailable. See `references/defuddle-html-extraction.md`.

### 3. Text Extraction
Use PyMuPDF (`fitz`) — reads ALL pages (no page limit):
```python
doc = fitz.open(pdf_path)
full_text = ""
for page_num in range(len(doc)):
    full_text += doc[page_num].get_text()
```

### 4. DOI Extraction from PDF
Prioritize DOIs found in the first 2000 characters of text (title/abstract section) over DOIs in references section. Regex: `10\.\d{4,}/[^\s\]]+`

### 5. Catalog Entry Fields
Each new entry in UNIVERSAL_CATALOG.json requires:
- `doi` (normalized, lowercase)
- `title` (verbatim from source)
- `authors` (list, preserving full names from Crossref)
- `year`, `journal`, `volume`, `issue`, `pages`
- `domain` (e.g., "Selected Studies", "Mendeley Import")
- `inferred_tags` (auto-generated + manually curated)
- `official_keywords` (from publication)
- `verification_status`: "VERIFIED"
- `files`: {base_path, pdf (if available), extracted_text}

### 6. Deduplication Check
Before saving:
1. DOI (case-insensitive) — skip if exists
2. Title Jaccard similarity (>0.85) — skip if near-duplicate
3. File checksum — skip if byte-identical

### 7. Backup + Sync
```bash
cp UNIVERSAL_CATALOG.json backups/UNIVERSAL_CATALOG_$(timestamp).json
cp UNIVERSAL_CATALOG.json skills/research/general-purpose-rag/
```

## Key Learning: Population vs. Keyword Match
Always verify the study's **actual population** (from Methods section) matches the query, not just that the keyword appears somewhere in the text. Background/intro sections often mention workload as a general problem without measuring it as a finding.
