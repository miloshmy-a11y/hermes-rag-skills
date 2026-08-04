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

1. **Primary**: DOI confirmed active via Crossref with matching metadata (title, authors, year, abstract). **Crossref is the authoritative citation/metadata source** — trust its returned title/authors/year over OpenAlex, Semantic Scholar, PubMed, or any retrieved full-text snippet. Never conclude a DOI is wrong from fallback text (S2-page/PubMed can return a wrong record for old/non-biomedical DOIs); verify the DOI, not the snippet.
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

When a study needs full text added to the RAG catalog, follow the consolidated chain in
`research/general-purpose-rag/references/fulltext-retrieval-priority.md` (single source of truth).
Key session-validated tactics:

1. Verify DOI via Crossref API.
2. Follow the consolidated chain in `research/general-purpose-rag/references/fulltext-retrieval-priority.md`
   (SINGLE SOURCE OF TRUTH). Key session-validated tactics it encodes:
   - **Paywalled publisher PDFs (Wiley/Elsevier/SAGE) 403 on bot GET**, and `web_extract` on the `doi.org`
     landing page returns 0 chars (publisher blocks bots). The reliable workaround is **S2 paper-page HTML**:
     `get_paper(f"DOI:{doi}", fields="paperId")` → `web_extract(urls=["https://www.semanticscholar.org/paper/<paperId>"])`.
     S2 pages are bot-accessible and embed abstract + references + often full text (recovered 46/47 paywalled
     2020+ thesis refs in one pass). Store as `.md` in `SOURCE_TEXT/`, set `full_text_status: s2_page_extracted`.
   - If a paper is not on S2, try **PubMed** (`https://pubmed.ncbi.nlm.nih.gov/<pmid>/`) — extractable even
     when S2 lacks the paper (recovered the final 3 of 285 post-2020 studies this way).
3. Never present a login-wall/landing page as "full text." Assert real PDF or extracted-HTML, else mark
   `full_text_status: pending`.

`web_extract` is importable ONLY inside `execute_code` (not terminal Python). Batch ≤5 URLs/call.

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

