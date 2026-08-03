# Search Discrimination Pattern: Distinguishing Instrument Usage vs. Mention

## Problem

When searching for studies using a specific measurement instrument (e.g., "Expanded Nursing Stress Scale"), many results returned studies that merely *mention* the instrument in discussion or reference sections, or use a *different but similarly named* instrument (e.g., NSS vs. ENSS).

## Solution: Multi-Target Verification Approach

### Step 1: Multi-Database Search

Search across multiple authoritative sources:
```bash
# PubMed (most reliable for health sciences)
curl -s "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term={SEARCH_TERMS}&retmode=json"

# PMC (for open-access articles)
curl -s "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pmc&term={SEARCH_TERMS}&retmode=json"

# Crossref (for DOI resolution)
curl -s "https://api.crossref.org/works?query.bibliographic={SEARCH_TERMS}&rows=20"
```

### Step 2: Exact Instrument Verification

For each candidate study:
```bash
# Fetch full XML abstract from PubMed
curl -s "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id={PMID}&retmode=xml" | python3 -c "
import sys, re
content = sys.stdin.read()
# Verify actual usage, not just mention
if re.search(r'Expanded Nursing Stress Scale|ENSS', content, re.IGNORECASE):
    print('VERIFIED: Study uses ENSS')
else:
    print('FALSE POSITIVE: Study does not use ENSS')
"

# Fetch metadata from Crossref for exact details
curl -s "https://api.crossref.org/works/{DOI}" | python3 -c "
import sys, json
d = json.load(sys.stdin)
msg = d.get('message', {})
abstract = msg.get('abstract', '')
# Check abstract for ENSS usage
if 'Expanded Nursing Stress Scale' in abstract or 'ENSS' in abstract:
    print('Abstract confirms ENSS usage')
else:
    print('Abstract does NOT confirm ENSS usage')
"
```

### Step 3: Population Verification

Verify that the study population specifically matches the request:
```bash
# Check abstract for population keywords
if re.search(r'Malaysia|Malaysian', abstract, re.IGNORECASE):
    print('Population: Malaysia confirmed')
elif re.search(r'Malaysia|Malaysian', full_text, re.IGNORECASE):
    # Check full text if abstract doesn't contain it
    print('Population: Malaysia confirmed (full text)')
else:
    print('FALSE POSITIVE: Not Malaysian population')
```

## Pitfalls to Avoid

- **Mention vs. Usage**: A study might reference ENSS in the introduction/discussion but use a different instrument in methodology
- **Scale confusion**: NSS (Nursing Stress Scale) ≠ ENSS (Expanded Nursing Stress Scale) - verify the exact instrument name
- **Cross-National Studies**: Papers may include Malaysia in the sample but not be Malaysia-specific
- **Book Chapters vs. Peer-Reviewed**: Studies in edited books or conference proceedings (like the HUSM case study in an OSH collection) may lack traditional DOIs and peer-review status
- **Google Scholar False Positives**: Often returns citations that mention instruments without using them
- **Platform display artifact**: Chat interfaces automatically convert plain text URLs into clickable hyperlinks with embedded page titles. This is a rendering artifact, NOT a formatting error.

## Handling Secondary/Supporting Findings

When a study does NOT perfectly match all criteria but still contains relevant information, present it as **secondary/supporting findings** with explicit transparency notes.

### When to Present as Secondary/Supporting:
- **Instrument match but publication type mismatch**: A study uses the exact requested instrument (e.g., ENSS) but is published in a non-peer-reviewed source (e.g., book chapter, report, thesis)
- **Partial population match**: Study includes the requested population but in a cross-national or multi-country design
- **Methodology match but context differs**: Study used the requested instrument with the population but in a different context (e.g., students vs. practicing nurses)

### How to Present Secondary Findings:
Follow this structure:
```
### Secondary/Supporting Finding:
[Study title]
**Authors:** [Full author list]
**Status:** ⚠️ PARTIALLY VERIFIED - [Explain why it's not a primary match]

**Reason for Partial Match:**
[Explain the discrepancy - e.g., "Uses ENSS but published as book chapter, not peer-reviewed journal" or "Includes Malaysian nurses but in cross-national sample"]

**Key Finding:**
[Brief relevant finding]

**APA 7th Reference:**
[Full properly formatted reference with DOI/URL as plain text]

**Note:** [Explain how this finding supports or complements the main research question despite not being a perfect match]
```

**Example:** For ENSS + Malaysian nurses search:
If no peer-reviewed journal articles are found using ENSS with Malaysian nurses, but a book chapter does use ENSS with HUSM nurses, present:

### Secondary/Supporting Finding: Prevalence of Job Stress Among Nurses at HUSM

**Authors:** Paneerselvam, A., Abdul Samad, N. I., & Hussin, N.

