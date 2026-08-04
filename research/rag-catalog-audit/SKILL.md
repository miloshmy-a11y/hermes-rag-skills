---
name: rag-catalog-audit
description: Randomly audit a RAG literature catalog for metadata errors.
---

# RAG Catalog Audit & Maintenance

## When to use
- User asks to verify/audit catalog records, check for errors, or "randomly check records".
- After any bulk ingest, enrichment pass, or metadata fix — to catch drift before it compounds.
- Recurring maintenance: the user wants ongoing random-record verification of the index.

## Core discipline (load-bearing — these prevent the exact errors found this session)
1. **Random-sample, then verify against the ACTUAL full text** — not against keywords or titles alone. Sample ~10 full-text records per pass; for each, confirm the indexed title, year, country, and `measures` are supported by the real body text.
2. **Never bulk-edit on keyword matches.** A keyword signal (e.g. "Jordan" in a title) is NOT proof of study country. Verify each flagged record individually via the authoritative source BEFORE changing it. This is the single most common catalog-corruption path (it produced 24 false-positive country flags in one pass; only 4 were real).
3. **Authoritative order for verifying a field:**
   - *Metadata (title/authors/year/DOI):* Crossref API (`https://api.crossref.org/works/<DOI>`). Trust Crossref over OpenAlex / Semantic Scholar / PubMed / full-text snippets. Never judge a DOI wrong from fallback text.
   - *Country:* (a) Crossref `author[].affiliation` (most reliable); (b) full-text sentence "conducted in X" / "hospitals in X"; (c) NEVER infer from a country name merely appearing in title/abstract (comparison studies, cited locations) or from a publisher download/access IP (e.g. "Downloaded by NIH Malaysia" ≠ Malaysian study).
   - *Instrument / `measures`:* only record an instrument if it appears in the paper's methods/full text. If the indexed `measures` is a guess (e.g. "stress scale (unspecified)"), correct it from the body (e.g. the Saudi study actually used PSS-10 + ENSS).
4. **Enrich only when it adds value — do NOT pad `keywords_llm` for its own sake.** Add keywords only when the full text/abstract reveals genuinely missing, high-value terms (a real instrument name, the true country). Off-topic or thin records (e.g. a pediatric paper sitting in a nursing-stress catalog) should be LEFT AS-IS, not padded. User explicitly: "don't simply add more keywords just for the sake of doing it."
5. **Ad-hoc verification of any script you write.** Before declaring a fix done, run a read-only check that the catalog JSON still loads, the intended edits persisted, and the script executes without error (see `scripts/audit_random_records.py` — it self-verifies catalog validity).

## Workflow
1. Run `scripts/audit_random_records.py` (read-only) to get a flagged list.
2. For each flag, open the full text and decide: true issue vs false positive.
   - FALSE POSITIVES to ignore: review / meta-analysis / multi-country studies (many country names in text); download-watermark IPs; translated reprints (e.g. German reprint of a US classic → country stays None); `local:` tool docs (PRISMA checklist, consent forms) — exclude these from sampling.
3. Fix only genuine issues: correct `country` (with `country_note` + `country_corrected: true`), correct `measures`, or add a few high-value `keywords_llm`.
4. Save catalog; push to the GitHub backup (if configured) with a descriptive commit.

## Pitfalls (from real session failures)
- **Country keyword = false friend.** "Leadership style & turnover — Jordan" was actually Universiti Tenaga Nasional (Malaysia); "Despotic leadership — Pakistan" was Universiti Utara Malaysia. Both were over-flagged by a title scanner and confirmed MY via Crossref affiliation. See `references/country-verification.md`.
- **Download IP ≠ study country.** A Wiley "Downloaded by National Institutes of Health Malaysia" watermark is NOT evidence the study is Malaysian.
- **`measures` guesses rot.** An earlier enrichment pass left `"stress scale (unspecified)"` on a Saudi study that actually used PSS-10 + ENSS. Always read the methods.
- **Don't re-guess what you just corrected.** Once `measures` is verified from text, leave it.
- **Title-check false negatives:** non-breaking hyphens / em-dashes (e.g. "App‑Based") make naive substring checks fail even when the title IS present. Normalize whitespace/dashes before comparing.

## References
- `references/country-verification.md` — detailed country-disambiguation examples and the authoritative-check order.
- `scripts/audit_random_records.py` — read-only random-sample auditor (reports flags, mutates nothing; self-checks catalog validity).

## Relationship to other skills
Companion to `general-purpose-rag` (ingestion/search) and `rag-verification-protocol` (DOI + content verification). This skill covers *ongoing catalog quality maintenance* after ingest. NOTE: those two are user-owned — if you need to extend them, recommend `hermes curator adopt <name>` rather than patching directly.
