# Instrument-usage verification — the ENSS case study

## The failure
User asked: "find all studies which used ENSS to measure stress levels among nurses."
Naive approach (keyword/title/`measures` search) returned 7 hits and MISSED 3 genuine users:
- **Vu et al. 2024** `10.1371/journal.pone.0309028` — Vietnam, mean 1.79, COVID-19 nurses.
  ENSS appeared only in methods/results body, not in `keywords_llm`/`title`/`measures`.
- **Sarafis et al. 2016** `10.1186/s12912-016-0178-y` — Greece. Used ENSS + SF-12 + CBI.
- **Werke & Weret 2023** `10.3389/fpubh.2023.1147086` — Ethiopia. Collected via ENSS questionnaire.

A broader full-text scan returned 37 "ENSS mentions" — but most were CITED-ONLY (systematic
reviews, lit-review sentences, the user's own FYP reference list). Only **8** were genuine
ADMINISTERED users (incl. French 2000 CA, Paneerselvam 2022 MY, Harsono 2024 ID, Alqarni 2025 SA,
Chittra 2026 MY).

## The rule
"Used instrument X" = the study ADMINISTERED/COLLECTED/MEASURED via X, not merely cited it.
Never decide from `keywords_llm`/`title`/`measures` alone — deep-scan `extracted_text`.

## ADMINISTERED-vs-CITED regex (Python)
```python
import json, os, re
CAT = r"<CATALOG_PATH>"
docs = json.loads(open(CAT, encoding="utf-8").read())["documents"]
INSTR = "expanded nursing stress scale|enss"   # generalize per instrument
adm, cited = [], []
for d in docs:
    p = (d.get("files") or {}).get("extracted_text")
    if not p or not os.path.exists(p): continue
    t = open(p, encoding="utf-8", errors="ignore").read().lower()
    if not re.search(INSTR, t): continue
    used = re.search(
        r"(administered|used|collected|measured|assessed|employ|utili[sz]ed|completed).{0,40}(" + INSTR + r")", t
    ) or re.search(
        r"(" + INSTR + r").{0,40}(was (used|administered)|to measure|questionnaire|instrument)", t
    )
    (adm if used else cited).append(d.get("doi"))
print("ADMINISTERED:", len(adm), adm)
print("CITED-ONLY (exclude from 'used X'):", len(cited))
```

## How the gaps were caught (the real lesson)
The user said: "you miss the other Malaysian study and I'm almost certain others… see my thesis
where I cite ENSS." The thesis (`local:chittra-thesis-2026-work-stress-hsm`) full text cited
Vu 2024 explicitly ("Vu et al. (2024) reported a lower overall mean score of 1.79"). Extracting
the thesis reference list + in-text ENSS citations is the authoritative seed for "which studies
should be present." Always cross-check the user's own thesis/reference list.

## Country from title when Crossref affiliations are empty
Crossref returned empty `affiliation` for regional journals (Vietnam, Greece, Ethiopia). The
TITLE itself stated the country ("Vietnamese tertiary hospital", "Addis Ababa, Ethiopia",
Greek author surnames). Use title + author nationality, not inference from download IP.

## NSS ≠ ENSS
NSS (Gray-Toft & Anderson 1981) and ENSS (French 2000, expanded) are DISTINCT. The Malaysian ENSS
set = {Paneerselvam 2022, Chittra 2026} only. NSS Malay 2010 validation is a different instrument.
