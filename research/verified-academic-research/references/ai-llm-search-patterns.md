# AI/LLM Search Patterns: Documented Zero-Result Workflow

## Problem

When searching for highly-niche combinations (e.g., "Open University Malaysia AND AI/LLM AND student"), the result set is often empty after exhaustive searches across PubMed, PMC, Crossref, and Google Scholar. In that situation the correct behavior is NOT to broaden the query into a flood of loose near-matches (which would yield false positives and dilute precision), but to:

1. Report "NO STUDIES FOUND" explicitly and honestly.
2. Optionally surface the *closest* related studies as **Secondary/Supporting Findings** ONLY when they clearly state the exact mismatch.

## Verified Pattern: OUM + AI/LLM (No Results Found)

**Query**: Open University Malaysia AND (ChatGPT OR "generative AI" OR LLM OR "artificial intelligence") AND (student OR "university student")

**Databases searched**: PubMed, PMC, Crossref API, Google Scholar, NCBI EUtils

**Result**: **ZERO studies found** linking OUM students to AI/LLM adoption.

**Correct response format**:
> ❌ **NO STUDIES FOUND**: No published studies were found that specifically examine Open University Malaysia (OUM) students and their use of AI/LLM tools across PubMed, PMC, Crossref, or Google Scholar databases.

**Secondary/Supporting presentation** (only when close studies exist):
Present studies from OTHER Malaysian universities using ChatGPT/LLM as `Secondary/Supporting Findings`, with explicit note that they are NOT OUM-specific.

Example secondary finding format:
```
### Secondary/Supporting Finding: ChatGPT usage at Universiti Teknikal Malaysia Melaka (UTM)

**Authors:** Ibrahim, Ismail; Md Saad, Mohd Shamsuri; Rajikon, Muhd Akmal Noor
**Status:** ⚠️ PARTIALLY VERIFIED - ChatGPT study from UTM, NOT OUM (different institution)
**Reason for Partial Match:** This study examined ChatGPT usage among 367 university students, but at Universiti Teknikal Malaysia Melaka (UTM), not Open University Malaysia (OUM). However, it provides the closest available evidence of AI/LLM adoption patterns among Malaysian university students.
**DOI:** https://doi.org/10.47772/ijriss.2024.8120209
**Note:** No studies specifically about OUM students and AI/LLM adoption were found in any indexed database.
```

## Search Heuristics for Niche Topics

1. **Start narrow**: Exact institution + exact instrument + exact population
2. **Search ≥2 independent databases** (PubMed, Crossref, institutional repos)
3. **If zero hits after 5-8 queries**: Report "NO STUDIES FOUND" explicitly — do NOT broaden
4. **Only broaden to "related" studies** if they still meet ≥1 exact criterion (institution + AI topic, even if different instrument)
5. **Always label non-matching studies as Secondary/Supporting** with explicit mismatch note
6. **Never infer or fabricate** that no study exists — be precise about databases searched and date range covered

## Date Range Note

For very recent topics (e.g., ChatGPT launched November 2022), many studies may be preprints or conference papers without formal DOIs. Use OSF Preprints, SSRN, and arXiv as additional sources, but always indicate the publication status transparently.