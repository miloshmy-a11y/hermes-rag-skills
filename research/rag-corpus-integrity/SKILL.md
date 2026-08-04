---
name: rag-corpus-integrity
description: Detect and repair mismatched or empty RAG corpus files.
category: research
---

# RAG Corpus Integrity Audit & Repair

## When to use
- After a bulk PDF/full-text extraction pass (files get **swapped** — a real, observed failure: an ENSS paper's file held a p53 article; Karasek 1979 held a 2019 HEMS-physicians paper; NSS 1981 held an HCV article).
- Before answering a literature query where you rely on `brief_abstract` / `keywords_llm` / `measures` — those fields are **derived from the extracted text**, so a wrong file silently poisons them.
- When the user says "verify the index," "check for errors," or "audit random records."

## THE CORE PRINCIPLE (load-bearing)
**If the full text is wrong, the index record derived from it is also wrong. Fix BOTH in one pass — do not fix only the file or only the metadata.**

Concretely, for any corrupted record:
1. Replace the `extracted_text` file with **Crossref/PubMed-verified** content (title + journal + year + authors + real abstract if available).
2. **Re-derive** `title`, `journal`, `year`, `authors`, `brief_abstract` from that authoritative source — NOT from the old bad file.
3. **Clear** `keywords_llm` and `measures` that were derived from the wrong text; refill them only after a real body/abstract is acquired. Never invent an abstract — set `full_text_status: meta_only` and write a one-line honest citation as `brief_abstract`.
4. Set `metadata_source: "Crossref (verified <date> after mismatch fix)"`.

## Verification workflow (small batches, not one giant pass)
The user observed: large batch passes miss errors; **random/small (~10-record) verified batches catch them**. Process records in chunks of ~10–12, reading each flagged file's head to confirm it's the RIGHT paper.

For each record with an `extracted_text`:
1. **Exists & real?** size < 800B, or contains "this page can't be found" / "Skip to main content" / "Javascript is currently disabled" → empty/failed scrape.
2. **Right paper?** Normalize title (replace non-breaking spaces, hyphens, `&amp;`) and test whether ≥25% of its significant words appear in the text. Below that → likely a **mismatched file**.
3. **PubMed.gov banner trap:** a file beginning "Skip to main content … An official website of the United States government" is the *site chrome*, not the article — the study country is NOT "US" from that; re-fetch from PMC.
4. **Country:** read the affiliation sentence ("University of X, City, COUNTRY"). Filter false positives: German reprint of a US paper (text shows DE but study is US); download-IP/"NIH Malaysia" watermark ≠ study country; multi-country author lists for reviews (leave `None`).

## False-positive filters (do NOT "fix" these — they are correct)
- `10.2307/2392498` (Karasek 1979): text shows "DE" = German reprint → keep `None` (or US if verified).
- `10.1038/138032a0` (Selye 1936): "ET"/"Ethiopia" in text = a citation, not the study.
- A scoping/systematic review whose text says "The USA dominates the research" → that's a *finding*, not the study country → keep `None`.
- Multi-country validation/comparative studies → `None` is correct.

## Reusable scripts (in `scripts/`)
- `audit_fulltext_mismatch.py` — full-coverage detector: flags empty/placeholder and title-overlap<25% (mismatched) files across all full-text records. Read-only report.
- `fix_record_from_crossref.py <DOI>` — rebuilds the file + indexed fields for one DOI from Crossref (or PubMed for PubMed-URL DOIs). One-pass fix.
- `dedup_check.py [catalog.json]` — **duplicate detector (READ-ONLY report)**. Flags exact DOI collisions, same-title/different-DOI pairs, and Jaccard>=0.6 near-dup titles, and classifies each with the correct action. Run this BEFORE any dedupe pass.

## Duplicate detection & SAFE MERGE (validated lesson, 2026-08-04)
**Two records sharing a DOI is NOT automatically a true duplicate.** Either:
(a) they are the **same study under two DOIs** (preprint `10.21203/rs.3.rs-…` ↔ published `10.1136/…` — merge), or
(b) they are **DIFFERENT studies where one carries a WRONG DOI** (a different paper cloned a real DOI) — these must be **FLAGGED FOR REVIEW, never deleted**.

**Workflow (loop until the catalog is stable, then re-run `dedup_check.py` to confirm 0 hazards):**
1. Run `dedup_check.py` to enumerate candidates.
2. For each candidate, **verify by title + authors + year**, not by DOI alone:
   - Same title/authors/year but different DOI → **TRUE DUPLICATE** → merge.
   - Different title/authors but same DOI → **WRONG DOI on one record** → flag for human review; do NOT delete.
3. **Merge recipe (true dup only):** keep the **published/canonical DOI**; backfill any field the canonical lacks from the stub; remove the stub; set `merged_from: <removed-doi>` + `merge_note:` on the canonical for traceability. Always backup the catalog first.
4. **Re-run `dedup_check.py`** after edits — assert 0 DOI collisions and 0 same-title/diff-DOI pairs. If a wrong-DOI-different-study case is simulated, assert it is *detected* (routed to review), not silently dropped.
5. **Preprint↔published pairs** are the most common true-dup shape: identical title + same author set + same year, one DOI on a preprint server. Merge to the journal DOI.

**Pitfalls:**
- ❌ Never delete both records of a "duplicate" or blindly keep the first by DOI order.
- ❌ Never assume a shared DOI means identical content — the wrong-DOI-on-different-study case is real and deletion loses a genuine paper.
- ✅ Keep merge provenance (`merged_from`) so audits can reconstruct why a record vanished.

## Pitfalls
- **Never trust keyword co-occurrence for country** — comparison countries and cited locations inflate false positives. Verify via affiliation, not title scanning.
- **Never judge a DOI wrong from fallback full text** — resolve the DOI via Crossref first (established rule). A 404/failed S2 fetch is not proof the DOI is bad.
- **Don't pad `keywords_llm` just to fill it** — only add keywords from real abstract/body. Off-topic records should be left thin, not force-enriched.
- **Backup before bulk edits:** the catalog JSON is the source of truth; commit/push to its GitHub backup after each audit round.

## See also
`references/technique.md` for worked examples from a real audit session (13 corrupted files found & repaired, error rate 5.2% → 0% corrupted).
