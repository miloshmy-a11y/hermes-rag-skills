---
name: verified-academic-research
description: "Search academic studies with verified APA citations."
version: 1.1.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [Research, Academic, Citations, APA, Verification]
    related_skills: [arxiv, ocr-and-documents]
---

# Verified Academic Research with APA 7th Edition Citations

## Trigger

User requests finding academic studies with verified citations, extracting summaries/abstracts from original sources, formatting APA 7th edition references with in-text citations, and compiling study metadata (keywords, methodology, findings).

## Workflow

### 1. Search Phase
- Search across multiple academic sources: PubMed, PMC, ResearchGate, Google Scholar, academic journals, institutional repositories
- Use precise search terms including specific scale names (e.g., "Expanded Nursing Stress Scale"), institutional affiliations, and population descriptors
- Cross-reference findings across sources to verify authenticity
- **Dedup candidates** by normalized title + first author + year before verification to reduce redundant API calls
- **Stopping rule**: Stop when N matching studies found across ≥2 independent databases, OR M queries (typically 5-8) yield no new matches

### 2. Verification Phase (Priority Order)
**User Preference Enforcement**: When the user requests research, they require ALL claims to have backup with accurate, verified citations. Every claim presented must be traceable to verified source material — no speculative or secondary summaries. Apply this standard rigorously:

1. **Primary**: DOI confirmed active via Crossref with matching metadata (title, authors, year, abstract)
2. **Secondary**: PMC/EUtils confirmation without Crossref (check NCBI EUtils API for DOI + abstract)
3. **Tertiary**: Multiple independent non-DOI sources agreeing (publisher pages, institutional repositories, citation networks)
4. **Minimum**: Single secondary mention only — mark as "CITED ONLY"

**Verification steps:**
- Extract content directly from original sources using `web_extract` or `read_file`
- Verify that extracted studies match EXACT research criteria (specific scales, institutions, populations)
- **Distinguish between direct instrument usage vs. mention in passing** — only present studies that actually used the requested instrument with the specified population
- Trace back from secondary references to original sources
- **Verify DOIs through systematic Crossref resolution**: Use `curl -s "https://doi.org/{DOI}" -H "Accept: application/json"` or `https://api.crossref.org/works/{DOI}` to confirm DOI is active and returns correct metadata
- **Cross-reference findings**: Verify that the DOI metadata (title, authors, year) matches the extracted content — discrepancies indicate potential issues
- **Verify PMC articles via NCBI EUtils**: For PMC articles, use `https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pmc&id={PMCID}&retmode=json` to confirm details and find associated DOIs
- **For studies without DOIs**: Cross-verify through multiple independent sources (institutional repositories, academic databases, citation networks) before presenting
- **Rate-limit handling**: If Crossref/EUtils returns 429 (rate limit), retry once after a pause. If still limited, mark as "PARTIALLY VERIFIED" and proceed.

### 3. Extraction Phase
For each verified study, extract:
1. Exact abstract/content from the original source
2. Complete bibliographic details (authors, year, title, journal, volume, pages, DOI)
3. Methodology details (sample size, study design, location, time period)
4. Key findings and statistical results
5. Keywords as listed in the original publication

### 3.5. Mandatory DOI/URL Enforcement
**User Preference**: Every reference MUST include either a DOI or an official URL. Never omit the DOI/URL field.
- If a DOI exists, include it as `https://doi.org/XX.XXXX/XXXXXX`
- If no DOI exists (e.g., book chapters, proceedings, reports), include the **most official URL** available:
  - Official publisher page URL
  - Institutional repository URL
  - DOI for the book/proceedings containing the chapter
  - ISBN with publisher website URL
- If neither DOI nor URL can be found, flag the study as "CITED ONLY" and note the limitation transparently — do NOT fabricate or omit the URL
- For studies from edited books (e.g., "OSH Issues: Collection of Case Studies in Malaysia"), cite the publisher and ISBN, plus a link to the publisher or repository where available
- **Grey alternatives for non-commercial use**: When no legal open-access source is available and the user explicitly approved grey alternatives for non-commercial personal use, proceed with repository mirrors, author preprints, and conference proceedings. Clearly label these as "GREY — non-commercial personal use" and prefer the most authoritative source available. Always attempt legal sources first (Crossref oa-url, Unpaywall, Europe PMC, CORE, DOAJ); grey alternatives are a last resort, not a default.

