---
name: rag-verification-protocol
description: "Two-factor RAG verification: DOI plus content match."
version: 1.0.0
author: Hermes Agent
license: MIT
---

# RAG Result Verification Protocol v1.0

## Overview
Protocol for verifying that RAG search results are genuinely relevant — not just keyword matches. Applies whenever a user asks for studies matching specific population + concept criteria.

## The Problem This Solves
DOI verification only confirms a citation is real. It says nothing about whether the paper's content matches the queried population and finding.

## Two-Factor Verification (Both Required)

### Factor 1: DOI Verified (Crossref is the authoritative metadata source)
- Crossref returns HTTP 200 for the DOI, and Crossref's returned title/authors/year/journal
  match the catalog entry / the paper it claims to be. **Always resolve the DOI via Crossref**
  (`https://api.crossref.org/works/<DOI>`) — trust Crossref over OpenAlex, Semantic Scholar,
  PubMed, or any retrieved full-text snippet. Do NOT judge a DOI wrong from fallback text
  (S2-page/PubMed can return a wrong record for old/non-biomedical DOIs). Crossref registration
  data is the canonical citation record.
- Confirms the **citation is real AND correctly attributed**.

### Factor 2: Content Verified  
- Population match: actual studied population matches query
- Finding match: concept explicitly reported as significant factor
- Confirms the **content is relevant**

## Common False Positive Patterns
| Pattern | Example | Action |
|---------|---------|--------|
| Instrument on wrong population | NASA-TLX on diabetes | Exclude |
| Term in background only | workload in intro | Exclude |
| Term as survey item | rate your workload | Exclude |
| Explicit "no association" | no link found | Exclude |

## Summary Statement Rules
- "X verified" means ALL X passed DOI + content verification
- Label DOI status and content status distinctly

## Content-Trust Pitfalls (session-hardened 2026-08)

Hard-won lessons from enriching a thesis-cited catalog — encode so they aren't repeated:

- **DOI correctness is Crossref-only, never inferred from retrieved full text.** The S2-page /
  PubMed fallback can return a WRONG record for old/non-biomedical DOIs (Selye 1936, Karasek 1979,
  Gray-Toft & Anderson NSS, French 2000 ENSS all returned garbage fallback text while the DOI was
  correct). Resolve via `https://api.crossref.org/works/<DOI>`; do NOT flag "MISATTRIBUTED-DOI" from
  fallback content. (This is Factor 1 above — stated again because it was violated in practice.)
- **Instrument (`measures`) must be read from the METHODS section, not guessed from the abstract.**
  A Kelantan job-stress study was wrongly indexed as "NSS + HSOPSC" from its abstract, but the body
  says "Expanded Nursing Stress Scales and Safety Attitude Questionnaire" (ENSS + SAQ). Grep the real
  body for scale names (ENSS/NSS/MBI/JCQ/ERI/PSS/SAQ/NAQ-r/HSOPSC); if only an abstract exists, set
  `measures=null` or tag `suspected_abstract_only` — never assert an instrument not seen named in body.
- **ENSS != NSS.** Expanded Nursing Stress Scale (French 2000) vs Nursing Stress Scale
  (Gray-Toft & Anderson 1981) are distinct and routinely conflated by chatbots (ChatGPT/Grok) and
  abstract-readers. When the user says "ENSS study", exclude NSS-only studies from any count.
