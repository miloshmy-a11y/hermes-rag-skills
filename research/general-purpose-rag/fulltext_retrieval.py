#!/usr/bin/env python3
"""
Legal Full-Text Retrieval Pipeline v4.5.3
==========================================
Uses only legal, open-access sources for PDF/text retrieval:

1. Unpaywall API — free open-access PDFs
2. PubMed Central (PMC) — NIH-funded and deposited papers
3. CORE API — repository-hosted copies
4. Journal DOAJ listing — fully open-access journals
5. Corresponding author's institutional page / ResearchGate (author-uploaded only)

NEVER uses: Sci-Hub, LibGen, paywall circumvention, header spoofing, proxies, or mirror sites.

Usage:
    python3 fulltext_retrieval.py <DOI>

Returns: Path to downloaded full text, or "FULL TEXT NOT ACCESSIBLE — abstract/citation only"
"""
import json
import os
import re
import urllib.request
import urllib.parse
import urllib.error
import fitz  # PyMuPDF for PDF text extraction
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PDF_DIR = os.path.join(BASE_DIR, "PDFs")
TEXT_DIR = os.path.join(BASE_DIR, "Texts")
EMAIL = "hermes-rag@local"  # Required by Unpaywall API

os.makedirs(PDF_DIR, exist_ok=True)
os.makedirs(TEXT_DIR, exist_ok=True)


def sanitize_doi(doi: str) -> str:
    """Convert DOI to safe filename."""
    return re.sub(r'[^\w.\-]', '_', doi)


def get_filename(doi: str, ext: str = "pdf") -> str:
    """Generate filename for DOI."""
    safe = sanitize_doi(doi)
    return os.path.join(BASE_DIR, f"PDF_{safe}.{ext}")


def try_unpaywall(doi: str) -> dict | None:
    """Step 1: Check Unpaywall API for legal open-access PDF."""
    url = f"https://api.unpaywall.org/v2/{doi}?email={EMAIL}"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'RAG-System/4.5.2'})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
        
        if data.get('oa_status') in ('gold', 'green', 'hybrid', 'libre'):
            # Try ALL locations, not just the "best" one
            for loc in data.get('oa_locations', []):
                pdf_url = loc.get('url_for_pdf')
                if pdf_url:
                    return {
                        'source': 'unpaywall',
                        'oa_status': data['oa_status'],
                        'pdf_url': pdf_url,
                        'host_type': loc.get('host_type'),
                        'url': loc.get('url')
                    }
            # Also try best_oa_location
            location = data.get('best_oa_location') or {}
            pdf_url = location.get('url')
            if pdf_url:
                return {
                    'source': 'unpaywall',
                    'oa_status': data['oa_status'],
                    'pdf_url': pdf_url,
                    'host_type': location.get('host_type'),
                    'url': location.get('url')
                }
        
        return None
    except Exception as e:
        print(f"  Unpaywall error: {e}")
        return None


def try_pmc(doi: str) -> dict | None:
    """Step 2: Check PubMed Central for PDF."""
    # First try to find PMCID via Crossref
    url = f"https://api.crossref.org/works/{doi}"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'RAG-System/4.5.2'})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
        
        item = data['message']
        
        # Check for PMC links
        for link in item.get('link', []):
            if 'ncbi.nlm.nih.gov/pmc' in link.get('URL', '').lower():
                pmc_url = link['URL']
                return {
                    'source': 'pmc',
                    'pdf_url': pmc_url,
                    'url': pmc_url
                }
        
        # Try searching PMC directly with DOI
        search_url = f"https://www.ncbi.nlm.nih.gov/pmc/utils/idconv/v1.0/?tool=rag-system&email={EMAIL}&ids={doi}"
        req = urllib.request.Request(search_url, headers={'User-Agent': 'RAG-System/4.5.2'})
        with urllib.request.urlopen(req, timeout=15) as resp:
            content = resp.read().decode('utf-8')
        
        if 'PMCID' in content:
            pmcid_match = re.search(r'PMCID="([^"]+)"', content)
            if pmcid_match:
                pmcid = pmcid_match.group(1)
                pdf_url = f"https://www.ncbi.nlm.nih.gov/pmc/articles/{pmcid}/pdf/"
                return {
                    'source': 'pmc',
                    'pmcid': pmcid,
                    'pdf_url': pdf_url,
                    'url': pdf_url
                }
        
        return None
    except Exception as e:
        print(f"  PMC error: {e}")
        return None


