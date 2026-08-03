# Full-Text Retrieval Priority Chain (SINGLE SOURCE OF TRUTH)

All RAG skills that acquire full text MUST follow this one chain. Do NOT redefine it
per-skill — edit this file instead. Verified working 2026-08-03.

## Two governing rules (user directive 2026-08-03)

1. **Metadata & citations: Crossref is authoritative — always prefer it.** For any
   DOI→citation/metadata check (title, authors, journal, year, or "does this DOI resolve to
   the paper it claims"), resolve via Crossref (`https://api.crossref.org/works/<DOI>`) and
   trust Crossref over OpenAlex / Semantic Scholar / PubMed / retrieved full-text snippets.
   OpenAlex is the discovery + OA-link + citation-count engine; Crossref is the citation record.
   **Never conclude a DOI is wrong from retrieved full-text content** — the S2/PubMed fallback
   can return a wrong record for old/non-biomedical DOIs. Verify the DOI, not the fallback text.
2. **Abstract / snippet is sufficient for foundational & frequently-cited works.** A complete
   PDF body is NOT required for every entry. For seminal classics cited across many papers
   (e.g. Karasek 1979 demand-control, Selye 1936 GAS, Siegrist ERI, Gray-Toft & Anderson NSS,
   French 2000 ENSS) — and for any entry where only metadata + abstract is obtainable after a
   legitimate OA-tier attempt — store `full_text_status: meta_only` / `abstract_only`, cite via
   Crossref, and move on. Do NOT burn retrieval effort chasing full bodies of widely-cited works.
   Pursue full PDF/HTML body only for (a) the user's own thesis citations that are primary studies
   being read for content, or (b) studies specifically queried for their findings.

## Legal-first ordering
1. **OpenAlex `oa_url`** — gold/diamond/bronze OA (publisher-hosted or repository). Try direct GET; verify the downloaded bytes are a real PDF (`%PDF` magic, >5 KB), NOT a login-wall/landing HTML page.
2. **Unpaywall** (`https://api.unpaywall.org/v2/<DOI>?email=...`) — best OA location (often PMC, arXiv, institutional repo).
3. **Europe PMC / PMC** (`https://europepmc.org/article/MED/<pmid>`) — biomedical OA full text (HTML or PDF).
4. **CORE / DOAJ** — OA aggregators for non-biomedical.
5. **paper-fetch** (`scripts/fetch.py --batch`) — wraps Unpaywall → S2 → arXiv → PMC → (Sci-Hub only if `PAPER_FETCH_NO_SCIHUB` is unset and user approved).
6. **Semantic Scholar paper page** (`https://www.semanticscholar.org/paper/<paperId>`) — bot-accessible; extract the page HTML as **full text markdown** when no PDF is obtainable. Works for paywalled publisher papers that block direct PDF download (Wiley/Elsevier/SAGE 403 on bot GET). Store as `.md` in `SOURCE_TEXT/`, set `full_text_status: s2_page_extracted`.
7. **PubMed** (`https://pubmed.ncbi.nlm.nih.gov/<pmid>/`) — extractable full text for papers S2 lacks.
8. **web_search + web_extract** on alternate hosts (ResearchGate, institutional repo, preprint) as last resort.

## Critical rules
- **Never** present a login-wall/landing page as "full text." After any download, assert the bytes are a real PDF or extracted-HTML, or mark `full_text_status: pending`.
- **Sci-Hub**: EXCLUDED. Direct tests (2026-08) confirm it is non-functional (anti-bot/CAPTCHA walls, 403s from mirrors). Do not rely on it; the legal OA tiers + S2-page HTML + PubMed cover all cases encountered.
- **Metadata-only entries are never dropped** — flag `[META]`, keep the citation, attempt retrieval later.
- **Two verification checks, independently**:
  1. **DOI verification** — DOI resolves via Crossref; title/authors/year match.
  2. **Content/population verification** — full text confirms the studied population matches the query intent (e.g. Malaysian nurses), not just the topic keywords.

## Why one file
Three skills previously defined this chain three different ways and drifted. This file is
the only place the order lives. `general-purpose-rag`, `rag-literature-build`, and
`verified-academic-research` all point here.
