---
name: rhetorag-research-indexing
description: "Build searchable research RAG indexes for fast retrieval."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [Research, RAG, Indexing]
    related_skills: [verified-academic-research]
---

# Building Research RAG Indexing Systems

## Trigger
User wants to create a searchable index from research documents (reference lists, PDF collections, academic databases) for efficient retrieval without re-reading all source materials.

## Core Principle
**Index once, query efficiently.** Store only metadata, snippets, tags, and first-5-pages text. Never store full documents.

## Workflow

### Phase 1: Document Ingestion
1. Extract DOIs/references from source document (PDF, DOCX, TXT)
2. Verify each DOI via Crossref API resolution
3. Download PDFs via Unpaywall or publisher APIs where available
4. Extract text from PDFs (first 5 pages) using pymupdf/PyMuPDF
5. Save with structured naming: `PDF_[DOI].pdf`, `TEXT_[DOI].txt`

### Phase 2: Index Building
Create RAG_INDEX.json with minimal structure:
```json
{
  "metadata": {"total": 79, "pdfs": 25, "texts": 25},
  "documents": [{
    "doi": "10.1186/...",
    "title": "...",
    "abstract": "...snippet...",
    "tags": ["Nursing", "PDF-Available"],
    "domain_subscales": {"workload": {"mentions": 5, "confidence": "high"}},
    "files": {"pdf": "PDF_...pdf", "text": "TEXT_...txt"}
  }]
}
```

### Phase 3: Search Interface
```bash
python rag_system.py "search terms"
python rag_system.py --list --tag Workload
python rag_system.py --doc [DOI]
```

### Phase 4: Domain-Specific Mapping
For instrument-specific research (e.g., ENSS):
1. Define subscales and keyword sets per subscale
2. Scan documents for keyword mentions
3. Assign confidence levels (high=3+ mentions, medium=2, low=1)
4. Map studies to subscales without storing full text in index

## File Organization
```
research_collection/
├── RAG_INDEX.json
├── rag_system.py
├── PDF_[DOI].pdf
├── TEXT_[DOI].txt
└── [year]_[title].json
```

## Conciseness Rule
The index must NEVER be larger than the total full-text size of papers it represents.

## Python Gotchas
- User packages may need explicit `sys.path.insert(0, user_site)`
- Windows paths: use raw strings `r'C:\\path'`
- Use `python3` vs `python` consistently per environment