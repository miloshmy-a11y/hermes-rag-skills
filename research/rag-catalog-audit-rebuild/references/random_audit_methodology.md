# Random small-batch audit + OA re-acquisition — working recipe

Companion to the "Audit methodology" section in SKILL.md. Proven this session on a 526-doc
/ 252-full-text catalog. Goal: drive genuine error rate below 5% (target 0%) on country,
full-text identity, and doc_type — without the blind spots of one giant pass.

## 1. Random sample + per-record verify (the core loop)
Sample 10–12 full-text records at random. For each, check THREE things against the actual file:
- **Identity**: normalized title's content words present in file? (norm apostrophes/dashes; drop
  stopwords + "nurses/nurse/stress"). overlap < 25% => read file head; if it's an unrelated paper,
  publisher cover page, "javascript is disabled" landing, or just a Wiley/PubMed download banner ->
  MISMATCH.
- **Country**: scan affiliation/abstract for a single clear country word. idx contradicts single text
  country -> fix; idx None but one clear country in text -> fix; multi-country (reviews/comparative)
  or "USA dominates" as a *finding* -> leave None (false positive, do NOT flag).
- **doc_type / full_text_status**: doc_type populated & plausible? status matches file size on disk?

Filter false positives BEFORE counting errors:
- German/foreign *reprint* of a classic (Karasek 1979 shows "DE") -> study country is the original, not DE.
- PubMed.gov page banner text ("official website of the United States government") -> not the study country.
- Wiley/Springer "Downloaded from ... NIH Malaysia" watermark -> download IP, NOT study country.
- Reviews where a country appears only as a *conclusion* (e.g. racism review: "USA dominates the research").

## 2. When a file is wrong — fix file + index in ONE pass
Write the correct text (Crossref/PubMed metadata block, or re-fetched OA body), then re-derive from
the AUTHORITATIVE source, never the bad file:
```python
import json, urllib.request, urllib.parse
def crossref(doi):
    req=urllib.request.Request(f"https://api.crossref.org/works/{urllib.parse.quote(doi)}",
                               headers={"User-Agent":"hermes/1.0 (t@e.com)"})
    return json.loads(urllib.request.urlopen(req,timeout=20).read())["message"]
m=crossref(doi)
d["title"]=m["title"][0]; d["journal"]=m["container-title"][0]
d["year"]=int(m["issued"]["date-parts"][0][0])
d["authors"]=[f"{a.get('given','')} {a.get('family','')}".strip() for a in m.get("author",[])]
d["full_text_status"]="meta_only"          # honest: body not yet re-acquired
d["brief_abstract"]=f"{d['journal']} ({d['year']}). {d['title']}."
d["keywords_llm"]=[]; d["measures"]=[]      # cleared from bad text; refill after real body
d["metadata_source"]="Crossref (verified after mismatch fix)"
```
For PubMed-only DOIs (no Crossref), use `eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id=<PMID>&rettype=abstract`.

## 3. OA re-acquisition chain (when user says "get the missing papers")
For each `meta_only`:
1. Europe PMC: `rest/search?query=DOI:<doi>&resultType=core` -> `pmcid` + `abstractText`.
   If `pmcid`: fetch body via `rest/<pmcid>/fullTextXML`, strip `<[^>]+>`, write to file, set
   `full_text_status="present"`.
2. Else if `abstractText` present: write abstract, `full_text_status="abstract_only"`.
3. Semantic Scholar: `api.semanticscholar.org/graph/v1/paper/DOI:<doi>?fields=openAccessPdf`.
4. Unpaywall: `api.unpaywall.org/v2/<doi>?email=...` -> `best_oa_location.url`.
5. Publisher OA PDF: Nature `nature.com/articles/<id>.pdf`; DovePress `getfile.php?fileID=`.
Then **comprehensively re-index** (measures from actual text, doc_type from abstract/methods,
brief_abstract, keywords_llm) in the SAME pass.
- No OA (JSTOR/Springer paywall, foundational classics) -> leave valid `meta_only` with Crossref
  metadata. Don't fabricate. (Per user: "if don't have, nevermind.")

## 4. Verify-before-backup (run a FRESH check, never trust a cached claim)
After all edits, re-read the catalog JSON and assert:
- loads as valid JSON; all docs have id
- 0 wrong-body files (scan for known corrupted signatures: "mutant p53", "breast cancer subtype",
  "hcv care", "hiv-1 pretreatment", "stress load of emergency", "underserved does not mean")
- 0 likely-mismatched (title-overlap<25% on real files)
- status/disk consistent: `present`/`abstract_only` => file on disk >800B; `meta_only` with >5KB file
  = status lag (re-apply + save)
- country: re-run the overlap scan; genuine issues should be ~0% (exclude reviews + FALSE_POS set:
  Karasek 1979, Selye 1936, the SA-WPV PubMed record)

**Save-failure trap**: a script that writes text files to disk but raises before `json.dump` leaves
disk files real but JSON status stale. If any edit script aborted mid-loop, re-apply status updates
and re-save before verifying. Always verify the SAVED file, not the in-memory state.

## 5. Reusable audit scripts (live in the catalog dir, not this skill)
- `audit_random_records.py` — random 10/batch country+title+measures reporter
- `audit_full_coverage.py` — ordered full sweep, country only
- `audit_fulltext_doctype.py` — random batch: file exists? title-in-text? doc_type?
- `audit_fulltext_mismatch.py` — full sweep: empty/mismatched files + doc_type gaps
Copy these into the working catalog folder per session; they read `UNIVERSAL_CATALOG.json` + `EXTRACTED/`.
