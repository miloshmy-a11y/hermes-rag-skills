---
name: rag-workflow-discipline
description: "RAG catalog workflow rules for this user."
version: 1.0.0
author: Hermes Agent
license: MIT
---

# RAG Workflow Discipline (user-specific, class-level)

These are workflow corrections the user issued during real catalog work (2026-08-03).
They are NOT in the base general-purpose-rag skill and must be followed for this user.
Several also belong in `general-purpose-rag`/master `rag` SKILL.md — see
`references/general-purpose-rag-patch.md` for ready-to-apply text (those skills are
user-owned; run `hermes curator adopt general-purpose-rag` first, then apply).

## 1. Thesis-first / citation-driven scope
When the user has a thesis or bibliography, **read it FIRST** and harvest its reference
list (DOIs). Then only fetch / enrich the *cited* studies. Do NOT blindly open the whole
catalog (e.g. 300+ PDFs). The cited subset is the correct unit of work — it avoids wasted
retrieval and keeps enrichment on-topic.
- Practical: parse the FYP/reference section for DOIs, cross-check against the catalog,
  and only run acquisition/enrichment on the gap (cited-but-no-full-text).

## 2. Extraction ≠ Enrichment (never claim "complete")
Downloading + text-extracting a PDF only puts bytes on disk. The index is NOT enriched
until the LLM has READ the text and written `keywords_llm` / `brief_abstract` /
`measures`. Before reporting "all full texts extracted/complete", check the
`keywords_llm` population — empty `keywords_llm` means unenriched.
- Real failure this session: 314 files were "extracted" but wrongly called complete;
  55 thesis-cited studies still lacked real text and 52 lacked `keywords_llm`. The fix was
  a per-doc LLM read in batches, writing content-derived keywords.

## 3. Prefer reviews for global / gap-fill evidence
When gathering *additional* or *global* evidence — especially to fill catalog gaps beyond
the user's own thesis — lead with REVIEWS (systematic review / meta-analysis / umbrella
review) over primary studies. The user explicitly stated this after praising web-found
reviews. Surface reviews first in global-evidence answers.

## 4. Use the web-acquisition skills, not ad-hoc web_search
For gap-fill discovery/acquisition, load and use `openalex-skill` (OpenAlex = primary
discovery), `semanticscholar-skill` (S2 paperId for paywalled), `arxiv` (preprints),
`paper-fetch`. Do NOT fall back to bare `web_search`. The skills encode the verified legal
OA chain (fulltext-retrieval-priority.md).

## 5. Crossref is the citation/metadata authority (reminder)
Resolve every DOI via Crossref (`https://api.crossref.org/works/<DOI>`) and trust its
title/authors/year over OpenAlex/S2/PubMed/full-text snippets. Never judge a DOI wrong
from retrieved fallback text (S2/PubMed can return a wrong record for old/non-biomedical
DOIs). For foundational/seminal works, an abstract or secondary snippet is sufficient —
store `full_text_status: meta_only`/`abstract_only`, don't chase the full body.

## Shared References
- `references/general-purpose-rag-patch.md` — exact patch text to fold rules 1-4 into
  `general-purpose-rag` SKILL.md (apply after `hermes curator adopt general-purpose-rag`).
