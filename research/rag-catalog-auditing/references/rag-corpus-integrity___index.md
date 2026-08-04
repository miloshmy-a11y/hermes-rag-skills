# rag-corpus-integrity — file index

- `SKILL.md` — when-to-use, core principle (fix file + index in one pass), small-batch workflow, false-positive filters, pitfalls.
- `references/technique.md` — worked examples from a real audit: file-swap failure mode, overlap-test detection, one-pass repair code, country-verification notes, false-positive examples.
- `scripts/audit_fulltext_mismatch.py` — runnable full-coverage detector (empty + title-overlap<25% mismatched files). Usage: `python scripts/audit_fulltext_mismatch.py [catalog_path]`.
