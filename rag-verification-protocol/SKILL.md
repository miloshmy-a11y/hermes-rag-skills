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
