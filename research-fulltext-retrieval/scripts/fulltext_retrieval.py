#!/usr/bin/env python3
"""
Legal Full-Text Retrieval Pipeline
Run: python3 fulltext_retrieval.py <DOI>
Uses only open-access sources: Unpaywall, PMC, CORE, DOAJ.
NEVER uses Sci-Hub, LibGen, or paywall circumvention.
"""
import json
import os
import re
import urllib.request
import fitz  # PyMuPDF

EMAIL = "hermes-rag@local"
PDF_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "PDFs")
os.makedirs(PDF_DIR, exist_ok=True)


def sanitize_doi(doi):
    return re.sub(r'[^\w.\-]', '_', doi)


def try_unpaywall(doi):
    """Check Unpaywall API for OA PDF."""
    url = f"https://api.unpaywall.org/v2/{doi}?email={EMAIL}"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'RAG-System/4.5.2'})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())

        # Try ALL locations, not just best_oa_location
        for loc in data.get('oa_locations', []):
            pdf_url = loc.get('url_for_pdf') or loc.get('url')
            if pdf_url:
                return {
                    'source': 'unpaywall',
                    'oa_status': data.get('oa_status'),
                    'pdf_url': pdf_url,
                    'host_type': loc.get('host_type'),
                }
        return None
    except Exception as e:
        print(f"  Unpaywall error: {e}")
        return None


def try_pmc(doi):
    """Check PubMed Central for PDF via DOI conversion."""
    url = f"https://www.ncbi.nlm.nih.gov/pmc/utils/idconv/v1.0/?tool=rag-system&email={EMAIL}&ids={doi}"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'RAG-System/4.5.2'})
        with urllib.request.urlopen(req, timeout=15) as resp:
            content = resp.read().decode('utf-8')

        pmcid_match = re.search(r'PMCID="([^"]+)"', content)
        if pmcid_match:
            pmcid = pmcid_match.group(1)
            return {
                'source': 'pmc',
                'pmcid': pmcid,
                'pdf_url': f'https://www.ncbi.nlm.nih.gov/pmc/articles/{pmcid}/pdf/',
            }
        return None
    except Exception as e:
        print(f"  PMC error: {e}")
        return None


def try_core(doi):
    """Check CORE repository database."""
    url = f"https://api.core.ac.uk/works/?doi={doi}"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'RAG-System/4.5.2'})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())

        for item in data.get('results', []):
            pdf_url = item.get('downloadUrl') or item.get('pdfUrl')
            if pdf_url and pdf_url.startswith('http'):
                return {
                    'source': 'core',
                    'pdf_url': pdf_url,
                }
        return None
    except Exception:
        return None


def try_doaj(doi):
    """Check DOAJ for open-access journal articles."""
    url = f"https://doaj.org/api/v2/search/articles/{doi}"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'RAG-System/4.5.2'})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())

        if data.get('count', 0) > 0:
            for item in data.get('results', []):
                pdf_url = item.get('external_url')
                if pdf_url:
                    return {'source': 'doaj', 'pdf_url': pdf_url}
        return None
    except Exception:
        return None


def download_pdf(url, doi):
    """Download PDF and validate it's actually a PDF."""
    safe = sanitize_doi(doi)
    pdf_path = os.path.join(PDF_DIR, f"PDF_{safe}.pdf")

    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'RAG-System/4.5.2'})
        with urllib.request.urlopen(req, timeout=60) as resp:
            content = resp.read()
            if not content[:5] == b'%PDF-':
                print(f"  ⚠️ Not a PDF (starts with {content[:20]})")
                return None
            with open(pdf_path, 'wb') as f:
                f.write(content)
            print(f"  ✅ Downloaded: {len(content)} bytes")
            return pdf_path
    except Exception as e:
        print(f"  ❌ Download failed: {e}")
        return None


def extract_text(pdf_path, doi):
    """Extract text from PDF using PyMuPDF."""
    safe = sanitize_doi(doi)
    parent = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    text_path = os.path.join(parent, f"TEXT_{safe}.txt")

    doc = fitz.open(pdf_path)
    full_text = ""
    for page in doc:
        full_text += page.get_text()
    doc.close()

    with open(text_path, 'w', encoding='utf-8') as f:
        f.write(full_text)

    print(f"  ✅ Text extracted: {len(full_text)} chars → {text_path}")
    return text_path


def retrieve_fulltext(doi):
    """Run the legal retrieval pipeline."""
    print(f"\n=== Full-text retrieval for {doi} ===\n")

    sources = [
        ("Unpaywall", try_unpaywall),
        ("PMC", try_pmc),
        ("CORE", try_core),
        ("DOAJ", try_doaj),
    ]

    for name, func in sources:
        print(f"  Checking {name}...")
        result = func(doi)
        if result and result.get('pdf_url'):
            print(f"  ✅ Found via {name}")
            pdf_path = download_pdf(result['pdf_url'], doi)
            if pdf_path:
                extract_text(pdf_path, doi)
                return {'status': 'FOUND', 'source': name, 'pdf_path': pdf_path}

    return {
        'status': 'NOT_ACCESSIBLE',
        'note': 'FULL TEXT NOT ACCESSIBLE — abstract/citation only. Checked: Unpaywall, PMC, CORE, DOAJ.'
    }


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python3 fulltext_retrieval.py <DOI>")
        sys.exit(1)

    doi = sys.argv[1]
    result = retrieve_fulltext(doi)
    print(f"\n=== Result ===")
    print(json.dumps(result, indent=2))
