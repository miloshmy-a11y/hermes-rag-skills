# Universal RAG System v4.3.1 - Production Build (Final)

## Context
Built a universal RAG system from 4 sources:
1. ENSS research (79 thesis references) - `~/.hermes/cache/web/ENSS_research/`
2. OUM Books (25 papers + instruments) - `<YOUR_WORK_FOLDER>\sayang\OUM\RESEARCH\bsc\pdf`
3. All OUM documents (625 files) - full recursive scan of `<YOUR_WORK_FOLDER>\sayang\OUM`
4. Mendeley backup (78 PDFs) - `<YOUR_WORK_FOLDER>\mendeley import`

**Final catalog**: 718 documents (after comprehensive deduplication), 199 Crossref-verified DOIs
**Domains**: ENSS (74), OUM_Research (583), Selected Studies (22), Mendeley Import (24), OUM_Books (15)

## Key Improvements Over Standard RAG Pattern

### 1. Never Touch Original Files (Critical for Shared Source Folders)
The OUM research folder at `<YOUR_WORK_FOLDER>\sayang\OUM` contains user documents that must not be modified.
**Fix**: `copy_file_to_rag()` copies every file to `~/.hermes/cache/web/universal_rag/` before processing. Original path preserved in metadata as `original_path`.

### 2. Multi-Path File Resolution
**Problem**: Standard `rag-search-confirmation.md` pattern assumes all files in one folder (`base_dir`). With 4+ source domains, files are in different locations.
**Fix**: Store `base_path` per-document in `files` dict. Confirmation logic reads from `doc['files']['base_path']` not the global catalog path.

### 3. Automatic DOI Verification Pipeline
**Problem**: Previous system relied on pre-verified DOIs in metadata.
**Fix**: `verify_doi()` method makes live Crossref API call to `https://api.crossref.org/works/{DOI}` and extracts verified metadata (title, authors, year, journal). Falls back to filename-derived metadata only if verification fails.

### 4. Comprehensive Multi-Layer Deduplication
**Problem**: 1091 files scanned from OUM + 78 Mendeley files, many duplicates (same content with different filenames across subfolders, same DOI in multiple domains).

**Fix**: Three-layer deduplication with quality-based retention:
1. DOI normalization (case-insensitive) - catches `10.2478/fon-...` vs `10.2478/FON-...`
2. File checksums (full MD5, not partial) - catches identical files with different names
3. Title normalization (case-insensitive, strip punctuation) - catches renamed student files

**Pitfall discovered in production**: Truncated DOIs from PDF text extraction (e.g., `10.1136/bmjopen-2021-` cut off by page boundary) are NOT duplicates of each other - each represents a different paper. These should be resolved to full DOIs via Crossref search of the article title.

### 5. Tag Propagation After DOI Resolution
**Critical pitfall**: When DOI metadata is fetched from Crossref and titles/abstracts are corrected, existing `inferred_tags` may no longer match the study's actual content. Tags MUST be re-inferred from the verified title/abstract. Without this, 12 studies had incorrect "Workload" and "Malaysia" tags that didn't match their actual text content. After re-inference, 5 additional studies gained correct tags.

### 6. Python Environment Gotchas
```bash
# PyMuPDF import fails in default venv - must use system Python
python3 -c "import fitz"  # May fail

# Solution: set PYTHONPATH explicitly
export PYTHONPATH="/c/Users/Milos/AppData/Roaming/Python/Python314/site-packages:$PYTHONPATH"
python3 script.py
```

### 7. Path Normalization
```python
# Problem: Windows paths like <YOUR_WORK_FOLDER>\sayang\OUM cause escaping issues
# Fix: normalize all paths to forward slashes
def _normalize_path(self, path):
    return path.replace('\\', '/').strip()
```

## Instrument Detection Keywords
```
ENSS: "expanded nursing stress scale", "enns"
NSS: "nursing stress scale", "nss"
PSS: "perceived stress scale", "pss"
ERI: "effort-reward imbalance", "eri"
NASA-TLX: "nasa-tlx", "task load index"
MBI: "maslach burnout inventory", "mbi"
NWSQ: "nursing worklife survey", "nwsq"
STAI: "state trait anxiety inventory", "stai"
```

## Domain Classification Heuristics
- Path contains `RESEARCH/bsc/pdf` → OUM_Research
- Filename contains `ENSS` or `NASA-TLX` → instrument detection
- Text mentions "Malaysia" → Malaysia tag
- Text mentions "new graduate" or "novice" → New Graduate tag
- Filename from Mendeley → Mendeley Import domain

## Command Sequence for New Collections
```bash
# 1. Scan folder, copy PDFs, extract text, verify DOIs
python3 universal_rag.py --add-folder "D:/new/papers" "New_Domain"

# 2. Verify imports
python3 universal_rag.py --stats

# 3. Test search
python3 universal_rag.py --search "your topic" --check-fallback

# 4. Run deduplication after imports
python3 deduplicate_catalog_v2.py
python3 final_cleanup.py
```

## Deduplication Scripts (Run After Each Major Import)
| Script | Purpose |
|--------|---------|
| `deduplicate_catalog_v2.py` | DOI (case-insensitive) + checksum deduplication |
| `final_cleanup.py` | Removes edge-case title duplicates |
| `migrate_enss_data.py` | Migrates ENSS subscale data to universal catalog |
| `fix_dois.py` (implicit) | Resolves truncated DOIs to full Crossref DOIs |

## File Inventory (718 docs after dedup)
- `UNIVERSAL_CATALOG.json` (main catalog, ~1MB)
- `universal_rag.py` / `general_rag.py` (search interface, both synced)
- `build_comprehensive_rag.py` (full import script)
- `import_mendeley.py` (Mendeley-specific import with dedup)
- `deduplicate_catalog_v2.py` (multi-layer deduplication)
- `PDF_*.pdf` (711+ copied PDFs, originals untouched)
- `TEXT_*.txt` (668+ extracted text files for confirmation)