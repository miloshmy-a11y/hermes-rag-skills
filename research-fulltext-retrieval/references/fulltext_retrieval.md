# Legal Full-Text Retrieval Pipeline — Session Reference

## What Happened This Session
Implemented full-text retrieval for workload + nurses studies. Discovered that many "web-found" studies don't have accessible PDFs even when Unpaywall claims to have a link — need to iterate through ALL OA locations and validate downloads.

## API Endpoints Used

### 1. Unpaywall
```
GET https://api.unpaywall.org/v2/{DOI}?email={YOUR_EMAIL}
```
Returns `oa_status` and `oa_locations` array with `url_for_pdf` and `host_type`.

**Response structure:**
```json
{
  "oa_status": "gold" | "green" | "hybrid" | "libre",
  "best_oa_location": {...},
  "oa_locations": [
    {"url_for_pdf": "...", "host_type": "publisher" | "repository", ...},
    ...
  ]
}
```

### 2. PubMed Central (PMC)
```
GET https://www.ncbi.nlm.nih.gov/pmc/utils/idconv/v1.0/?tool=rag-system&email={email}&ids={DOI}
```
Returns `PMCID` if article is deposited in PMC. Then PDF is at:
```
https://www.ncbi.nlm.nih.gov/pmc/articles/{PMCID}/pdf/
```

### 3. CORE
```
GET https://api.core.ac.uk/works/?doi={DOI}&apiKey={KEY}
```
Returns repository-hosted copies.

### 4. DOAJ
```
GET https://doaj.org/api/v2/search/articles/{DOI}
```
For fully open-access journals.

## Gotchas & Workarounds

- **Cloudflare blocks npx subprocess on PMC**: When `npx defuddle` or direct requests fail on PMC/NCBI URLs, the page returns "Checking your browser" redirect. Use Hermes `web_extract` tool in the agent environment instead of subprocess for these domains.
- **subprocess.run with npx on Windows**: Must use `shell=True`, otherwise Python can't find the `npx` binary.
- **PDF validation**: Always check downloaded file starts with `b'%PDF-'`. Some servers return HTML redirect pages (200 OK) instead of 403.
- **Sage publisher PDFs via Unpaywall**: Unpaywall may return a Sage-hosted `url_for_pdf` that 403s. Must fall through to the next `oa_location` (often a PMC-hosted copy).
- **Unpaywall best_oa_location is not always best**: Always iterate through ALL `oa_locations` entries and try downloading from each until one works.
- **CORE API 404**: The CORE API endpoint format changed — `https://api.core.ac.uk/works/?doi=...` returns 404 without API key.

## Tested DOIs (this session)

| DOI | Unpaywall Status | Source Found | Download Method |
|-----|-----------------|-------------|-----------------|
| 10.2174/1874434602115010204 | gold | opennursingjournal.com | Direct PDF ✅ |
| 10.1177/23779608241245212 | gold | PMC hosted | Direct PDF ✅ |
| 10.1038/s41598-025-05253-0 | gold | Springer | Direct PDF ✅ |
| 10.1016/j.ijnurstu.2006.07.007 | green | PMC | Direct PDF ✅ |

## Pipeline Flow
```
for source in [unpaywall, pmc, core, doaj]:
    result = source.check(doi)
    if result.pdf_url:
        pdf = download(pdf_url)
        if pdf.starts_with(b'%PDF-'):
            text = extract_text(pdf)  # via PyMuPDF
            return FOUND
return NOT_ACCESSIBLE
```