# Multi-Step Verification Workflow with Tools and False Positive Patterns

## Phase 1: Initial Search
- Use `web_search` with specific terms: `"Instrument Name" "Location" population study`
- Search PubMed/MEDLINE, Crossref, Google Scholar, institutional repositories

## Phase 2: Candidate Extraction
- Use `web_extract` on publisher pages (DOI resolver, PMC, institutional repos)
- Use `read_file` on cached web content for complete text when truncated

## Phase 3: DOI Resolution Validation (MANDATORY for every study)
```bash
# Verify DOI is active and returns correct metadata
curl -s "https://doi.org/{DOI}" -H "Accept: application/json" -L

# OR use Crossref API to get full metadata
curl -s "https://api.crossref.org/works/{DOI}" -H "Accept: application/json"
```
**CRITICAL CHECK**: The returned title, authors, and year MUST match the study you found. Mismatches indicate Crossref returned a different (possibly similar-titled) study.

## Phase 4: Finding DOI When Not Obvious
If a study doesn't have an obvious DOI:
1. **Crossref search**: `curl -s "https://api.crossref.org/works?query={TITLE}&rows=5"` — look for exact title match
2. **PMC EUtils**: For PMC articles, use `https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pmc&id={PMCID}&retmode=json`
3. **Google Scholar**: Check for DOI in search results
4. **Journal website**: Navigate to the article page directly

## Phase 5: When DOI Doesn't Exist (Book Chapters, Reports, Theses)
**Mandatory**: Find an official URL or ISBN to cite the source.

### For Book Chapters:
1. Search ISBN on Google Books, WorldCat, or publisher websites
2. Check if the book/publisher has a DOI or catalog page
3. Use the publisher's official website URL
4. Check ResearchGate, institutional repositories for the chapter

### For Theses/Dissertations:
1. Check institutional repository URL (e.g., eprints, DSpace)
2. ProQuest if applicable
3. Google Scholar may yield a PDF with a stable URL

### For Edited Book Collections:
1. Search ISBN → identify publisher (ISBN prefix lookup)
2. Search publisher website for the book
3. Check if individual chapters have DOIs (rare but possible)
4. Use publisher website URL + ISBN as the citation source

### Publisher Identification by ISBN Prefix:
- **978-629**: Malaysian publisher prefix (check specific registrant)
- **978-967**: Universiti Malaya or related Malaysian publishers
- **978-983**: Various Malaysian publishers
- Use ISBNdb, WorldCat, or publisher directories to identify exact publisher

## Phase 6: Publisher URL Discovery Tools
When stuck on finding a publisher URL:
1. **WorldCat**: `https://www.worldcat.org/search?q={ISBN}`
2. **OpenLibrary**: `https://openlibrary.org/search.json?isbn={ISBN}`
3. **ISBNdb**: Commercial ISBN lookup
4. **Publisher websites**: Direct navigation based on identified publisher name
5. **ResearchGate**: Search for the book/chapter title, verify DOI/URL

## Phase 7: PMC Article Lookup
```bash
# Get PMC article metadata including DOI
curl -s "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pmc&id={PMCID}&retmode=json"

# OR search PMC by keywords
curl -s "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pmc&term={SEARCH_TERMS}&retmode=json"
```

## Phase 8: Cross-Reference Verification
- If DOI metadata doesn't match extracted content → wrong study, search again
- If no DOI → verify through at least 2 independent sources
- If only in institutional repo/thesis → flag as "CITED ONLY"
- If in edited book chapter → verify ISBN, publisher, and official URL

## False Positive Patterns to Avoid
- Studies that *mention* Malaysia/ENSS in discussion but didn't use them in methods
- Papers that cite ENSS but actually used a different instrument
- Scribd/Google Books snippets from book chapters (not peer-reviewed)
- Conference abstracts without full validation
- Studies with similar titles but wrong DOIs (Crossref may return closest match, not exact match)
- Google Books API quota limits (429 errors) — use alternative ISBN lookup services

## Phase 9: APA 7th Edition Reference Formatting (CRITICAL)

**USER PREFERENCE - DO NOT SKIP:**
- DOIs and URLs MUST be presented as PLAIN TEXT full https URLs only
- NEVER use citation tool exports (Zotero, Mendeley, EndNote, Google Scholar citation generator) — they wrap titles in clickable hyperlinks
- NEVER wrap DOIs/URLs in markdown link syntax `[text](url)` or angle brackets `<https://...>`
- NEVER append additional titles, descriptions, or notes AFTER the reference entry
- ALWAYS extract metadata directly from Crossref API for exact author names, titles, journal, volume, issue, pages

**Extraction Command:**
```bash
# Get exact metadata from Crossref
curl -s "https://api.crossref.org/works/DOI_HERE" | python3 -c "import sys,json; d=json.load(sys.stdin); msg=d.get('message',{}); print(msg.get('title',['N/A'])[0]); print(' '.join(a.get('given','')+'. '+a.get('family','') for a in msg.get('author',[]))); print(msg.get('container-title',['N/A'])[0]); print('Vol:', msg.get('volume'), 'Issue:', msg.get('issue'), 'Pages:', msg.get('page'))"
```

**Platform Display Artifact:**
Some chat interfaces automatically render plain text URLs as clickable hyperlinks with embedded page titles. This is a rendering artifact, NOT a formatting error. The reference entry itself contains correct plain text DOI/URL.

## Common Malaysian Research Sources
- **Universiti Sains Malaysia (USM)**: HUSM studies often in university repositories; published chapters may be from UTHM or USM presses
- **Universiti Kebangsaan Malaysia (UKM)**: Nursing stress studies in JK-KMN or institutional repos
- **Asia Pacific Journal of Public Health**: Publishes Malaysian nursing studies (SAGE, DOI: 10.1177)
- **Malaysian Journal of Medical Sciences (IJMS)**
- **BMC Nursing**: Open-access, common venue for Malaysian nursing research (DOI: 10.1186)
- **SAGE Publications**: Many Malaysian public health nursing studies (DOI: 10.1177)
- **UTHM Publishing**: Publishes OSH/occupational health book collections (ISBN: 978-629 prefix)
- **Penerbit USM**: Universiti Sains Malaysia publishing house