## Full-Text Acquisition Workflow

When a study needs to be added to the RAG catalog from web sources:

1. Verify DOI via Crossref API
2. Try legal OA sources in priority order:
   - **Hermes `web_extract` HTML (PRIMARY):** Resolve DOI → publisher landing URL (Crossref `URL`
     field or `doi.org` redirect), then `web_extract(urls=[url], char_limit=60000)`. The HTML page
     usually holds the FULL paper (~50–60k chars clean markdown), not just the abstract. This is the
     highest-success route — it retrieved 46/50 DOIs that failed PDF download in one session. Run via
     `execute_code` (batch ≤5 URLs/call); `web_extract` is NOT importable from terminal Python.
   - Crossref oa_url → Europe PMC → Unpaywall → CORE → DOAJ (for the actual PDF when available)
3. If PDF unavailable via the above, the web_extract HTML above already covers it — do not fall through
   to defuddle CLI (prefer `web_extract`, which cleans content natively; defuddle CLI hits Cloudflare).
4. If still blocked (BMJ Open, OUP, JSTOR, subscription instruments), note `full_text_html:''` and flag
   as needing a real browser session (the `browser` tool holds cookies/JS) — do NOT claim fetched.
5. Save extracted text, deduplicate, backup, sync to skill folder.

**See `references/fulltext-acquisition-pipeline.md` for the detailed priority chain.**
- **PLATFORM RENDERING WARNING**: Some chat interfaces (including Hermes desktop) automatically convert plain text URLs into clickable hyperlinks with embedded page titles. This is a rendering artifact, NOT a formatting error. When the user sees "title | Publisher" instead of the actual URL, this is the platform's URL preview feature, not a mistake in the reference entry. The underlying text reference IS correctly formatted with the plain text DOI/URL.

## Local Catalog Search (hybrid) + APA output
If the user ALREADY owns a JSON study catalog (rebuilt/audited per `rag-catalog-audit-rebuild`,
e.g. `UNIVERSAL_CATALOG.json` with `documents[]`), do NOT re-fetch the web — search locally.
Use the pattern in `references/local_catalog_hybrid_search.md`: context-aware query expansion →
scored title/abstract/keyword match (filter `doc_type=='study'`) → two-factor verification →
formatted APA 7th reference list. This is the "use" stage after a rebuild.

### 4. Citation Formatting (APA 7th Edition)

**Journal Article Format:**
```
Author, A. A, Author, B. B, & Author, C. C. (Year). Title of the article. *Title of the Journal*, *VolumeNumber*(IssueNumber), page-range. https://doi.org/xx.xxxxx/xxxxx
```

**In-text citation:** `(Author, Year)` or `(Author & Author, Year)`

**Key formatting rules:**
- Author names: Last name, First initial (up to 20 authors)
- Article title: Sentence case (only first word and proper nouns capitalized)
- Journal title: Title case and italics
- Volume number: italics
- Issue number: parentheses, no italics
- DOI: https://doi.org/ prefix
- No retrieval URLs for published works with DOIs