- **Do NOT infer "first/Nth study in country X using instrument Y" from catalog count.** Discovery
  order is not real-world novelty (a 2022 paper found today doesn't make the user "first" until 2022).
  Verify no other such study exists (broad web search incl. non-OA journals/theses/conference abstracts)
  and confirm the SAME instrument, then scope the claim (e.g. "first in in-patient wards of HSM Perak",
  "first FYP/thesis") rather than state it absolutely.

## Verification discipline: small batches, never one giant pass
A user correction hardened this (2026-08): attempting to "go through ALL records" in one large
batch causes errors to be MISSED — at scale the agent trusts the index / matches keywords and skips
opening the full text, so wrong `country` and guessed `measures` slip through. The errors only
surface when each record is opened and its affiliation sentence is actually read.

- Process records in SMALL chunks (10-25 at a time), verifying EACH against its real full text.
- Random sampling is good for spot-checks but never reaches the long tail; pair it with a FULL
  ORDERED pass (all 252 records in slices) so nothing is left unaudited.
- For catalog hygiene (country/instrument accuracy), see `references/country-audit.md` — it has the
  reusable scanner invocations and the false-positive catalog (reprints, PubMed.gov banners, Wiley
  download watermarks, comparison-country-in-title) that must NOT be "fixed".
- After each batch of fixes, push the catalog to its GitHub backup so progress is never lost.

## Full-text FILE integrity — the file must actually be the right paper
A user correction hardened this (2026-08): *"if full text was wrong, the index record is likely
also wrong, because it's supposed to be a brief extract from the full text/abstract — so verify
both at the same time."* This is the most damaging class of index corruption and it is INVISIBLE
to metadata-only checks: the DOI is correct, Crossref matches, but the stored `extracted_text`
file holds a DIFFERENT document (e.g. the ENSS French-2000 paper stored a p53/breast-cancer
article; Karasek-1979 stored a 2019 HEMS-physicians paper; NSS-1981 stored an HCV article). Any
`brief_abstract` / `keywords_llm` / `measures` derived from that file is then also wrong.

**Co-verify file + indexed fields in ONE pass.** When you open a record to fix anything, do not
treat `country` / `measures` / `brief_abstract` as independent. If the file is wrong, rebuild ALL
of them from an authoritative source (Crossref, or PubMed-by-PMID) in the same edit — never leave a
half-fixed record with a corrected `country` but a `brief_abstract` still derived from the bad file.

**Detecting mismatched files** (reusable: `scripts/audit_fulltext_mismatch.py` for full coverage;
random spot-checks via the catalog's `audit_random_records.py` / `audit_fulltext_doctype.py`):
1. Open `files.extracted_text`; if `<800` bytes OR first 300 chars contain "skip to main content" /
   "this page can't be found" / only a PubMed.gov banner → file is EMPTY/banner-only (not the article).
2. Title-match test: normalize the title (collapse non-breaking hyphens/ampersands), take the 8
   longest content words (drop stopwords + topic words like nurse/stress), require ≥25% present in
   the file text. <25% overlap = LIKELY MISMATCHED file → verify by reading the file head, then rebuild.
3. **PRISMA-template scan (separate — the title test misses these):** scan every file for template
   boilerplate (`tips for reporting this item`, `eligibility criteria with a rationale`, `preferred
   reporting items`, `identify any specific restrictions such as date`) where the paper's title words are
   NOT in the body and the file is `<6000` bytes. These are reporting templates swapped in for the real
   article (confirmed this session: burden-of-treatment, parents/pediatric, self-management). Rebuild from
   EPMC/PubMed. **Always run BOTH scans** (title-overlap + template-signature) on a full-coverage pass.
4. **OUM/coursework wrapper scan (a THIRD, larger class the title test also misses):** scan every file
   for Open University Malaysia student-kit markers (`open university malaysia`, `oumk`, `nbbs`, `nbns`,
   `learning kit`, `matriculation no`, `matrix no`, `final year project submitted`, `project paper submitted`)
   where the paper's title words are NOT in the body and there is no `abstract` near the top. These are
   OUM learning-kit / exam / assignment PDFs swapped in for the real research article (confirmed this
   session: 34 files had OUM markers, 24 still mis-typed as `doc_type=study`). Action: set
   `doc_type=coursework` + `relevance=off_topic`; do NOT keyword them as research. If the indexed DOI is a
   real paper you want, re-fetch its abstract from EPMC and overwrite the file. `local:` instrument/checklist/
   thesis-support docs (STROBE, NASA-TLX forms, NMRR guides) are reference material, not research — they
   legitimately lack `keywords_llm`. **Always run THREE scans** (title-overlap + PRISMA + OUM) on a pass.
   The bundled `scripts/audit_fulltext_mismatch.py` already runs all three + a status/disk check.
4. When a file is confirmed wrong: replace it with Crossref/PubMed-verified metadata (title, journal,
   year, authors) and set `full_text_status` honestly (`meta_only` if only the abstract is available,
   `present` once a real body is acquired). Do NOT invent an abstract — set `brief_abstract` to a
   minimal citation line and clear `keywords_llm`/`measures` until a real body/abstract is in hand.
   After acquiring a new full text, do the comprehensive re-index immediately (same pass), not later.

**Topical RELEVANCE is a separate verification dimension.** Country + file-integrity pass even when a
record is OFF-TOPIC for the user's thesis (pediatric, genetics, COPD, COSMIN reporting-guideline, PRISMA
templates). Add a `relevance` field per record: `off_topic` / `weakly_relevant` / `instrument` / (default
on-topic, untagged). Use `scripts/audit_relevance.py` for random spot-checks; verify every flag by READING
the abstract, never auto-tag from the keyword score. Keep off-topic records (exclude at query time), don't
delete. See `references/fulltext-integrity.md` for the relevance-audit recipe + confirmed off-topic examples
(burden-of-treatment, parents/pediatric, self-management, racism-in-healthcare, COSMIN guideline) and the
weakly-relevant / instrument distinctions (clinical-burnout cognitive function; PSS/ERI papers).

**Full-text false positives that must NOT be "fixed"** (running list in `references/fulltext-integrity.md`):
- PubMed.gov site banner ("official website of the United States government" is page chrome, not the
  study country) — the study's own country comes from its title/affiliation, not the .gov frame.
- Wiley "Downloaded from … NIH Malaysia, Wiley Online Library on [date]" is a download WATERMARK, not
  the study country (and not an article body).
- A PMC article whose head is just the "[Skip to main content]" nav LINK but HAS a real body below is
  CORRECT — do not flag it as empty.
- A `local:` tool/guideline record whose text matches its own title is correct — a verifier keyword
  hitting the record's own title is a false positive in the verifier, not corruption.

**Pitfall — disk/catalog divergence after a crash.** A script that writes extracted-text files to
disk but then raises before its final `json.dump` leaves the catalog JSON OUT OF SYNC with the files
on disk (files are real, but `full_text_status` still says `meta_only`). Always either (a) structure
the file writes + the single `json.dump` so they can't partially fail, or (b) after running, verify
disk-vs-catalog: for each acquired DOI confirm `os.path.getsize(files.extracted_text) > 800` AND the
catalog `full_text_status` matches (`present`/`abstract_only`); re-run the save if they diverge.

**Pitfall — external audit may target a DIFFERENT catalog.** If an external reviewer (e.g. another LLM) hands
you a "critical issues" checklist, FIRST confirm it describes THIS catalog, not a different/wrong file. This
session an external audit claimed 722 docs, `quality_score` tiers, and functions (`add_documents_from_folder`,
`verify_doi_metadata`) that DO NOT EXIST here (real catalog: 526 docs, no such functions/fields). The
*spirit* was valid (bulk-ingestion corruption), but the specific counts/fields were wrong. **Action:** measure
the real catalog yourself (`len(docs)`, field coverage) before acting; verify which field the actual search
code reads (here it is `keywords_llm`, NOT the legacy always-empty `official_keywords`) and backfill THAT.

**Pitfall — DOI-normalization in audit/backfill code.** Catalog stores some DOIs WITH `https://doi.org/` and
some WITHOUT (bare `10.x/...`). Any `by = {d['doi']: d}` dict + lookup will MISS the bare-DOI records. Always
normalize keys: `key = d['doi'].replace('https://doi.org/','').replace('http://doi.org/','').strip()`.

## Support files for this section
- `references/fulltext-integrity.md` — false-positive running list (PubMed.gov banner, Wiley watermark, PMC
  nav-link, German reprint, local-guideline self-match, global-review country) that must NOT be "fixed"; the
  PRISMA-template + OUM/coursework detection recipes; the topical-relevance audit recipe; re-acquisition
  sources (PMC/EPMC/PubMed/Crossref); the RETRIEVAL-FIELD lesson (verify which field the search code reads
  before backfilling); the `verified_at` backfill (cheap, stops re-verification churn); status/disk
  consistency; and the DOI-normalization pitfall.
- `scripts/audit_fulltext_mismatch.py` — re-runnable full-coverage detector: runs empty + title-overlap<25%
  + PRISMA-template + OUM/coursework scans AND a status/disk consistency check. Read its flags, then read
  each flagged file's head to confirm before rebuilding.
- `scripts/audit_relevance.py` — random topical-relevance auditor (nurse/workforce + stress detection;
  flags off-topic candidates for manual abstract read + `relevance` tagging).
