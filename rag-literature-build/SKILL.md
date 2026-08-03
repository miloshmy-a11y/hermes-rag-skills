---
name: rag-literature-build
description: Build and reconcile a local academic-paper RAG catalog.
license: MIT
homepage: https://openalex.org
compatibility: python3, requests, hermes_tools. Windows git-bash needs native Windows paths.
platforms: [macos, linux, windows]
metadata: {"hermes":{"tags":["rag","literature-review","openalex","catalog","citation","research","academic"],"category":"research","requires_tools":["python3"],"related_skills":["general-purpose-rag","openalex-skill","semanticscholar-skill","paper-fetch","verified-academic-research"]},"author":"Hermes Agent","version":"1.0.0"}
---

# RAG Literature Build

Techniques for growing and maintaining a local academic-paper catalog (JSON-based),
verified against Crossref/OpenAlex, with full-text acquisition and clean reconciliation
between sessions. Domain-agnostic; battle-tested on a 435-doc nursing-stress catalog.

## Proven build pipeline (autonomous, verify-as-you-go)
1. **Discover** with OpenAlex (`skills/research/openalex-skill`, `oa.py`):
   `oa_search(q, filters="authorships.institutions.country_code:MY,from_publication_date:2015-01-01,has_doi:true,type:article", per_page=50)`.
   OpenAlex is free, no key, no rate limit, CC0; supports `country_code:MY` (S2 cannot).
   For citation-graph enrichment (who-cites-who, related-paper recommendations) where
   OpenAlex is weaker, the `semanticscholar-skill` now has a configured API key
   (1 req/s, 1.8s gap in `s2.py`) — use `batch_papers`/`get_citations` to stay under limit.
2. **Relevance filter** — keep only titles/abstracts mentioning the target population
   (nurse/nursing/ward/ICU). OpenAlex `abstract_inverted_index` must be reconstructed
   (word→position dict → sorted join) to get readable text.
3. **Dedupe** against existing catalog DOIs (case-insensitive).
4. **Add** as `doc_type:"study"`, assign `domain` (e.g. `Malaysian_Nursing_Studies`),
   `tags` (population + theme), `country`, `citation_count`, `keywords` (from `concepts`).
5. **Full text** — (a) OA ones: direct GET on `oa_url`, validate bytes start with `%PDF`
   and >5 KB; (b) rest: `paper-fetch` (Europe PMC / S2 / Unpaywall / Sci-Hub last-resort).
6. **Integrity check** — 0 duplicate DOIs, no dangling `files.*` paths. Backup after bulk ops.

## Catalog JSON field-safety (CRITICAL — caused false "0 results" + KeyErrors)
The catalog `UNIVERSAL_CATALOG.json` is heterogeneous. NEVER assume keys exist or types:
- `d.get('country')` not `d['country']` — key absent on intl/legacy entries.
- `d.get('id')` not `d['id']` — some entries lack `id`.
- `(d.get('tags') or [])` — `tags` may be None.
- **Tags CASE-SENSITIVE**: `'Malaysia'` ≠ `'malaysia'`. Match: `'malaysia' in [t.lower() for t in (d.get('tags') or [])]`.
- **`year` may be a STRING** — `int(d.get('year') or 0)` before `-year` sort.
- Duplicate `local:...` IDs across domains → suffix with domain when merging.

## Significance-role classification ("factor X as significant" lit reviews)
- `tags`: add `workload`, `workload_factor` (+ `Malaysia` if applicable).
- `workload_role` ∈ {`predictor`, `top_stressor`, `driver`, `influencer`, `factor`, `negative`}.
- `workload_note`: one-line finding. Keep `negative` findings (rule-out a predictor) — do NOT drop.
- Present Malaysian-first, then year desc.

## Cross-session reconciliation
Before trusting "added N new studies": (1) cross-check DOIs vs LIVE catalog; (2) if present,
do NOT re-add — UPGRADE thin copies (fetch full text, re-tag, set country/domain/role);
(3) if missing, add via pipeline + verification; (4) preserve conflicts, never silently overwrite.

## MANDATORY: audit-before-expand sequencing (user correction, 2026-08-03)
When asked to "verify the index, THEN expand / find more", the order is not optional:
1. Run the read-only pass FIRST — `python3 skills/research/rag-catalog-discipline/scripts/audit_studies.py`
   (or the inline verification from step 6 below). Fix incomplete metadata, broken paths,
   mis-typed non-studies, and duplicate DOIs BEFORE touching new discovery.
2. Only after the catalog is clean, run the Discover (OpenAlex) / fresh-search step.
Do NOT interleave expansion with the audit. A prior session expanded first and the user
had to ask twice for the corrected list — deliver the full ranked answer in ONE turn.

## Deliver the ranked list in the FIRST reply (user correction, 2026-08-03)
On "list all studies on X", output the complete ranked table (score = 0.6*relevance +
0.4*significance, see general-purpose-rag Result Ranking; top ~25, with full-text status)
in the same turn you ran the search. Background OA/paper-fetch jobs may continue async,
but the answer to the question must not wait for them.

## MSYS/Windows git-bash path pitfall (recurring)
Python under git-bash mangles `/c/Users/...` → `C:\c\Users\...`. ALWAYS pass NATIVE Windows
paths: script `C:\Users\Milos\...\paper-fetch\scripts\fetch.py`, `--out C:\Users\Milos\...\pf_out`,
feed DOIs via stdin `cat file | python3 <native> --batch - --out <native>`. Never `--batch <msys-path>`.
Not a tool defect — works with native paths.

## Full-text fallback (legal, user-approved non-profit)
OpenAlex `oa_url` → `paper-fetch` (Europe PMC/S2/Unpaywall) → Sci-Hub LAST RESORT (approved).
BMC/Bentham bot-wall PDFs may fail `%PDF` check (HTML redirect) — leave at abstract level.

## Related
`references/catalog_pitfalls.md` — worked field-safety code.
