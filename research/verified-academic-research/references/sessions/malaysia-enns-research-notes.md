# Research Session Notes: Expanded Nursing Stress Scale in Malaysia

## Search Strategy

### Initial Search
```
"Expanded Nursing Stress Scale Malaysia nurses study"
```
Found: General references to ENSS and Malaysian adaptation studies.

### Refined Search
```
"Expanded Nursing Stress Scale" "Malaysia" nurses "cross-sectional" study OR "correlates" stress
```
Found: Specific Malaysian studies using ENSS.

### Targeted Search
```
"Expanded Nursing Stress Scale" "Hospital Universiti Sains Malaysia" OR "HUSM" 2019-2025
```
Found: The HUSM prevalence study and related references.

### Verification Search
```
"Expanded Nursing Stress Scale" ("Malaysia" OR "Bahasa Melayu") nurses study full text
```
Found: Multiple sources confirming Malaysian ENSS studies.

## Key Sources Identified

### Primary Studies Using ENSS with Malaysian Nurses (CONFIRMED, 2026-08):

> NOTE (accuracy correction 2026-08-04): The earlier version of this note attributed an ENSS
> HUSM study to "Paneerselvam, Abdul Samad, & Hussin (2023)" with alpha 0.879 / 61.5%-31.5%-1.4%.
> That attribution was NOT verified against the catalog. The two CONFIRMED Malaysian ENSS
> studies are listed below. The HUSM/Kelantan study is in the catalog as `10.37231/ajmb.2022.6.S1.517`
> (East Coast Teaching Hospital, 2022, ENSS + SAQ). Treat the Paneerselvam 2023 detail as
> UNVERIFIED until cross-checked via Crossref.

1. **Chittra Selvi a/p Bala Krishnan (2026, OUM FYP)** - *Factors Inducing Work-Related Stress
   among Staff Nurses of In-patient Wards in a Government Hospital* (Hospital Seri Manjung, Perak)
   - Used **ENSS + NSS** (+ PSS, HSOPSC, Turnover Intention). n=195 staff nurses.
   - This is the user's own 2nd-Malaysian-ENSS-study thesis. Workload, Problems with Supervisors,
     and Patients/Families were the TOP ENSS subscales.
   - Local record: `local:chittra-thesis-2026-work-stress-hsm`.

2. **East Coast / HUSM study (2022)** - *The Overview of Job Stress and Patient Safety Culture
   among Nurses in the East Coast Teaching Hospital, Malaysia*
   - Used **ENSS + SAQ** (Safety Attitude Questionnaire). DOI: `10.37231/ajmb.2022.6.S1.517`.
   - Catalog record: `10.37231/ajmb.2022.6.S1.517`. (This is the Kelantan/HUSM ENSS study;
     verify whether Paneerselvam et al. are the authors via Crossref before citing the 2023 ISBN edition.)

3. **Rosnawati, Moe, Masilamani, & Darus (2010)** - *The Bahasa Melayu Version of the Nursing Stress
   Scale Among Nurses: A Reliability Study in Malaysia*
   - Adapted **NSS** (not ENSS) for Bahasa Melayu. 30 nurses, test-retest reliability.
   - Asia Pacific Journal of Public Health, 22(4), 501-506. DOI: 10.1177/1010539510380560.
   - Catalog record: `10.1177/1010539510380560`.

4. **Cheku et al. (2024)** - *Occupational stress, job satisfaction and intent to leave: Nurses at the
   Terengganu Tertiary Referral Hospital* (MJPHM 2024, 24(3):240-250)
   - Used **NSS** (+ Turnover Intention). Malaysian nursing stress study (NSS instrument).
   - Catalog record: `local:cheku2024nwsqinflfctpdfstudy`.

### Non-Malaysian ENSS (context only):
- **Kunwar et al. (2025)** - Occupational stress among nurses in a Medical College Hospital, Nepal.
  ENSS, 311 nurses. Industrial Psychiatry Journal, 34(2), 210-214. DOI: 10.4103/ipj.ipj_20_25.

### Secondary References Cited in Malaysian Studies:

- **French, Lenton, Walters, & Eyles (2000)** - Original ENSS development
  - Journal of Nursing Measurement, 8(2), 161-178
  - DOI: 10.1891/1061-3749.8.2.161

- **Kakemam et al. (2019)** - Occupational stress among nurses (referenced in Malaysian studies)
  - Contemporary Nurse, 55, 237-249
  - DOI: 10.1080/10376178.2019.1647791

