# Instrument Indexing — technique reference

Problem: a query like "NSS among nurses in Malaysia" returns generic stress studies, not
studies that *used* the Nursing Stress Scale. Cause: `measures`/`instrument` fields were
never populated during ingestion, so search fell back to brittle abstract-substring matching
("nurses"⊂"nursess…", ENSS vs NSS confusion).

## Fix (implemented in this project's precise_search.py + catalog)

### 1. One-time scan: populate `measures` from full text
For every full-text study since 2020 on disk, scan the extracted `.txt` and tag instruments
with a heuristic dictionary. Canonical name → phrase variants (regex for acronyms):

```
INSTRUMENTS = {
  "Nursing Stress Scale (NSS)":        ["nursing stress scale", r"\bnss\b"],
  "Expanded Nursing Stress Scale (ENSS)":["expanded nursing stress scale", r"\benss\b"],
  "Brief Nursing Stress Scale":         ["brief nursing stress scale"],
  "Maslach Burnout Inventory (MBI)":   ["maslach burnout inventory", r"\bmbi\b", "burnout inventory"],
  "Copenhagen Burnout Inventory (CBI)": ["copenhagen burnout inventory", r"\bcbi\b"],
  "Professional Quality of Life (ProQOL)":["professional quality of life", r"\bproqol\b"],
  "Connor-Davidson Resilience (CD-RISC)":["connor davidson resilience", r"\bcd-risc\b"],
  "Perceived Stress Scale (PSS)":       ["perceived stress scale", r"\bpss\b"],
  "Patient Safety Culture (HSOPSC)":    ["hospital survey on patient safety", "safety culture"],
  "Safety Attitude Questionnaire (SAQ)":["safety attitude questionnaire", r"\bsaq\b"],
  "Turnover Intention":                 ["turnover intention", "intention to leave"],
  "Workload (NASA-TLX)":               ["nasa-tlx", "nasa tlx", "task load index"],
  # ... extend as needed; variant lists are the only vocabulary that lives in code.
}
```

For each doc: `hits = [canon for canon, variants in INSTRUMENTS if any(v in text for v in variants)]`
then set `d["measures"] = hits; d["instrument"] = hits`. Backup the catalog before overwriting.

### 2. Query-time: detect + boost
`INSTRUMENT_DETECT` (same canonical → variants) is checked against the *query*. If the query
names an instrument, `precise_search._search_index` adds `+5.0` to the score of any study whose
`measures` contains it, and `judge_results` forces those to ON_TOPIC and sorts them first. So an
instrument query surfaces instrument USERS at the top instead of generic text matches.

### 3. LLM is the final judge
`judge_results` attaches an `evidence` block to each result (title, year, population, measures,
abstract snippet, full-text-available flag, plain-language reason). The agent MUST re-adjudicate
using that evidence (real abstract/metadata/full text) before citing — the regex is first-pass only.

## Verification recipe (ad-hoc, not a CI suite)
Run a query for each instrument and assert the top results are instrument-tagged:
- "Nursing Stress Scale NSS among nurses in Malaysia" → ≥3 NSS-tagged in top 6, #1 is NSS.
- "Maslach Burnout Inventory MBI among nurses" → MBI-tagged present.
- "find me an ebook about stress" → ref_intent True, reference doc leads.
If #1 is a non-instrument generic study, the `REF_INTENT` regex is eating the query
(bare `scale`/`measure` in the pattern) — narrow it to explicit object words.
