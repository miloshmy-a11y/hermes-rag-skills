# APA 7th Edition Formatting Quick Reference

## Journal Article (with DOI)
**Format:** Author, A. A, Author, B. B, & Author, C. C. (Year). Title of the article. *Title of the Journal*, *VolumeNumber*(IssueNumber), page-range. https://doi.org/xx.xxxxx/xxxxx

**Example:** 
French, S. E., Lenton, R., Walters, V., & Eyles, J. (2000). An empirical evaluation of an expanded Nursing Stress Scale. *Journal of Nursing Measurement*, *8*(2), 161–178. https://doi.org/10.1891/1061-3749.8.2.161

**In-text:** (French, Lenton, Walters, & Eyles, 2000)

## Journal Article (without DOI)
**Format:** Same as above but include official URL when no DOI available

## Key Formatting Rules

### Author Names
- Last name followed by initials (no spaces between initials)
- Up to 20 authors listed
- Example: `French, S. E., Lenton, R., Walters, V., & Eyles, J.`

### Article Titles
- Sentence case: Only first word of title and first word after colon are capitalized
- Proper nouns are also capitalized
- Example: `An empirical evaluation of an expanded Nursing Stress Scale`

### Journal Names
- Title case and italics
- Example: `*Journal of Nursing Measurement*`

### Volume and Issue
- Volume: italics
- Issue: parentheses, no italics
- Example: `*8*(2)`

## DOIs and URLs - CRITICAL USER PREFERENCE

**ALWAYS present DOIs and URLs as PLAIN TEXT. Do NOT wrap them in clickable hyperlinks.**

✅ **CORRECT:** `https://doi.org/10.1177/1010539510380560`

❌ **WRONG (no markdown/hyperlinks):**
- `[Rosnawati et al.](https://doi.org/10.1177/1010539510380560)`
- `<https://doi.org/10.1177/1010539510380560>`
- `"The Bahasa Melayu Version of... Title" [link](https://doi.org/...)`

**DO NOT use citation tool outputs** (Zotero, Mendeley, EndNote, Google Scholar exports) — these tools automatically wrap titles in clickable hyperlinks, which the user explicitly rejects. Instead, **always extract metadata directly from Crossref API** and format the reference manually.

**ALSO:** Do not append any additional titles, descriptions, or notes AFTER the reference entry. The reference should end with the DOI/URL, period.

### Platform Display Limitations
**IMPORTANT:** Some chat interfaces may automatically convert plain text URLs into clickable hyperlinks with embedded page titles. This is a display/interface issue, NOT a formatting error in the reference entry itself. The reference entry contains correct plain text DOIs/URLs as required by APA 7th edition.

### In-text Citations
- One author: (Author, Year) or Author (Year)
- Two authors: (Author & Author, Year)
- Three or more authors: (First Author et al., Year)

## Special Considerations for Research Sources

### When DOI is unknown but article is from PMC
If a PMC article doesn't show a DOI on the page, check the citation export feature or look for "PMC" followed by an article ID in the URL structure. Use `https://www.ncbi.nlm.nih.gov/pmc/articles/PMC{ID}/` as the official URL.

### When citing institutional repositories
Use the repository as publisher when no journal is involved. Include the direct URL to the article page in the repository.

### For conference/workshop papers
Include the conference name and location, plus the DOI or official proceedings URL.

### For book chapters without individual DOIs
Include publisher name, ISBN, and the official publisher or repository URL. Format:
```
Author, A. A., & Author, B. B. (Year). Chapter title. In A. Editor (Ed.), *Book Title* (pp. XX-XX). Publisher. ISBN: XXX-X-XXXXXX. URL
```

## Common Errors to Avoid

1. **Omitting DOI/URL** — Every reference must include either a DOI or an official URL
2. **Adding "Retrieved from"** for articles with DOIs — APA 7 says omit retrieval statements for works with DOIs
3. **Using ampersands in narrative citations** — use "and" in narrative text, "&" in parenthetical citations
4. **Incorrect capitalization** — journal names are title case, article titles are sentence case
5. **Missing issue numbers** — include issue numbers when available
6. **Using publisher page URL instead of DOI** — when a DOI exists, always use https://doi.org/{DOI}, not the publisher's landing page URL
7. **Fabricating DOIs or URLs** — never make up a DOI or URL
8. **Clickable hyperlink references** — DO NOT wrap DOIs/URLs or titles in clickable hyperlinks. Present DOIs and URLs as plain text only. Do not use citation tool exports that auto-link titles. Do not append descriptions or notes after the reference entry. ⚠️ **PLATFORM RENDERING WARNING**: Some chat interfaces automatically convert plain text URLs into clickable hyperlinks with embedded page titles. This is a display/interface artifact of the chat platform, NOT a formatting error in the reference entry. Users should understand that when they see a clickable link with a page title, the underlying reference text still contains the correct plain text DOI/URL.

## Crossref Author Extraction Pitfalls

When extracting authors from the Crossref API, several issues can arise:

1. **Institutional affiliations embedded in author list**: Crossref sometimes includes affiliation entries (with `name` key but no `given`/`family` keys) mixed into the `author` array alongside actual person authors.
   - **FIX**: When processing Crossref author data, skip entries that have `name` but lack both `given` and `family` fields. These are institution entries, not authors.

2. **Multi-part surnames**: Names like `AHMAD SHARONI` (where `AHMAD` is part of the surname) or `WAN ZAINODIN` (where `WAN` is part of the surname) must be preserved correctly.
   - Crossref returns `given: "WAN HARTINI"`, `family: "WAN ZAINODIN"`. The correct APA format is `ZAINODIN, W. H. W.` — not `Wan, Z.`
   - **Rule**: Never split multi-word surnames. Use the `family` field as-is from Crossref.

3. **DOI case sensitivity**: DOIs are technically case-insensitive, but Crossref returns them with specific casing. Always normalize to lowercase when comparing for deduplication.

## Handling Near-Match Studies

When a study does NOT exactly match the requested criteria (e.g., "OUM students" but the study is from "UTEM students" or another Malaysian university):

1. **Label clearly as secondary/supporting** - never present as primary finding
2. **Explicitly state the mismatch** - e.g., "Study from Universiti Teknikal Malaysia Melaka (not OUM)"
3. **Explain why it's still relevant** - same country, same population type, same instrument/method
4. **Format the same way** - APA 7th with plain text DOI/URL

**Example:** 
> ⚠️ Secondary finding - ChatGPT usage study from Universiti Teknikal Malaysia Melaka (UTEM), not Open University Malaysia (OUM). While this study is from a different Malaysian university, it provides relevant context about ChatGPT adoption patterns among Malaysian engineering students.

**APA Reference:**
> Ibrahim, E., Md Saad, M. S., & Rajikon, M. A. N. (2025). Exploring student perspectives on ChatGPT: Knowledge, attitudes, concerns, and usage patterns at Universiti Teknikal Malaysia Melaka. *International Journal of Research and Innovation in Social Science*, *9*(1), 771-785. https://doi.org/10.47772/ijriss.2024.8120209