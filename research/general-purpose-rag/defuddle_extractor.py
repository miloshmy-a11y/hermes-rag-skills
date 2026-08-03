#!/usr/bin/env python3
"""
Defuddle Integration for RAG System v4.5.1

Uses defuddle (npm defuddle) to extract clean article text from web HTML pages.
When PDF downloads fail or HTML pages are the only available source.

Workflow:
1. Try defuddle for clean article extraction (removes nav, ads, citations)
2. If defuddle blocked (Cloudflare/Sci-Hub), fall back to web_extract
3. Save as TEXT_<doi>.txt for full-text search

Usage:
    python3 defuddle_extractor.py "<URL>" <DOI>

Example:
    python3 defuddle_extractor.py "https://opennursingjournal.com/VOLUME/15/PAGE/204/ABSTRACT/" "10.2174/1874434602115010204"
"""
import subprocess
import json
import os
import re
import sys
import urllib.request

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WEB_CACHE = os.path.expandvars(r"C:\Users\Milos\AppData\Local\hermes\cache\web")

# Publishers where defuddle works well (no Cloudflare/Sci-Hub blocks)
DEFUDLE_FRIENDLY_DOMAINS = [
    "opennursingjournal.com",
    "www.hindawi.com",
    "www.frontiersin.org",
    "www.mdpi.com",
    "www.plos.org",
    "journals.plos.org",
]

# Publishers that block automated HTML extraction
DEFUDLE_BLOCKED_DOMAINS = [
    "pmc.ncbi.nlm.nih.gov",
    "www.ncbi.nlm.nih.gov",
    "link.springer.com",
    "www.nature.com",
    "www.sciencedirect.com",
    "onlinelibrary.wiley.com",
]


def is_defuddle_friendly(url: str) -> bool:
    """Check if the URL's domain supports defuddle extraction."""
    blocked = any(domain in url for domain in DEFUDLE_BLOCKED_DOMAINS)
    if blocked:
        return False
    return True


def extract_with_defuddle(url: str, doi: str) -> dict | None:
    """Extract clean article text using defuddle.
    
    Returns dict with DOI, title, content details, or None if failed.
    """
    if not is_defuddle_friendly(url):
        print(f"⚠️ Defuddle likely blocked by {url.split('/')[2]} — use web_extract instead")
        return None
    
    safe_doi = re.sub(r'[^\w.\-]', '_', doi)
    text_filename = f"TEXT_{safe_doi}.txt"
    text_path = os.path.join(BASE_DIR, text_filename)
    
    # Run defuddle to extract clean markdown
    cmd = ["npx", "defuddle", "parse", url, "--markdown"]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30, shell=True)
    
    if result.returncode != 0 or len(result.stdout) < 100:
        print(f"❌ Defuddle failed for {url}: {result.stderr}")
        return None
    
    clean_text = result.stdout
    
    # Also get JSON for metadata extraction
    cmd_json = ["npx", "defuddle", "parse", url, "--json"]
    result_json = subprocess.run(cmd_json, capture_output=True, text=True, timeout=30, shell=True)
    
    metadata = {}
    if result_json.returncode == 0:
        try:
            metadata = json.loads(result_json.stdout)
        except json.JSONDecodeError:
            pass
    
    # Save clean text
    with open(text_path, 'w', encoding='utf-8') as f:
        f.write(clean_text)
    
    print(f"✅ Clean text extracted via defuddle")
    print(f"   DOI: {doi}")
    print(f"   URL: {url}")
    print(f"   Output: {text_filename} ({len(clean_text)} chars)")
    print(f"   Title: {metadata.get('title', 'N/A')[:80]}")
    
    return {
        "doi": doi,
        "title": metadata.get("title", ""),
        "description": metadata.get("description", ""),
        "content_length": len(clean_text),
        "text_file": text_filename,
        "text_path": text_path
    }


def extract_from_pmc_or_publisher(url: str, doi: str) -> dict | None:
    """Fallback: use web_extract to get HTML text, then save as TEXT file."""
    safe_doi = re.sub(r'[^\w.\-]', '_', doi)
    text_filename = f"TEXT_{safe_doi}.txt"
    text_path = os.path.join(BASE_DIR, text_filename)
    
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'RAG-Extractor/1.0'})
        with urllib.request.urlopen(req, timeout=30) as resp:
            html_content = resp.read().decode('utf-8', errors='replace')
        
        # Try defuddle on raw HTML
        cmd = ["npx", "defuddle", "parse", "--markdown"]
        result = subprocess.run(cmd, input=html_content, capture_output=True, 
                              text=True, timeout=30, shell=True)
        
        if result.returncode == 0 and len(result.stdout) > 100:
            clean_text = result.stdout
        else:
            # Fall back to saving raw HTML text
            from html.parser import HTMLParser
            class TextExtractor(HTMLParser):
                def __init__(self):
                    super().__init__()
                    self.text_parts = []
                def handle_data(self, data):
                    self.text_parts.append(data)
                def get_text(self):
                    return '\n'.join(self.text_parts)
            
            parser = TextExtractor()
            parser.feed(html_content)
            clean_text = parser.get_text()
        
        with open(text_path, 'w', encoding='utf-8') as f:
            f.write(clean_text)
        
        print(f"✅ Text extracted (fallback method): {len(clean_text)} chars")
        return {
            "doi": doi,
            "content_length": len(clean_text),
            "text_file": text_filename,
            "text_path": text_path
        }
    except Exception as e:
        print(f"❌ Fallback extraction failed: {e}")
        return None


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 defuddle_extractor.py <URL> <DOI>")
        print("   or: python3 defuddle_extractor.py --fallback <URL> <DOI>")
        sys.exit(1)
    
    if sys.argv[1] == "--fallback":
        url = sys.argv[2]
        doi = sys.argv[3]
        result = extract_from_pmc_or_publisher(url, doi)
    else:
        url = sys.argv[1]
        doi = sys.argv[2]
        result = extract_with_defuddle(url, doi)
        if result is None:
            print("Falling back to web_extract method...")
            result = extract_from_pmc_or_publisher(url, doi)
    
    if result:
        print(json.dumps(result, indent=2))
