# Full-text retrieval for indexed-but-PDF-less references

Goal: give every study in the catalog a local PDF when one is legitimately open-access.
NEVER use Sci-Hub / LibGen / paywall-circumvention. Legal sources only.

## The working pipeline (validated in a live session)

1. **Unpaywall** — authoritative OA locator.
   `GET https://api.unpaywall.org/v2/<DOI>?email=YOUR_EMAIL`
   - Requires a real-looking `email` query param. A transient `HTTP 422` can happen on the
     first hit; just retry.
   - Read `is_oa` (bool) and `best_oa_location.url_for_pdf` (the direct PDF URL) or `best_oa_location.url`.
   - Also read `pmcid` — PMC-hosted articles can be fetched from PMC even when the publisher URL 403s.

2. **Download with a browser User-Agent** — this single change defeats most `403 Forbidden`
   errors that a bare `urllib` UA gets. Use:
   `Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36`
   and `Accept: application/pdf,*/*`.

3. **Validate the bytes** before saving:
   - must start with `%PDF-`
   - must be > 5 KB (otherwise it is an HTML landing/error page mislabeled as PDF)
   - If invalid, DO NOT save it as a PDF (you'll just create a dangling/garbage entry).

4. **Fallback chain per DOI** (when the Unpaywall PDF URL returns HTML/403):
   - PMC: `https://www.ncbi.nlm.nih.gov/pmc/articles/<PMCID>/pdf`
   - BMC/Springer: `https://link.springer.com/content/pdf/<DOI>.pdf`
   - MDPI: `https://www.mdpi.com/<journal>/<article>/<article>.pdf`
     (split DOI on `/`: parts[1]=journal, parts[2]=article; guard `len(parts)>=3`)
   - PLOS: `https://journals.plos.org/plosone/article/file?id=<DOI>&type=printable`
   - Try each candidate; keep the first that returns a real PDF.

## Realistic success rate
In a live run over 70 thesis-cited DOIs: 13 downloaded, 7 genuinely paywalled (no OA),
50 returned HTML/blocked even though `is_oa=true`. The 50 need a real browser session
(cookie/session) — programmatic urllib cannot get them. Record those with `full_text_pdf:''`
and the source still on D:\; do NOT claim they were fetched.

## Commands
- `python3 scripts/download_fulltext.py` — query Unpaywall for every Thesis_References entry
  lacking a PDF, download OA PDFs, write paths into the catalog, log to `FULLTEXT_DOWNLOAD_LOG.json`.
- Re-run only the failures: the script re-queries Unpaywall for logged `retry_fail` entries and
  applies the fallback chain. (The MDPI URL split must guard against short DOIs — see above.)
- Always `cp UNIVERSAL_CATALOG.json backups/CAT_before_download_<ts>.json` first.

## Gotchas that burned a session
- Reading subprocess stdout as text on a binary PDF raises `UnicodeDecodeError` — capture to a
  file (`pdftotext in.pdf out.txt`) instead of `capture_output=True, text=True`.
- A malformed `find` loop that includes the directory itself (no `-type f`) reports every file as
  "BAD" — always use `find <dir> -type f -iname "*.pdf"`.
- Mendeley "PDFs" can be gzip (`\x1f\x8b`); `gzip.decompress` and recheck for `%PDF` before skipping.
