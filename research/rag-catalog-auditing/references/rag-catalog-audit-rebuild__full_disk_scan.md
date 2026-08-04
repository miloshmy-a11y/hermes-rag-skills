# Full-disk scan recipe (peer-reviewed article harvest)

Goal: pull every real study PDF from the user's research subtree into the catalog, deduplicated and
Crossref-verified, without polluting it with course notes / ebooks / forms.

## Phase A — extract text (run via terminal; pdftotext absolute path)
```
PDFTO="C:/Users/Milos/scoop/apps/git/2.52.0/mingw64/bin/pdftotext.exe"
for each pdf under <YOUR_WORK_FOLDER>/OUM and <YOUR_WORK_FOLDER>/mendeley import:
    subprocess.run([PDFTO,'-q',src, txtp], timeout=60)
# keep txt in DISK_TEXT/ so re-runs are instant
```

## Phase B — classify + merge (run via execute_code with runpy.run_path)
For each `DISK_TEXT/*.txt`:
1. `doi = re.search(r'10\.\d{4,9}/[^\s"\'<>]+', full_text)`  # WHOLE text, not first 8k
2. if doi:
     if doi.lower() in catalog_dois: continue            # real dedup
     cr = crossref(doi)                                   # api.crossref.org/works/<doi>
     if cr.ok: ADD study {title,authors,year,journal from cr, doi, verification:'VERIFIED (Crossref)'}
     else: skip                            # malformed DOI, don't fake it
3. else (no DOI):
     if not (abstract in first 4k AND references in last 5k): skip
     if course/ebook/form junk regex matches: skip
     ADD study {clean_title, doi:'local:<key>', verification:'LOCAL (no DOI) — unverified'}
4. skip landing pages: 'see discussions, stats', 'log in to a free account'

## Pitfalls that burned a revert this session
- Naive "abstract+refs -> study" mislabels anatomy lectures / ebooks / declaration forms as studies.
  => DOI-first. Crossref gives authoritative metadata; no-DOI only if genuine article shape.
- `find_doi` limited to first 8000 chars missed 63/226 DOIs. => search whole text.
- Bad title extraction (filename fragment "708410 NSQXXX10.1177/...") caused false "dup" skips.
  => trust Crossref title when a DOI exists; only heuristic-title the no-DOI ones.
- If a pass pollutes the catalog: `cp` backup, restore, rerun — don't edit junk in place.

## Outcome (this session)
369 docs total / 256 studies (241 Crossref-verified) / 44 instruments / 0 duplicate DOIs.
User expectation "~100-200 peer-reviewed articles" met.
