#!/usr/bin/env python3
"""
Full-Text Acquisition Script v4.5.3

Priority chain for full-text acquisition (fallback for when PDFs aren't pre-indexed):
1. Crossref oa_url → best open access PDF
2. Europe PMC → repository PDF/HTML
3. Unpaywall → repository or publisher OA
4. Publisher page → defuddle HTML extraction (removes boilerplate)
5. Last resort: web_search → manual identification

Usage:
    python3 acquire_fulltext.py "<DOI>"
    python3 acquire_fulltext.py "<DOI>" --defuddle-only
    python3 acquire_fulltext.py "<DOI>" --fallback-search

Grey alternatives are acceptable as last resort for non-commercial personal use.
Always prefer legal open access sources (Crossref, Europe PMC, Unpaywall).
"""
import urllib.request
import urllib.parse
import json
import re
import os
import subprocess
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PDF_DIR = os.path.join(BASE_DIR, "PDFs")
TEXT_DIR = BASE_DIR

# Publishers where defuddle works (no Cloudflare/Sci-Hub blocks)
DEFUDLE_FRIENDLY = [
    "opennursingjournal.com",
    "www.hindawi.com",
    "www.frontiersin.org",
    "www.mdpi.com",
    "journals.plos.org",
    "www.sciencedirect.com",  # sometimes works
]

# Publishers blocked by defuddle
DEFUDLE_BLOCKED = [
    "pmc.ncbi.nlm.nih.gov",
    "www.ncbi.nlm.nih.gov",
    "link.springer.com",
    "www.nature.com",
    "onlinelibrary.wiley.com",
]


def doi_to_filename(doi: str) -> str:
    """Convert DOI to safe filename."""
    return "DOI_" + re.sub(r'[^\w.\-]', '_', doi)


def resolve_oa_url(doi: str) -> tuple[str, str] | None:
    """Resolve open-access URL using priority chain.
    
    Returns (url, method) or None.
    """
    import urllib.parse
    
    # 1. Crossref oa-url (most reliable for verified DOIs)
    try:
        url = f"https://api.crossref.org/works/{doi}"
        req = urllib.request.Request(url, headers={'User-Agent': 'RAG-System/4.5'})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
        item = data.get('message', {})
        
        oa_url = item.get('oa_url', '')
        if oa_url and ('pdf' in oa_url.lower() or 'download' in oa_url.lower()):
            return oa_url, "Crossref OA (PDF)"
        
        # Check link field for PDF
        for link in item.get('link', []):
            if 'pdf' in link.get('content-type', '').lower() or 'pdf' in link.get('URL', '').lower():
                return link.get('URL'), "Crossref PDF link"
        
        # Any oa_url counts
        if oa_url:
            return oa_url, "Crossref OA URL"
    except Exception as e:
        print(f"  Crossref failed: {e}")
    
    # 2. Europe PMC
    try:
        encoded_doi = urllib.parse.quote(doi)
        url = f"https://www.ebi.ac.uk/europepmc/webservices/rest/search?query={encoded_doi}&format=json"
        req = urllib.request.Request(url, headers={'User-Agent': 'RAG-System/4.5'})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
        
        for hit in data.get('resultList', {}).get('result', []):
            if hit.get('isOpenAccess') == 'Y':
                ft_urls = hit.get('fullTextUrlList', {}).get('fullTextUrl', [])
                if isinstance(ft_urls, dict):
                    ft_urls = [ft_urls]
                for link in ft_urls:
                    if 'pdf' in link.get('url', '').lower():
                        return link.get('url'), "Europe PMC (PDF)"
                # Fallback to first URL
                if ft_urls:
                    return ft_urls[0].get('url'), f"Europe PMC ({ft_urls[0].get('documentStyle', 'unknown')})"
    except Exception as e:
        print(f"  Europe PMC failed: {e}")
    
    # 3. Unpaywall
    try:
        url = f"https://api.unpaywall.org/v2/{doi}?email=rag@system.local"
        req = urllib.request.Request(url, headers={'User-Agent': 'RAG-System/4.5'})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
        
        if data.get('oa_status') in ('green', 'gold', 'hyBrid'):
            best = data.get('best_oa_location', {})
            if best:
                return best.get('url'), f"Unpaywall ({data.get('oa_status', 'OA')})"
            
            # Try first OA location
            for loc in data.get('oa_locations', []):
                if loc.get('url'):
                    return loc.get('url'), f"Unpaywall ({loc.get('host_type', 'unknown')})"
    except Exception as e:
        print(f"  Unpaywall failed: {e}")
    
    return None


def download_pdf(url: str, doi: str) -> str | None:
    """Download PDF from URL, return path or None."""
    os.makedirs(PDF_DIR, exist_ok=True)
    safe_name = doi_to_filename(doi)
    pdf_path = os.path.join(PDF_DIR, f"{safe_name}.pdf")
    
    try:
        print(f"  Downloading PDF from {url[:60]}...")
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=60) as resp:
            content = resp.read()
            with open(pdf_path, 'wb') as f:
                f.write(content)
        
        # Verify it's a real PDF
        if content[:4] == b'%PDF' or b'pdf' in content[:20]:
            print(f"  ✅ PDF saved: {os.path.getsize(pdf_path)} bytes")
            return pdf_path
        else:
            print(f"  ⚠️ Not a real PDF (got {len(content)} bytes)")
            return None
    except Exception as e:
        print(f"  ❌ Download failed: {e}")
        return None