**Status:** ⚠️ PARTIALLY VERIFIED - Uses ENSS with Malaysian nurses but published as book chapter

**Reason for Partial Match:** This study used the Expanded Nursing Stress Scale (ENSS) among nurses at Hospital Universiti Sains Malaysia (HUSM), meeting the instrument and population criteria. However, it was published as a chapter in an edited book (OSH Issues: Collection of Case Studies in Malaysia 2023) rather than in a peer-reviewed journal.

**Key Finding:** 61.5% of nurses experienced mild stress, 31.5% moderate stress, and 1.4% severe stress. The ENSS demonstrated good reliability (Cronbach's α = 0.879).

**APA 7th Reference:**
Paneerselvam, A., Abdul Samad, N. I., & Hussin, N. (2023). Prevalence of job stress among nurses in Hospital Universiti Sains Malaysia. In *OSH Issues: Collection of Case Studies in Malaysia 2025* (pp. 1-14). UTHM Publishing. ISBN 978-629-7566-81-8. https://www.researchgate.net/publication/378010713

**Note:** While this study is not a primary peer-reviewed finding, it provides valuable supporting evidence that ENSS has been used with Malaysian nurses in practice. The methodology, instrument, and population all match the research criteria, though the publication format differs from typical journal articles.

## Example Discrimination Logic

For searching "ENSS among Malaysian nurses":

```python
# WRONG approach - accepts any paper mentioning both terms
results = search("Expanded Nursing Stress Scale AND Malaysia")

# CORRECT approach - verifies actual instrument usage AND population
candidates = search("Expanded Nursing Stress Scale AND Malaysia AND nurse")
for study in candidates:
    abstract = fetch_abstract(study.pmid)
    # Must verify ENSS is used IN METHODS, not just mentioned anywhere
    if "Expanded Nursing Stress Scale" in abstract['methods']:
        if "Malaysia" in abstract['methods'] or "Malaysia" in abstract['results']:
            # Only accept if ENSS is used in methodology AND population is Malaysian nurses
            verified_studies.append(study)
    # Reject any study that only mentions ENSS in references or discussion
```

## Verification Precedence Hierarchy

Use this order when sources disagree or are unavailable:

1. **Primary (VERIFIED)**: DOI confirmed active via Crossref, content verified through publisher/PMC abstract, bibliographic details match
2. **Secondary (PARTIALLY VERIFIED)**: PMC/EUtils confirmation without Crossref (check NCBI EUtils API for DOI + abstract)
3. **Tertiary (PARTIALLY VERIFIED)**: Multiple independent non-DOI sources agreeing (publisher pages, institutional repositories, citation networks)
4. **Minimum (CITED ONLY)**: Single secondary mention only — original source could not be directly accessed

## Key Takeaway

Always verify through both **Crossref DOI resolution** AND **original source abstract extraction** that:
1. The study ACTUALLY USED the requested instrument (check methods section)
2. The study population is specifically the requested demographic
3. The instrument name is exact (NSS ≠ ENSS)

**Dedup before verification** — Remove duplicates by normalizing title + first author + year before running verification calls.

**Search stopping rule** — Stop when N matching studies found across ≥2 independent databases, OR M queries (typically 5-8) yield no new matches.

## Multi-Source Corpus Analysis Pattern

When working with a full-text corpus (dozens of extracted PDFs) rather than individual study verification:

### Deep Text Scanning
Shallow matching (abstracts, metadata only) finds only ~10-20% of relevant studies. For comprehensive corpus-wide searches:

1. **Shallow pass**: Match query keywords against titles, abstracts, journal names (fast, but shallow)
2. **Deep pass**: Scan ALL available text including:
   - Full extracted PDF content (first 5-10 pages)
   - Metadata JSON files (full Crossref responses)
   - Secondary identifiers (institution names, locations, methodology terms)
3. **Confidence scoring**:
   - **High**: Explicit mention in title, abstract, or journal scope
   - **Medium**: Mentioned in full text with clear methodological context
   - **Low**: Single indirect or peripheral mention

### Multi-Pass Tagging Best Practice
When applying tags across many documents in successive analysis passes:

**Always deduplicate tags after each pass:**
```python
# Fix: Remove duplicate tags after each analysis pass
doc['tags'] = list(dict.fromkeys(doc['tags']))  # preserves order, removes dups
# Or: doc['tags'] = list(set(doc['tags']))
```

**Validate counts:**
```bash
python rag_system.py --stats  # Verify tag counts match expected
```

This prevents the common failure mode where running analysis scripts multiple times accumulates duplicate tags like `"Supervisor Conflict", "Supervisor Conflict", "Supervisor Conflict"` in document lists, which inflates tag counts and breaks search filtering.