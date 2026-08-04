# Country / Geo-Field Audit Technique (catalog hygiene)

## Why this exists
When ingesting a large catalog (OpenAlex / Crossref / bulk import), the `country` field
frequently gets mislabeled: OpenAlex `country_code:MY` is misapplied, comparison countries
in the title get tagged as the study country, publisher landing pages get read as the paper,
and download-IP / PubMed.gov banners ("official website of the United States government")
leak into the text as a false "USA". A wrong `country` silently corrupts any geo-filtered
query (e.g. "Malaysian nurse stress studies"), which is exactly what a thesis literature
review depends on. This was caught repeatedly in a 2026-08 session.

## The technique (systematic, not random)
1. Iterate ALL full-text records in order (not random) in SMALL chunks (~10-25 at a time).
   Random sampling alone never reaches the long tail; a full ordered pass does.
2. For each record, extract the actual affiliation sentence / "conducted in <Country>" /
   author-address block from the real full text (NOT the abstract, NOT the title keyword).
3. Compare against the indexed `country`. Classify:
   - GENUINE FIX: indexed country absent or wrong, and the body shows ONE clear study country.
   - LEAVE NONE (correct): multi-country review/meta-analysis (many countries in text =
     comparative); "X dominates the research" is a FINDING not the study country; foundational
     instrument papers where the text country is a reprint/translation (e.g. Karasek 1979 "DE" =
     German reprint of a US paper).
   - FALSE POSITIVE (skip): comparison country named in title; PubMed.gov banner; Wiley download
     watermark ("downloaded from ... Wiley ... NIH Malaysia" = reader's institution, not study
     country); author affiliation country differs from where data was collected (verify METHODS).
4. Resolve ambiguous ones via Crossref affiliation as tie-breaker, but prefer the paper body.
5. After each chunk, push the catalog to backup so progress is never lost.

## Reusable scanner
`audit_full_coverage.py` (lives in the catalog dir) does steps 1-3 over a slice [start:end]
and prints only GENUINE issues, with a FALSE_POS set already excluding known reprint/banner
DOIs. Run: `python audit_full_coverage.py 0 25` then `25 50` ... until 252.
Also `audit_random_records.py` for ad-hoc spot-checks. Both are READ-ONLY reporters — they
do NOT mutate the catalog; the agent reviews flags and applies fixes.

## FALSE-POSITIVE CATALOG (do NOT "fix" these — they are correct as-is)
| Signal in text | Actual status | Why |
|---|---|---|
| "united states government" / PubMed.gov banner | not a country | site chrome, not the study |
| German/French reprint of a classic (Karasek 1979 -> DE, Selye 1936 -> ET in a citation) | original country | translation/reprint, not study location |
| "USA dominates the research" in a scoping review | None (review) | finding, not study country |
| Wiley download line "NIH Malaysia" | None | reader's institution IP, not study |
| Comparison countries in title (cross-national study) | None or lead country | the study isn't "of" that country |
| Author affiliation in X but data collected in Y | verify METHODS | affiliation != study population |

## Result from the 2026-08 session
Bulk scanner initially claimed ~12.7% "missing country" but most were false positives.
After a full ordered pass with per-record body verification: genuine country errors dropped to
~0.4% (1 record intentionally left None = global review). 53 country corrections total, all
text-verified. Lesson: trust the body, not the keyword scan; always open the full text.
