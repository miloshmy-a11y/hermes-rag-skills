# Technique: Full-text mismatch detection & one-pass repair

Condensed from a real session auditing a 526-doc nursing-stress RAG catalog (252 with full text).

## The failure mode
Bulk PDF extraction silently **swapped files**: the extracted text for one DOI held a
completely unrelated paper. Observed swaps:
- ENSS (French 2000, `10.1891/1061-3749.8.2.161`) → p53/breast-cancer article
- Karasek 1979 JCQ (`10.2307/2392498`) → 2019 "Stress load of emergency service… HEMS physicians"
- NSS (Gray-Toft 1981, `10.1007/bf01321348`) → "HCV Care in the Safety Net" (2018)
- Selye 1936 (`10.1038/138032a0`) → HIV-1 pretreatment resistance (2023)
- Palliative guideline (`10.7326/...-00009`) → Alberta LPN self-study course
- Rapid-review methods (`10.1186/s12916-015-0465-6`) → a review-template doc
- Lifestyle factors (`10.1007/s12529-013-9298-x`) → a "physical examination" textbook chapter

Because `brief_abstract`/`keywords_llm`/`measures` are derived FROM the extracted text,
every one of these also had wrong indexed metadata. **Fix file + index together.**

## Detection (title-overlap test)
Normalize title (replace `\u00a0 \u2010-\u2015 \u2212 &` → `-`), take significant words (len≥4,
drop stopwords + generic "nurse/stress"), check ≥25% appear in the text. Below → mismatch.
Also flag: size<800B, "this page can't be found", "Skip to main content" (PubMed banner),
"Javascript is currently disabled" (failed scrape).

## Repair (one pass per record)
```python
m = crossref(doi)                       # authoritative, not the bad file
title = m['title'][0]; journal = m['container-title'][0]
year  = m['issued']['date-parts'][0][0]
authors = [f"{a.get('given','')} {a.get('family','')}".strip() for a in m['author']]
write(file, f"{title}\n{journal}, {year}. DOI: {doi}\nAuthors: {authors}\n\nNOTE: mismatched file replaced {date}; rebuilt from Crossref.")
rec.update(title=title, journal=journal, year=int(year), authors=authors,
           full_text_status="meta_only",
           brief_abstract=f"{journal} ({year}). {title}.",
           keywords_llm=[], measures=[],
           metadata_source="Crossref (verified <date> after mismatch fix)")
```
For PubMed-URL DOIs (e.g. `https://pubmed.ncbi.nlm.nih.gov/41069779/`), use
`efetch.fcgi?db=pubmed&id=<pmid>&rettype=abstract` instead of Crossref.

## Country verification — read the AFFILIATION, not title keywords
Title/country-word scanning produces false positives (comparison countries, cited places).
Read the affiliation sentence: "...University of Hail, Saudi Arabia" → SA. Confirmed fixes:
US (UCSF, Ohio State, UMass Lowell, Yale), SA (Hail, Riyadh), MY (Kelantan, OUM),
JO (Zarqa, Jordan Univ), IL (northern Israel — NOT Pakistan/Saudi), GR, DE, IR, CN, AU, BR, CA.

## False positives to NOT "correct"
- Karasek 1979 text "DE" = German *reprint*, study is US → keep None/US.
- Selye 1936 text "Ethiopia" = a citation, not the study.
- Review text "The USA dominates the research" = a *finding*, not study country → keep None.
- Multi-country validation/comparative studies → None correct.
- PubMed.gov "United States government" banner ≠ study country (it's the site chrome).

## Result
13 corrupted full-text files found via full-coverage sweep (5.2% of 252 with text);
all repaired file+index in one pass → 0 wrong-body files remaining. 12 left as honest
`meta_only` placeholders (correct Crossref citation, body not yet re-acquired) — not errors.