## Search Challenges and Solutions

### Challenge: Truncation Issues
Web extracts limited to <5000 chars for most articles.
**Solution:** Read cached files using `read_file` to access complete content.

### Challenge: Access Barriers
Academia.edu requires login for full papers.
**Solution:** Use search result snippets and citation metadata from accessible sources.

### Challenge: Scale Confusion
Many papers reference "Nursing Stress Scale" (NSS) vs "Expanded Nursing Stress Scale" (ENSS).
**Solution:** Verify which instrument was actually used in the methodology section.

### Challenge: False Positives
Search results may mention Malaysia/ENSS in reference lists without direct usage.
**Solution:** Filter for studies where ENSS is the actual measurement tool in methodology.

## Tools Used

1. `web_search` - Initial discovery and targeted searches
2. `web_extract` - Content extraction from accessible sources (PMC, Scribd, Academia.edu)
3. `read_file` - Full content reading of cached web pages
4. `search_files` - Not applicable for this session

## Sources Accessed

- PMC (pubmed.ncbi.nlm.nih.gov) - Successful extraction
- Scribd - Partially accessible, used for methodology details
- Academia.edu - Accessible via cached content
- JSTOR - Partial preview available
- SAGE Journals - Abstract and citation info available
- ResearchGate - Reference data available via search snippets

## Session Lessons Learned

### Lesson 1: Platform Display Artifact with URLs
Some chat interfaces (including Hermes desktop) automatically convert plain text URLs into clickable hyperlinks with embedded page titles. This is a rendering artifact of the chat platform, NOT a formatting error. The reference entry itself contains the correct plain text DOI/URL. Users should copy and paste URLs directly to verify they resolve correctly.

### Lesson 2: Avoid Citation Tool Outputs
Citation tool exports (Zotero, Mendeley, EndNote, Google Scholar citation generators) automatically wrap titles in clickable hyperlinks, which the user explicitly rejects. Always extract metadata directly from Crossref API and format references manually.

### Lesson 3: Publisher Identification by ISBN
When DOI is not available (e.g., book chapters in edited collections), identify publisher through ISBN prefix lookup and official publisher pages. The ISBN 978-629-7566-81-8 was traced to UTHM Publishing through ResearchGate publisher listings.

### Lesson 4: Study Count Reality Check
Initial broad searches may suggest many Malaysian ENSS studies exist, but thorough verification reveals that direct ENSS usage in Malaysian nursing research is limited. Many papers mention ENSS but actually use the Nursing Stress Scale (NSS). Always verify the actual instrument used in the methodology section, not just mentions in the text.

### Lesson 5: CrossRef API for Exact Metadata
Always use `https://api.crossref.org/works/{DOI}` to get exact metadata including author names, journal titles, volume/issue numbers, and page ranges. Citation tool outputs often have formatting inconsistencies.

## Key Citations Verified

1. French, S. E., Lenton, R., Walters, V., & Eyles, J. (2000). An empirical evaluation of an expanded Nursing Stress Scale. *Journal of Nursing Measurement*, *8*(2), 161-178. https://doi.org/10.1891/1061-3749.8.2.161

2. Gray-Toft, P., & Anderson, J. G. (1981). The Nursing Stress Scale: Development of an instrument. *Journal of Behavioral Assessment*, *3*(1), 11-23. https://doi.org/10.1007/BF01321348

3. Rosnawati, M. R., Moe, H., Masilamani, R., & Darus, A. (2010). The Bahasa Melayu version of the Nursing Stress Scale among nurses: A reliability study in Malaysia. *Asia-Pacific Journal of Public Health*, *22*(4), 501-506. https://doi.org/10.1177/1010539510380560

4. Alkrisat, M. A., & Alatrash, M. A. (2017). Psychometric properties of the Extended Nursing Stress Scale: Measuring stress in workplace. *Journal of Nursing Measurement*, *25*(1), 31E-45E. https://doi.org/10.1891/1061-3749.25.1.31

5. Rosnawati, M. R., Mohd Fauzi, M. F., Mat Saruan, N. A., Mohd Yusoff, H., & Harith, A. A. (2020). Why so stressed? A comparative study on stressors and stress between hospital and non-hospital nurses. *BMC Nursing*, *19*(1), 90. https://doi.org/10.1186/s12912-020-00511-0