**Full-text sufficiency rule (user directive 2026-08-03):** a complete PDF body is not required for every entry. For **foundational / frequently-cited** works (e.g. Karasek 1979 demand-control, Selye 1936 GAS, Siegrist ERI, Gray-Toft & Anderson NSS, French 2000 ENSS) cited across hundreds of papers, an abstract or a snippet from a secondary source (publisher page, PubMed abstract, or a citing paper's description) is sufficient. Do not burn retrieval effort chasing the full body of such classics — record `full_text_status: meta_only`/`abstract_only` with the Crossref-verified citation, then move on. Pursue full body text only for (a) the user's own thesis citations that are primary studies being read for content, or (b) studies specifically queried for their findings.

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

**Preserve user-verified metadata (CRITICAL)**: When backfilling catalog metadata from Crossref/S2/OpenAlex, the user's manually-verified title/authors/year are AUTHORITATIVE. **Only fill EMPTY fields — never overwrite existing values.** Guard every write: `if not d.get('venue'): d['venue']=...`; `if not d.get('apa_citation'): d['apa_citation']=...`; `if not (d.get('authors') and [a for a in d['authors'] if a]): d['authors']=...`. This prevents silently clobbering a correct hand-curated reference with noisier API metadata. When in doubt, keep the user's value.

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
- `references/citation-workflow.md` — Verified citation workflow: 2-source verification, DOI content-negotiation for authoritative BibTeX, hallucination prevention (adapted from NousResearch hermes-agent)
- `scripts/crossref_backfill.py` — Non-destructive Crossref backfill (venue/apa/abstract/authors/year) + BibTeX via content-negotiation. Fills ONLY empty fields; preserves user-verified data. Run: `python3 scripts/crossref_backfill.py <CATALOG.json> [--min-year 2020] [--domains ...]`
- `references/self-correction-patterns.md` — Auto-verification triggers, quality scoring, and Crossref auto-enhancement patterns for catalog entries

> **Full-text retrieval priority:** see `research/general-purpose-rag/references/fulltext-retrieval-priority.md` (consolidated chain).

<!-- ===== Merged from rag-verification-protocol (2-factor DOI+content verification) ===== -->

# RAG Result Verification Protocol v1.0

## Overview
Protocol for verifying that RAG search results are genuinely relevant — not just keyword matches. Applies whenever a user asks for studies matching specific population + concept criteria.

## The Problem This Solves
DOI verification only confirms a citation is real. It says nothing about whether the paper's content matches the queried population and finding.

## Two-Factor Verification (Both Required)

### Factor 1: DOI Verified (Crossref is the authoritative metadata source)
- Crossref returns HTTP 200 for the DOI, and Crossref's returned title/authors/year/journal
  match the catalog entry / the paper it claims to be. **Always resolve the DOI via Crossref**
  (`https://api.crossref.org/works/<DOI>`) — trust Crossref over OpenAlex, Semantic Scholar,
  PubMed, or any retrieved full-text snippet. Do NOT judge a DOI wrong from fallback text
  (S2-page/PubMed can return a wrong record for old/non-biomedical DOIs). Crossref registration
  data is the canonical citation record.
- Confirms the **citation is real AND correctly attributed**.

### Factor 2: Content Verified  
- Population match: actual studied population matches query
- Finding match: concept explicitly reported as significant factor
- Confirms the **content is relevant**

## Common False Positive Patterns
| Pattern | Example | Action |
|---------|---------|--------|
| Instrument on wrong population | NASA-TLX on diabetes | Exclude |
| Term in background only | workload in intro | Exclude |
| Term as survey item | rate your workload | Exclude |
| Explicit "no association" | no link found | Exclude |

## Summary Statement Rules
- "X verified" means ALL X passed DOI + content verification
- Label DOI status and content status distinctly

## Content-Trust Pitfalls (session-hardened 2026-08)

Hard-won lessons from enriching a thesis-cited catalog — encode so they aren't repeated:

- **DOI correctness is Crossref-only, never inferred from retrieved full text.** The S2-page /
  PubMed fallback can return a WRONG record for old/non-biomedical DOIs (Selye 1936, Karasek 1979,
  Gray-Toft & Anderson NSS, French 2000 ENSS all returned garbage fallback text while the DOI was
  correct). Resolve via `https://api.crossref.org/works/<DOI>`; do NOT flag "MISATTRIBUTED-DOI" from
  fallback content. (This is Factor 1 above — stated again because it was violated in practice.)
- **Instrument (`measures`) must be read from the METHODS section, not guessed from the abstract.**
  A Kelantan job-stress study was wrongly indexed as "NSS + HSOPSC" from its abstract, but the body
  says "Expanded Nursing Stress Scales and Safety Attitude Questionnaire" (ENSS + SAQ). Grep the real
  body for scale names (ENSS/NSS/MBI/JCQ/ERI/PSS/SAQ/NAQ-r/HSOPSC); if only an abstract exists, set
  `measures=null` or tag `suspected_abstract_only` — never assert an instrument not seen named in body.
- **ENSS != NSS.** Expanded Nursing Stress Scale (French 2000) vs Nursing Stress Scale
  (Gray-Toft & Anderson 1981) are distinct and routinely conflated by chatbots (ChatGPT/Grok) and
  abstract-readers. When the user says "ENSS study", exclude NSS-only studies from any count.
- **Do NOT infer "first/Nth study in country X using instrument Y" from catalog count.** Discovery
  order is not real-world novelty (a 2022 paper found today doesn't make the user "first" until 2022).
  Verify no other such study exists (broad web search incl. non-OA journals/theses/conference abstracts)
  and confirm the SAME instrument, then scope the claim (e.g. "first in in-patient wards of HSM Perak",
  "first FYP/thesis") rather than state it absolutely.

## Verification discipline: small batches, never one giant pass
A user correction hardened this (2026-08): attempting to "go through ALL records" in one large
batch causes errors to be MISSED — at scale the agent trusts the index / matches keywords and skips
opening the full text, so wrong `country` and guessed `measures` slip through. The errors only
surface when each record is opened and its affiliation sentence is actually read.

- Process records in SMALL chunks (10-25 at a time), verifying EACH against its real full text.
- Random sampling is good for spot-checks but never reaches the long tail; pair it with a FULL
  ORDERED pass (all 252 records in slices) so nothing is left unaudited.
- For catalog hygiene (country/instrument accuracy), see `references/country-audit.md` — it has the
  reusable scanner invocations and the false-positive catalog (reprints, PubMed.gov banners, Wiley
  download watermarks, comparison-country-in-title) that must NOT be "fixed".
- After each batch of fixes, push the catalog to its GitHub backup so progress is never lost.

## Full-text FILE integrity — the file must actually be the right paper
A user correction hardened this (2026-08): *"if full text was wrong, the index record is likely
also wrong, because it's supposed to be a brief extract from the full text/abstract — so verify
both at the same time."* This is the most damaging class of index corruption and it is INVISIBLE
to metadata-only checks: the DOI is correct, Crossref matches, but the stored `extracted_text`
file holds a DIFFERENT document (e.g. the ENSS French-2000 paper stored a p53/breast-cancer
article; Karasek-1979 stored a 2019 HEMS-physicians paper; NSS-1981 stored an HCV article). Any
`brief_abstract` / `keywords_llm` / `measures` derived from that file is then also wrong.

**Co-verify file + indexed fields in ONE pass.** When you open a record to fix anything, do not
treat `country` / `measures` / `brief_abstract` as independent. If the file is wrong, rebuild ALL
of them from an authoritative source (Crossref, or PubMed-by-PMID) in the same edit — never leave a
half-fixed record with a corrected `country` but a `brief_abstract` still derived from the bad file.

**Detecting mismatched files** (reusable: `scripts/audit_fulltext_mismatch.py` for full coverage;
random spot-checks via the catalog's `audit_random_records.py` / `audit_fulltext_doctype.py`):
1. Open `files.extracted_text`; if `<800` bytes OR first 300 chars contain "skip to main content" /
   "this page can't be found" / only a PubMed.gov banner → file is EMPTY/banner-only (not the article).
2. Title-match test: normalize the title (collapse non-breaking hyphens/ampersands), take the 8
   longest content words (drop stopwords + topic words like nurse/stress), require ≥25% present in
   the file text. <25% overlap = LIKELY MISMATCHED file → verify by reading the file head, then rebuild.
3. **PRISMA-template scan (separate — the title test misses these):** scan every file for template
   boilerplate (`tips for reporting this item`, `eligibility criteria with a rationale`, `preferred
   reporting items`, `identify any specific restrictions such as date`) where the paper's title words are
   NOT in the body and the file is `<6000` bytes. These are reporting templates swapped in for the real
   article (confirmed this session: burden-of-treatment, parents/pediatric, self-management). Rebuild from
   EPMC/PubMed. **Always run BOTH scans** (title-overlap + template-signature) on a full-coverage pass.
4. **OUM/coursework wrapper scan (a THIRD, larger class the title test also misses):** scan every file
   for Open University Malaysia student-kit markers (`open university malaysia`, `oumk`, `nbbs`, `nbns`,
   `learning kit`, `matriculation no`, `matrix no`, `final year project submitted`, `project paper submitted`)
   where the paper's title words are NOT in the body and there is no `abstract` near the top. These are
   OUM learning-kit / exam / assignment PDFs swapped in for the real research article (confirmed this
   session: 34 files had OUM markers, 24 still mis-typed as `doc_type=study`). Action: set
   `doc_type=coursework` + `relevance=off_topic`; do NOT keyword them as research. If the indexed DOI is a
   real paper you want, re-fetch its abstract from EPMC and overwrite the file. `local:` instrument/checklist/
   thesis-support docs (STROBE, NASA-TLX forms, NMRR guides) are reference material, not research — they
   legitimately lack `keywords_llm`. **Always run THREE scans** (title-overlap + PRISMA + OUM) on a pass.
   The bundled `scripts/audit_fulltext_mismatch.py` already runs all three + a status/disk check.
4. When a file is confirmed wrong: replace it with Crossref/PubMed-verified metadata (title, journal,
   year, authors) and set `full_text_status` honestly (`meta_only` if only the abstract is available,
   `present` once a real body is acquired). Do NOT invent an abstract — set `brief_abstract` to a
   minimal citation line and clear `keywords_llm`/`measures` until a real body/abstract is in hand.
   After acquiring a new full text, do the comprehensive re-index immediately (same pass), not later.

**Topical RELEVANCE is a separate verification dimension.** Country + file-integrity pass even when a
record is OFF-TOPIC for the user's thesis (pediatric, genetics, COPD, COSMIN reporting-guideline, PRISMA
templates). Add a `relevance` field per record: `off_topic` / `weakly_relevant` / `instrument` / (default
on-topic, untagged). Use `scripts/audit_relevance.py` for random spot-checks; verify every flag by READING
the abstract, never auto-tag from the keyword score. Keep off-topic records (exclude at query time), don't
delete. See `references/fulltext-integrity.md` for the relevance-audit recipe + confirmed off-topic examples
(burden-of-treatment, parents/pediatric, self-management, racism-in-healthcare, COSMIN guideline) and the
weakly-relevant / instrument distinctions (clinical-burnout cognitive function; PSS/ERI papers).

**Full-text false positives that must NOT be "fixed"** (running list in `references/fulltext-integrity.md`):
- PubMed.gov site banner ("official website of the United States government" is page chrome, not the
  study country) — the study's own country comes from its title/affiliation, not the .gov frame.
- Wiley "Downloaded from … NIH Malaysia, Wiley Online Library on [date]" is a download WATERMARK, not
  the study country (and not an article body).
- A PMC article whose head is just the "[Skip to main content]" nav LINK but HAS a real body below is
  CORRECT — do not flag it as empty.
- A `local:` tool/guideline record whose text matches its own title is correct — a verifier keyword
  hitting the record's own title is a false positive in the verifier, not corruption.

**Pitfall — disk/catalog divergence after a crash.** A script that writes extracted-text files to
disk but then raises before its final `json.dump` leaves the catalog JSON OUT OF SYNC with the files
on disk (files are real, but `full_text_status` still says `meta_only`). Always either (a) structure
the file writes + the single `json.dump` so they can't partially fail, or (b) after running, verify
disk-vs-catalog: for each acquired DOI confirm `os.path.getsize(files.extracted_text) > 800` AND the
catalog `full_text_status` matches (`present`/`abstract_only`); re-run the save if they diverge.

**Pitfall — external audit may target a DIFFERENT catalog.** If an external reviewer (e.g. another LLM) hands
you a "critical issues" checklist, FIRST confirm it describes THIS catalog, not a different/wrong file. This
session an external audit claimed 722 docs, `quality_score` tiers, and functions (`add_documents_from_folder`,
`verify_doi_metadata`) that DO NOT EXIST here (real catalog: 526 docs, no such functions/fields). The
*spirit* was valid (bulk-ingestion corruption), but the specific counts/fields were wrong. **Action:** measure
the real catalog yourself (`len(docs)`, field coverage) before acting; verify which field the actual search
code reads (here it is `keywords_llm`, NOT the legacy always-empty `official_keywords`) and backfill THAT.

**Pitfall — DOI-normalization in audit/backfill code.** Catalog stores some DOIs WITH `https://doi.org/` and
some WITHOUT (bare `10.x/...`). Any `by = {d['doi']: d}` dict + lookup will MISS the bare-DOI records. Always
normalize keys: `key = d['doi'].replace('https://doi.org/','').replace('http://doi.org/','').strip()`.

## Support files for this section
- `references/fulltext-integrity.md` — false-positive running list (PubMed.gov banner, Wiley watermark, PMC
  nav-link, German reprint, local-guideline self-match, global-review country) that must NOT be "fixed"; the
  PRISMA-template + OUM/coursework detection recipes; the topical-relevance audit recipe; re-acquisition
  sources (PMC/EPMC/PubMed/Crossref); the RETRIEVAL-FIELD lesson (verify which field the search code reads
  before backfilling); the `verified_at` backfill (cheap, stops re-verification churn); status/disk
  consistency; and the DOI-normalization pitfall.
- `scripts/audit_fulltext_mismatch.py` — re-runnable full-coverage detector: runs empty + title-overlap<25%
  + PRISMA-template + OUM/coursework scans AND a status/disk consistency check. Read its flags, then read
  each flagged file's head to confirm before rebuilding.
- `scripts/audit_relevance.py` — random topical-relevance auditor (nurse/workforce + stress detection;
  flags off-topic candidates for manual abstract read + `relevance` tagging).
