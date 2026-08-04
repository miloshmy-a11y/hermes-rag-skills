# Local Catalog Hybrid Search + APA 7th Output

When the user has a local JSON catalog (e.g. `UNIVERSAL_CATALOG.json` with a `documents[]`
array, each entry carrying `title / authors / year / doi / journal / abstract /
official_keywords / inferred_tags / verification_status / files`), support fast
relevant-study retrieval AND APA 7th reference output with this pattern. This is the
"use" stage after a rebuild/audit (see `rag-catalog-audit-rebuild`).

## 1. Query expansion (context-aware, not a static dictionary alone)
Expand the user's query tokens with domain synonyms BEFORE matching. Example dictionary
(nursing-stress domain — adapt per user topic):

```python
EXPANSION = {
  'workload':   ['work load','caseload','staffing','patient load','demand'],
  'burnout':    ['exhaustion','maslach','depersonalization','burn-out','cynicism'],
  'stress':     ['stressors','strain','distress','pressure'],
  'nurses':     ['nursing','nurse','ward','clinical staff'],
  'malaysia':   ['malaysian','kuala','selangor','sabah','sarawak','hsm','seri manjung'],
  'job satisfaction': ['js','satisfaction','morale'],
  'shift':      ['night shift','rotating','roster','schedule'],
  'enns':       ['expanded nursing stress scale','nursing stress scale'],
  'eri':        ['effort reward imbalance','siegrist'],
  'discrimination': ['bias','inequity','fairness'],
  'patient safety': ['medication error','safety culture','adverse event'],
  'intention to leave': ['turnover','retention','quit'],
}
```

Let Claude decide additional expansion terms per query when local results are thin
(<5) — do NOT hard-code every topic.

## 2. Scored match
Build a lowercase blob per entry = `title + abstract + official_keywords + inferred_tags + journal`.
For each expanded term present, add weight **3 if in title else 1**. Rank descending.
Filter to `doc_type == 'study'` by default so instruments / assignments / forms never
pollute "studies" results (pass `require_study=False` only when the user wants scales/books too).

## 3. Two-factor verification (MUST report both, from `rag-verification-protocol`)
- **DOI verified** — Crossref resolves, metadata matches.
- **Content verified** — studied population matches (nurses, not diabetes patients) AND the
  factor is reported as a significant finding, not a background keyword or a survey item.
Exclude false positives: instrument validated on wrong population, term-in-intro-only,
explicit "no association".

## 4. APA 7th generation from catalog fields
Format: `Author, A. A., Author, B. B., & Author, C. C. (Year). Title. *Journal*. https://doi.org/XX`
- Author list: last name + first initial; up to 20 authors; `&` before final.
- Article title: sentence case. Journal: title case + italics. Volume: italics.
- DOI: always `https://doi.org/<doi>` prefix, PLAIN TEXT (never hyperlink-wrapped).
- If `doi` is `local:...` (no real DOI), output the official URL or flag `CITED ONLY`.

## 5. Worked example (nursing-stress catalog)
Query: *"workload and burnout among nurses in Malaysia"*
→ expansion adds maslach/exhaustion, malaysian/kuala/hsm, caseload/staffing
→ top hits: Zakaria 2022 (BMJ Open), Lee 2024 (SAGE Open Nursing), Majid 2024 — all
  `doc_type=='study'`, all Crossref-verified, returned as an APA 7th list.

## 6. Environment note
Any `web_extract`-based fetching (to backfill abstracts/keywords) runs ONLY inside
`execute_code` (`from hermes_tools import web_extract`) — NOT terminal Python
(`ModuleNotFoundError: hermes_tools`). Batch ≤5 DOIs per `execute_code` call.
