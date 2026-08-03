---
name: research-fulltext-retrieval
description: "Legal OA full-text retrieval — web_extract HTML (primary), Unpaywall/PMC/CORE/DOAJ for PDF."
version: 1.0.0
author: Hermes Agent
tags:
  - research
  - fulltext
  - open-access
parameters:
  - name: doi
    type: string
    description: "DOI of the study to retrieve full text for"
    required: true
---

# Legal Full-Text Retrieval Pipeline

## Overview
Retrieves full-text PDFs for academic studies using **only legal, open-access sources**. Never uses Sci-Hub, LibGen, or paywall circumvention.

## Sources (checked in priority order)
1. **Hermes `web_extract` HTML (PRIMARY — highest success)** — For most DOIs, the publisher's
   HTML article page contains the FULL text (not just abstract). `web_extract` returns clean
   markdown (~50–60k chars = complete paper) for BMC, Springer, Nature, Wiley, MDPI, Hindawi,
   Elsevier, PLOS, Frontiers, SAGE, etc. This retrieved **46/50 failed-PDF DOIs** in one session —
   far better than PDF download, which was bot-blocked or returned HTML landing pages for most.
   Resolve the DOI to its landing URL (Crossref `URL` field or `doi.org` redirect), then `web_extract`.
   Save as `HTML_<sanitized_doi>.md`.
   - **Invocation gotcha**: `web_extract` (via `from hermes_tools import web_extract`) is ONLY
     available inside the `execute_code` sandbox, NOT in terminal Python (terminal raises
     `ModuleNotFoundError: hermes_tools`). Run the fetch loop via `execute_code`, batch 5 URLs/call.
2. **Unpaywall API** — `https://api.unpaywall.org/v2/{DOI}?email=YOUR_EMAIL`. Use to *locate* the OA
   PDF URL (`best_oa_location.url_for_pdf`), but expect many to 403 or serve HTML. Loop ALL
   `oa_locations`, not just `best_oa_location`.
3. **PubMed Central (PMC)** — `https://www.ncbi.nlm.nih.gov/pmc/utils/idconv/v1.0/` → PMCID →
   `https://www.ncbi.nlm.nih.gov/pmc/articles/{PMCID}/pdf/`. Best for NIH/UKRI-funded papers.
4. **CORE / DOAJ** — repository mirrors; lower hit rate, CORE needs API key.

## Usage
```bash
# Run inside execute_code, NOT terminal:
from hermes_tools import web_extract
out = web_extract(urls=[resolved_landing_url], char_limit=60000)
# save out['results'][0]['content'] as HTML_<doi>.md
```

## Key Gotchas
- **web_extract HTML > PDF download.** Direct PDF URLs (BMC `track/pdf`, Wiley, Elsevier) frequently
  return an HTML landing page (200 OK, not 403) instead of a PDF. Detect via `%PDF-` magic + size>5KB.
  When PDF fails, the HTML route via web_extract almost always succeeds.
- **subprocess/defuddle on Windows:** `npx defuddle` from a script needs `shell=True`; but prefer the
  `web_extract` tool (agent environment) over `npx` — it handles Cloudflare/PMC blocking.
- **PDF validation:** Always check file starts with `%PDF-` to avoid redirect pages.
- **Expectation reset:** With web_extract HTML, expect **~63/70** thesis refs to get full text
  (13 PDF + 50 HTML), NOT ~13/70. Only bot-walled sites (BMJ Open, OUP) and subscription instruments
  (JSTOR/APA/Elsevier scale papers) stay metadata-only — those need a real browser session.

## File: references/fulltext_retrieval.md
See references directory for session-specific API details, gotchas, and tested DOIs.