def try_core(doi: str, api_key: str = "") -> dict | None:
    """Step 3: Search CORE repository database."""
    url = f"https://api.core.ac.uk/works/?doi={doi}"
    if api_key:
        url += f"&apiKey={api_key}"
    
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'RAG-System/4.5.2'})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
        
        for item in data.get('results', []):
            pdf_url = item.get('downloadUrl') or item.get('pdfUrl')
            if pdf_url and pdf_url.startswith('http'):
                source = item.get('source', {}).get('title', 'repository')
                return {
                    'source': f'core:{source}',
                    'pdf_url': pdf_url,
                    'url': pdf_url
                }
        
        return None
    except Exception as e:
        print(f"  CORE error: {e}")
        return None


def try_doaj(doi: str) -> dict | None:
    """Step 4: Check DOAJ (Directory of Open Access Journals)."""
    url = f"https://doaj.org/api/v2/search/articles/{doi}"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'RAG-System/4.5.2'})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
        
        if data.get('count', 0) > 0:
            for item in data.get('results', []):
                pdf_url = item.get('external_url') or item.get('pdf_url')
                if pdf_url:
                    return {
                        'source': 'doaj',
                        'pdf_url': pdf_url,
                        'url': pdf_url
                    }
        
        return None
    except Exception as e:
        print(f"  DOAJ error: {e}")
        return None


def download_pdf(url: str, doi: str) -> str | None:
    """Download PDF from a legal open-access URL."""
    pdf_path = get_filename(doi, "pdf")
    
    try:
        print(f"  Downloading from: {url[:80]}...")
        req = urllib.request.Request(url, headers={
            'User-Agent': 'RAG-System/4.5.2 (Legal Open Access Retrieval)'
        })
        with urllib.request.urlopen(req, timeout=60) as resp:
            content = resp.read()
            
            # Verify it's actually a PDF
            if not content[:5] == b'%PDF-':
                print(f"  ⚠️ Content doesn't appear to be a PDF")
                return None
            
            with open(pdf_path, 'wb') as f:
                f.write(content)
            
            size = len(content)
            print(f"  ✅ Downloaded: {size} bytes")
            return pdf_path
    except Exception as e:
        print(f"  ❌ Download failed: {e}")
        return None


def extract_text_from_pdf(pdf_path: str, doi: str) -> str:
    """Extract text from PDF using PyMuPDF."""
    safe_doi = sanitize_doi(doi)
    text_path = os.path.join(BASE_DIR, f"TEXT_{safe_doi}.txt")
    
    doc = fitz.open(pdf_path)
    full_text = ""
    for page_num in range(len(doc)):
        full_text += doc[page_num].get_text()
    doc.close()
    
    with open(text_path, 'w', encoding='utf-8') as f:
        f.write(full_text)
    
    print(f"  ✅ Text extracted: {len(full_text)} chars")
    return text_path


def retrieve_fulltext(doi: str, max_sources: int = 4) -> dict:
    """Run the full legal retrieval pipeline.
    
    Returns:
        dict with: status, source, pdf_path, text_path, note
        - If success: {'status': 'FOUND', 'source': ..., 'pdf_path': ..., 'text_path': ...}
        - If not found: {'status': 'NOT_ACCESSIBLE', 'note': '...'}
    """
    print(f"\n=== Full-text retrieval for {doi} ===\n")
    
    # Try each source in order
    sources = [
        ("Unpaywall", lambda: try_unpaywall(doi)),
        ("PubMed Central", lambda: try_pmc(doi)),
        ("CORE", lambda: try_core(doi)),
        ("DOAJ", lambda: try_doaj(doi)),
    ]
    
    for source_name, try_func in sources[:max_sources]:
        print(f"  Checking {source_name}...")
        result = try_func()
        if result and result.get('pdf_url'):
            print(f"  ✅ Found via {source_name}: {result['source']}")
            
            # Download PDF
            pdf_path = download_pdf(result['pdf_url'], doi)
            if pdf_path:
                # Extract text
                text_path = extract_text_from_pdf(pdf_path, doi)
                return {
                    'status': 'FOUND',
                    'source': result['source'],
                    'pdf_path': pdf_path,
                    'text_path': text_path,
                    'doi': doi
                }
    
    # If nothing found
    return {
        'status': 'NOT_ACCESSIBLE',
        'source': None,
        'pdf_path': None,
        'text_path': None,
        'doi': doi,
        'note': 'FULL TEXT NOT ACCESSIBLE — abstract/citation only. Checked: Unpaywall, PMC, CORE, DOAJ.'
    }


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python3 fulltext_retrieval.py <DOI>")
        print("Example: python3 fulltext_retrieval.py 10.1038/s41598-025-05253-0")
        sys.exit(1)
    
    doi = sys.argv[1]
    result = retrieve_fulltext(doi)
    
    print(f"\n=== Result ===")
    print(json.dumps(result, indent=2))