def extract_text_from_pdf(pdf_path: str, doi: str) -> str:
    """Extract text from PDF using PyMuPDF."""
    try:
        import fitz
    except ImportError:
        print("  ⚠️ PyMuPDF not available, using fallback")
        return ""
    
    safe_name = doi_to_filename(doi)
    text_path = os.path.join(BASE_DIR, f"TEXT_{safe_name}.txt")
    
    doc = fitz.open(pdf_path)
    full_text = ""
    for page_num in range(len(doc)):
        full_text += doc[page_num].get_text()
    doc.close()
    
    with open(text_path, 'w', encoding='utf-8') as f:
        f.write(full_text)
    
    print(f"  ✅ Text extracted: {len(full_text)} chars, {len(doc)} pages → {os.path.basename(text_path)}")
    return full_text


def extract_with_defuddle(url: str, doi: str) -> str | None:
    """Use defuddle to extract clean article text from HTML."""
    safe_name = doi_to_filename(doi)
    text_path = os.path.join(BASE_DIR, f"TEXT_{safe_name}.txt")
    
    try:
        cmd = ["npx", "defuddle", "parse", url, "--markdown"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30, shell=True)
        
        if result.returncode == 0 and len(result.stdout) > 100:
            clean_text = result.stdout
            
            with open(text_path, 'w', encoding='utf-8') as f:
                f.write(clean_text)
            
            print(f"  ✅ Clean text via defuddle: {len(clean_text)} chars → {os.path.basename(text_path)}")
            return clean_text
        else:
            print(f"  ⚠️ Defuddle failed ({result.returncode}), trying fallback parser")
            return None
    except Exception as e:
        print(f"  ❌ Defuddle error: {e}")
        return None


def acquire_fulltext(doi: str, fallback_search: bool = False) -> dict | None:
    """Main acquisition function with fallback chain."""
    
    print(f"\n=== Acquiring full text for DOI: {doi} ===")
    
    # Step 1: Resolve OA URL
    result = resolve_oa_url(doi)
    
    if result:
        url, method = result
        print(f"  📍 Found via {method}: {url[:80]}")
        
        # Step 2: Try PDF download
        pdf_path = download_pdf(url, doi)
        if pdf_path:
            text = extract_text_from_pdf(pdf_path, doi)
            if text:
                return {
                    "doi": doi,
                    "source": method,
                    "pdf_path": pdf_path,
                    "text_path": os.path.join(BASE_DIR, f"TEXT_{doi_to_filename(doi)}.txt"),
                    "text_length": len(text),
                    "method": "pdf_download"
                }
    
    # Step 3: Try defuddle on publisher page
    print(f"  🔄 Trying publisher page with defuddle...")
    try:
        req = urllib.request.Request(f"https://doi.org/{doi}", 
                                     headers={'User-Agent': 'RAG-System/4.5', 'Accept': 'text/html'})
        with urllib.request.urlopen(req, timeout=15) as resp:
            final_url = resp.url
            print(f"  Publisher URL: {final_url}")
            
            defuddle_result = extract_with_defuddle(final_url, doi)
            if defuddle_result and len(defuddle_result) > 500:
                return {
                    "doi": doi,
                    "source": f"Publisher page (defuddle)",
                    "text_path": os.path.join(BASE_DIR, f"TEXT_{doi_to_filename(doi)}.txt"),
                    "method": "defuddle_html"
                }
    except Exception as e:
        print(f"  DOI resolution failed: {e}")
    
    # Step 3b: Try PMC HTML extraction (for PubMed Central articles)
    print(f"  🔄 Trying PMC HTML fallback...")
    try:
        encoded_doi = urllib.parse.quote(doi)
        pmc_url = f"https://www.ebi.ac.uk/europepmc/webservices/rest/search?query={encoded_doi}&format=json"
        req = urllib.request.Request(pmc_url, headers={'User-Agent': 'RAG-System/4.5'})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
        
        for hit in data.get('resultList', {}).get('result', []):
            pmc_id = hit.get('pmcid')
            if pmc_id:
                pmc_html_url = f"https://www.ncbi.nlm.nih.gov/pmc/articles/{pmc_id}/"
                print(f"  PMC URL: {pmc_html_url}")
                
                # Try defuddle on PMC
                defuddle_result = extract_with_defuddle(pmc_html_url, doi)
                if defuddle_result and len(defuddle_result) > 500:
                    return {
                        "doi": doi,
                        "source": f"PMC HTML (defuddle)",
                        "text_path": os.path.join(BASE_DIR, f"TEXT_{doi_to_filename(doi)}.txt"),
                        "method": "defuddle_html"
                    }
                break
    except Exception as e:
        print(f"  PMC fallback failed: {e}")
    
    # Step 4: Last resort - web search (if enabled)
    if fallback_search:
        print(f"  ⏳ Web search not implemented in script mode")
        print(f"  Hint: Use web_search with query: '{doi}' to find alternative sources")
    
    return None


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 acquire_fulltext.py <DOI> [--fallback-search]")
        sys.exit(1)
    
    doi = sys.argv[1]
    fallback = "--fallback-search" in sys.argv
    
    result = acquire_fulltext(doi, fallback_search=fallback)
    if result:
        print(f"\n✅ Full text acquired:")
        print(json.dumps(result, indent=2))
    else:
        print(f"\n❌ Could not acquire full text for {doi}")
        print("Options:")
        print("  1. Check if a PDF is already in the catalog")
        print("  2. Try manual download from publisher")
        print("  3. Use web_search to find alternative sources")
