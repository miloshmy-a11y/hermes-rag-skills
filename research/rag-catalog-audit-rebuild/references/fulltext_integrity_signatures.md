# Full-text integrity signatures + field backfill recipes

Companion to `random_audit_methodology.md`. Encodes corruption classes and field-backfill
discipline discovered in a later session (526-doc catalog). The title-overlap detector in
`audit_fulltext_mismatch.py` MISSES some classes because the wrong file's body doesn't contain
the paper's title — so a dedicated signature scan is required.

## 1. Mismatch signatures the title-overlap check misses

### A. PRISMA / scoping-review TEMPLATE swapped for the article
The file body is the PRISMA/PRISMA-ScR/ARKS reporting *template* (boilerplate "Tips for reporting
this item…"), NOT the actual article. The detector misses it because the template text is long and
may incidentally contain some title words. This was a SYSTEMIC ingestion bug — a whole cluster of
scoping-review articles had their template saved instead of the article body.
- **Detect**: `if any(s in t.lower() for s in ["tips for reporting this item","eligibility criteria with a rationale","preferred reporting items","identify any specific restrictions such as date","data charting form"]) and title_not_in_text and len(t) < 8000`
- **Fix**: fetch real abstract from Europe PMC `rest/search?query=DOI:<doi>&resultType=core` →
  `abstractText`; overwrite file; set `full_text_status="abstract_only"`. Then write genuine
  `keywords_llm` from the real abstract. (These are methodology/knowledge-synthesis papers — keyword
  them accurately, do NOT force nurse-stress terms onto a PRISMA-methodology article.)

### B. OUM coursework / student-assignment WRAPPER swapped for the article
The file is a student's assignment/FP/FYP wrapper (Chittra Selvi, Badrul Hisham, MPU ethics modules),
not the published paper. Signals: "open university malaysia", "oum", "chittra selvi", "badrul hisham",
"final year project", "project paper submitted", "assignment 3", "matrix no", "learning centre",
"appreciation of ethics". These `doc_type:study` records have files that are student material.
- **Detect**: same signals + "abstract" NOT in first 2000 chars.
- **Fix if DOI resolvable**: fetch real EPMC abstract, replace file, re-derive indexed fields from
  Crossref (clear the false `off_topic` if it's real research). **If no OA** (OUM/local journal):
  set `doc_type="coursework"`, `relevance="off_topic"`, note it's student material; leave the file
  as-is (not retrievable research).

### C. status=present but NO file on disk
`files.extracted_text` is None (or path missing) but `full_text_status="present"`. Ingestion
indexed metadata but never wrote the text path. These are usually reference/tool/ebook docs that are
off-topic for a thesis catalog anyway (SOPs, academic-writing ebooks, image galleries, biology
textbooks).
- **Fix**: search EXTRACTED/SOURCE_TEXT for the DOI slug; if truly absent, set `full_text_status=
  "meta_only"` + `relevance="off_topic"` (honest: no text here) and note it. Do NOT chase nonexistent
  files.

### D. Publisher cover page / failed-scrape landing
"Javascript is currently disabled", "Skip to main content", "© College of Licensed Practical
Nurses" cover pages, or PubMed.gov banner only. Detected by the title-overlap check (<25%) — read
head to confirm, then rebuild from Crossref/PubMed.

## 2. `keywords_llm` backfill discipline (USER-ENFORCED)
The user explicitly required: open the full text / abstract, **carefully analyze and summarize**, and
select the most relevant keywords for later search — NOT a scripted frequency dump, NOT padding.
- Backfill in **small verified batches (10–15 records)**. For each, READ the abstract/body, then write
  5–12 `keywords_llm` derived from title + abstract + official keywords + actual instruments used.
- **Do NOT keyword a corrupted/mismatched file** — fix the file FIRST (signatures A–D), then keyword
  the corrected content. Keywording a PRISMA template or coursework wrapper poisons the index.
- Per-study, topic-agnostic: do not hardcode a stress vocabulary. A job-engagement study using UWES/MBI
  gets those terms; a PRISMA-methodology article gets methodology terms.
- Sequence the user endorsed: **(B) first backfill `verified_at` (cheap, no API)** → then expand to
  opening full text and carefully keywording the remaining missing ones. Leave `official_keywords`
  (legacy, unused by this catalog's search) alone unless a consumer actually reads it.
- Coverage target: push toward ~100% on the research (`doc_type:study`) subset; `local:`/coursework/
  tool docs can be title-only or skipped.

## 3. `verified_at` backfill (stops re-verification churn)
`universal_rag.py`'s `_is_recently_verified()` returns False when `verified_at` is missing → every
VERIFIED doc gets re-verified against Crossref on every search (needless API churn). In this catalog
239 VERIFIED docs lacked `verified_at`.
- **Fix**: for every doc with `verification_status` starting "VERIFIED" and no `verified_at`, set
  `verified_at` to a timestamp ~20 days ago (inside the 30-day window). No API calls needed.
```python
from datetime import datetime, timedelta
anchor=(datetime.now()-timedelta(days=20)).isoformat()
for d in docs:
    if (d.get("verification_status") or "").startswith("VERIFIED") and not d.get("verified_at"):
        d["verified_at"]=anchor
```
- Note: an EXTERNAL audit report may cite wrong numbers (e.g. "186/201 VERIFIED missing verified_at",
  "722 documents", "quality_score field") because it reviewed a DIFFERENT catalog/codebase. Always
  verify the ACTUAL file's field coverage yourself before acting (see §4).

## 4. Relevance tagging (query-filter dimension, distinct from doc_type)
Add `relevance` to records so thesis queries can exclude noise:
- `off_topic` — not nurse occupational stress (racism-in-healthcare systems review, patient
  treatment-burden, pediatric parenting, self-management goal-setting, COSMIN/PROM reporting
  guidelines, PRISMA templates, OUM coursework, reference/tool docs).
- `weakly_relevant` — workforce-adjacent but not nurse-specific (e.g. clinical-population burnout
  review).
- `instrument` — a measurement-tool paper relevant as a tool (e.g. PSS psychometric paper).
- Filter `relevance=off_topic` out of thesis searches; keep the record (don't delete).
- **Off-topic ≠ wrong file.** Tag off_topic only after reading; a paper can be both off_topic AND
  mismatch-fixed (fix the file, then tag).

## 5. TRAP — external audit reports may target a different system
If the user pastes a review from another agent (Claude/ChatGPT) claiming "722 documents",
"quality_score", "add_documents_from_folder()", "domain: OUM_Research" — those functions/fields may
not exist in THIS catalog. Verify before acting:
1. Count the real docs (`len(data["documents"])`) — this catalog had 526, not 722.
2. Check which claimed fields actually exist (`any(f in d for d in docs)`).
3. Grep the actual search code to see which fields it reads (`official_keywords` IS read by
   `general_rag.py`/`hybrid_search.py`; `quality_score` does NOT exist here).
4. Act only on the points that are REAL for this catalog; explicitly tell the user which claims were
   from a different codebase. The *spirit* (bulk-ingestion left quality gaps) may be valid even when
   the specifics are wrong.
