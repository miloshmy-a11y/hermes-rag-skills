# Full-Text Acquisition Pipeline v4.5.3

## Priority Chain for Full-Text Retrieval

When a study needs to be added to the RAG catalog, follow this priority chain:

1. **Crossref oa_url** — Most reliable for verified DOIs
   ```python
   url = f"https://api.crossref.org/works/{doi}"
   item = requests.get(url).json()['message']
   oa_url = item.get('oa_url', '')  # Direct PDF link if open access
   ```

2. **Europe PMC** — Good coverage for NIH/UKRI funded papers
   ```python
   url = f"https://www.ebi.ac.uk/europepmc/webservices/rest/search?query={doi}&format=json"
   ```

3. **Unpaywall** — Aggregates repository-hosted PDFs
   ```python
   url = f"https://api.unpaywall.org/v2/{doi}?email=YOUR_EMAIL"
   ```

4. **Defuddle (publisher HTML)** — Clean article text when PDF not available
   ```bash
   npx defuddle parse "<publisher_url>" --markdown
   ```
   ✅ Works on: opennursingjournal.com, frontiersin.org, mdpi.com, plos.org
   ❌ Blocked by: pmc.ncbi.nlm.nih.gov (Cloudflare), link.springer.com

5. **Defuddle (PMC fallback)** — When publisher blocks defuddle, try PMC
   ```bash
   # 1. Find PMCID via Europe PMC API
   # 2. Use defuddle on the PMC article URL
   ```

## Grey Alternatives (Last Resort)

For non-commercial personal use only, when no legal OA source is available:
- Google Scholar → institutional repository mirrors
- Author's ResearchGate page (if they uploaded it)
- Preprint servers (arXiv, bioRxiv, medRxiv)
- Conference proceedings repositories

**Always prefer legal sources.** Only use grey alternatives as a last resort.

## Defuddle Integration Notes

**Problem:** PMC and Springer block defuddle with Cloudflare/browser checks.

**Solution:** Implement fallback chain:
1. Try defuddle → if output < 500 chars → blocked
2. Fall back to web_extract for full HTML text
3. For PMC specifically, use Europe PMC API to find repository PDF URLs

**File handling:**
- Always save extracted text as `TEXT_<sanitized_doi>.txt`
- Verify defuddle output is real content (not "Checking your browser...")
- For PMC HTML: 77KB raw → ~1KB defuddle (if not blocked) → web_extract fallback if blocked

## Self-Correction Triggers

During searches, watch for these patterns and auto-fix:

| Pattern | Trigger | Action |
|---------|---------|--------|
| `Authors: []` or placeholder dots | Empty author list | Query Crossref API immediately |
| `10.6007/...`, `10.1155/2024`, `10.1155/nuf` | Non-resolving placeholder DOIs | Flag as `local_only`, verify manually |
| `abstract_preview: "N/A"` | Missing abstract | Extract from TEXT_ file first paragraph |
| `instrument: ["Not specified"]` | Missing instrument | Scan TEXT_ file for scale names |
| Defuddle output < 500 chars | Cloudflare blocking | Fall back to web_extract |