**⚠️ CRITICAL USER PREFERENCE - DO NOT SKIP:** Present DOIs and URLs as PLAIN TEXT. Do NOT:
- Wrap them in markdown link syntax (e.g., [text](url)) — this creates clickable links which the user explicitly rejects
- Wrap them in angle brackets (e.g., <https://doi.org/...>)
- Use citation tool outputs (Zotero, Mendeley, EndNote) that automatically hyperlink titles to URLs/DOIs
- Include any additional titles, descriptions, or notes AFTER the reference entry
- EVER use citation tool exports (which wrap the study title in a clickable hyperlink)

**Always extract metadata directly from Crossref API** (`https://api.crossref.org/works/{DOI}`) rather than copying from citation tool outputs or formatted reference generators. The user has repeatedly emphasized that references must show the actual DOI/URL as plain text, not as a clickable link attached to the title.

### 5. Limitations Handling
- Clearly distinguish between verified full publication details vs. details needing additional verification
- When studies are referenced but not directly accessible, note citation completeness limitations
- Flag when a study used different instruments than requested
- Avoid claims about studies that cannot be fully verified

## Pitfalls

- **Secondary citation trap**: Many papers reference studies without full details. Always trace to original sources.
- **Scale confusion**: NSS vs. ENSS are different instruments. Verify which was actually used.
- **Truncation issues**: Web extracts may be truncated (<5000 chars). Read cached files for complete content.
- **Access barriers**: Scribd, ResearchGate, and publisher sites may require login. Use cached content and search results as fallbacks.
- **False positives**: Search results may mention locations/scales in passing without actual usage. Filter carefully.
- **DOI verification**: Cross-check DOIs against original publication records, not just search snippets.
- **False DOI attribution**: Crossref and search results sometimes return different DOIs for similar titles. Always verify that the DOI metadata (title, authors, year) matches the content you extracted — mismatches indicate the wrong study.
- **DOI verification ≠ content verification** (critical): DOI verification only confirms the citation is real. It says nothing about whether the study's population or findings match your criteria. ALWAYS perform both: (1) DOI resolves with matching metadata, AND (2) content verification confirms the studied population matches (e.g., nurses, not diabetes patients) and the factor is reported as significant (not just a keyword mention). See `references/doi-vs-content-verification.md` for the two-tier verification checklist. A study should only be included if BOTH tiers pass. Never present a study with a caveat like "DOI verified but population doesn't match" — exclude it entirely.
- **Instrument as population**: Studies validating workload instruments (e.g., NASA-TLX) on non-nursing populations will mention "workload" in keywords/titles. Check that the actual study POPULATION is nurses, not just that the instrument is named. NASA-TLX study validated on 51 Type 1 diabetes patients, not nurses.
- **Contextual vs. direct relevance**: Distinguish between studies where workload is a measured finding vs. merely mentioned in background. Present context-only mentions in a clearly separated section, never mixed with findings-level results.
- **Pattern cross-field false positives**: Search patterns matching "significant.*workload" can match across document fields without actual semantic relationship. Always verify co-occurrence is in the same content region, not across fields.
- **False positive triage**: When content verification reveals a false positive, note BOTH the reason AND the source of the false match to refine future search patterns.
- **PMC without DOI**: Some PMC articles lack DOIs. In these cases, use PMCID as the identifier and verify through NCBI EUtils API.
- **Chapter/book vs. journal articles**: Studies appearing in edited books or conference proceedings (like the HUSM case study in an OSH collection) may lack traditional journal DOIs. Verify through ISBN, publisher records, or institutional repositories. Always include publisher name and ISBN in the reference, plus an official URL.
- **Google Books API quota limits**: When Google Books API returns 429 quota exceeded, switch to WorldCat, OpenLibrary, or direct publisher website searches for ISBN verification. See `references/verification-workflow.md` for detailed ISBN verification methods.
- **Cross-referencing requirement**: If a DOI is not found for a study, search Crossref and multiple databases to find an alternative verified source before presenting. Never present unverified bibliographic details.
- **Platform display artifact**: Some chat interfaces and platforms (including Hermes desktop) automatically convert plain text URLs into clickable hyperlinks with embedded page titles. This is a rendering artifact of the chat interface, NOT a formatting error in the reference entry. The reference entry contains the correct plain text DOI/URL. Users should copy and paste URLs directly to verify they resolve correctly. The presence of clickable links does NOT mean the citation is incorrect.
- **Citation tool avoidance**: DO NOT use citation tool exports (Zotero, Mendeley, EndNote, Google Scholar citation generator) — these automatically wrap titles in clickable hyperlinks, which the user explicitly rejects. ALWAYS extract metadata directly from Crossref API and format references manually.
- **ISBN prefix lookup**: See `references/verification-workflow.md` for complete ISBN prefix identification table and publisher lookup methods.
- **Zero-result searches**: When a narrowly-defined query (e.g., "Open University Malaysia AND AI/LLM AND student") returns no hits across ≥2 databases, do NOT expand the query so broadly it yields false positives. Instead, report "NO STUDIES FOUND" explicitly and, only if relevant, present the closest related studies as `Secondary/Supporting Findings` with the exact mismatch noted. See `references/ai-llm-search-patterns.md` for the documented pattern.
- **Do NOT fabricate or INFER literature gaps.** Recommendation engines (`recommend`, `find_similar`) and forward-citation searches surface papers by *seed-matching* — their output is algorithm behavior, not an analytical finding. If a seed set (e.g. ENSS + NSS) returns no papers on a specific local population (e.g. Malaysian nurses), that is the algorithm's match limitation, NOT evidence of a gap. If the user has already stated the ground truth (e.g. "my thesis is the only Malaysian ENSS study I know of"), treat that as authoritative and do NOT contradict it or present seed-matching silence as a discovered gap. State coverage facts (X/Y refs indexed, N with full text) separately from any interpretive claim, and only make gap claims the user themselves frames.
- **Inclusive source scope.** The user's RAG legitimately includes theses, ebooks, instruments, and web/org references (WHO, OECD, HSE, MOH, hospital sites), not just peer-reviewed `study` PDFs. When searching, apply `doc_type` as a filter, never hard-exclude non-`study` types. A reference list the user hands over (even non-DOI web/org docs) must be fully indexed, not treated as junk.

## Output Format

Present findings with this fixed structure for each study:

### Standard Output Template

**Title**: [Exact study title from source]

**Authors**: [Full author list as provided by source]

**Status**: [VERIFIED | PARTIALLY VERIFIED | CITED ONLY]

**Source Verification**:
- DOI: https://doi.org/XX.XXXX/XXXXXX [Verified active via Crossref]
- Abstract extracted from: [Publisher/PMC/Repository name]
- Content verified: [Direct source link or extraction method]

**Abstract/Summary**:
[Verbatim abstract or key content summary from the original source]

**Key Findings**:
- [Statistical result 1]
- [Methodological detail]
- [Main conclusion]

**APA 7th Reference**:
Author, A. A, Author, B. B. (Year). Title of the article. *Title of the Journal*, *VolumeNumber*(IssueNumber), page-range. https://doi.org/xx.xxxxx/xxxxx

**In-text Citation**: (Author, Year) or (Author & Author, Year)

**Keywords**: [Keywords as listed in publication, separated by commas]

**Notes**:
[Any limitations, secondary/fallback findings, or source restrictions noted]

**DOI/URL Requirement**: Every reference MUST include either a DOI or an official URL. For studies without a DOI, verify through publisher pages, institutional repositories, ISBN records, or conference/book chapter URLs. Never present a reference without a traceable URL/DOI.

**Verification Status Indicators**: Prefix each study with a verification status. TWO checks required:
- DOI VERIFIED — DOI resolves via Crossref, metadata (title/authors/year) matches source
- CONTENT VERIFIED — Full text confirms studied population matches AND finding matches criteria
- **✅ VERIFIED** — Both DOI and content verification passed
- **⚠️ PARTIALLY VERIFIED** — Study found through multiple sources but DOI or full text could not be independently confirmed
- **🔍 CITED ONLY** — Study is referenced in other works but original source could not be directly accessed

## Linked Resources

- `references/apa-formatting-quickref.md` — Detailed APA 7th edition formatting examples
- `references/verification-workflow.md` — Multi-step DOI and source verification workflow with tools, false positive patterns, and ISBN prefix lookup tables
- `references/search-discrimination-pattern.md` — Pattern for distinguishing instrument usage vs. mere mention; NSS vs. ENSS confusion avoidance; handling secondary/supporting findings
- `references/ai-llm-search-patterns.md` — Pattern for handling zero-result searches on highly-niche topics (e.g., specific institution + AI/LLM); when to report no studies found and when to present closest related studies as Secondary/Supporting Findings
- `references/rag-document-indexing.md` — Workflow for building lightweight JSON-based RAG index from collections of DOIs; includes DOI extraction from Word docs, PDF text extraction with PyMuPDF, and search query interface pattern
- `references/catalog-deduplication.md` — Multi-layer deduplication strategy for research RAG catalogs: DOI normalization (case-insensitive), title normalization, full-file checksum detection, quality-based retention scoring, and cross-domain duplicate handling
- `references/rag-web-indexing-workflow.md` — Step-by-step workflow for indexing web-found studies into the RAG catalog: DOI verification, PDF acquisition, text extraction, deduplication, and backup
- `references/data-quality-control.md` — Quality scoring, placeholder author detection, auto-enhancement from Crossref
- `references/defuddle-html-extraction.md` — Defuddle publisher compatibility matrix and fallback chain
- `references/fulltext-acquisition-pipeline.md` — Priority chain for full-text retrieval (Crossref → Unpaywall → Defuddle → web_extract)
- `references/self-correction-patterns.md` — Auto-verification triggers, quality scoring, and Crossref auto-enhancement patterns for catalog entries