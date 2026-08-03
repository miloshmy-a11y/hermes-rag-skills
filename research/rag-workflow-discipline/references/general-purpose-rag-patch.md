# Patch text for general-purpose-rag (user-owned — apply after `hermes curator adopt general-purpose-rag`)

The base `general-purpose-rag` SKILL.md already has the Crossref-authority and
full-text-sufficiency rules (added 2026-08-03). The following four WORKFLOW rules
are captured in the `rag-workflow-discipline` skill and should be merged into
`general-purpose-rag`'s "Key Process Decisions" block (currently items 1-5) so they
live with the engine. After adopting the skill, append these items to that block:

```
6. **Thesis-first / citation-driven scope (USER WORKFLOW RULE):** When the user has a
   thesis/bibliography, ALWAYS read it FIRST and harvest its reference list (DOIs), then
   only fetch/enrich the *cited* studies. Do NOT blindly open the whole catalog (e.g. 300+
   PDFs). The cited subset is the correct unit of work. (User correction 2026-08-03.)
7. **Extraction ≠ Enrichment (do NOT claim "complete"):** Downloading/extracting a PDF only
   puts text on disk. The index is not enriched until the LLM has READ the text and written
   `keywords_llm` / `brief_abstract` / `measures`. Never report "all full texts
   extracted/complete" as if the index is enriched — check `keywords_llm` population first.
   (Session lesson: a 314-file extraction was wrongly called "complete"; 55 thesis-cited
   studies still lacked real text + 52 lacked keywords_llm.)
8. **Use the web-acquisition skills, not ad-hoc web_search:** For gap-fill discovery/
   acquisition, load and use `openalex-skill` (OpenAlex, primary discovery),
   `semanticscholar-skill` (S2 paperId for paywalled), `arxiv` (preprints), and `paper-fetch`
   — NOT bare `web_search`. The skills encode the verified legal OA chain
   (fulltext-retrieval-priority.md). (User reminder 2026-08-03.)
9. **Prefer reviews for global / gap-fill evidence (USER EVIDENCE PREFERENCE):** When
   gathering additional or *global* evidence (especially to fill catalog gaps beyond the
   user's own thesis), lead with REVIEWS — systematic review / meta-analysis / umbrella
   review — over primary studies. (User stated this explicitly after praising web-found
   reviews.)
```

Also add to the master `rag` SKILL.md Verification discipline / routing, mirroring the same
items, so the router enforces them even when general-purpose-rag is not the loaded sub-skill.
