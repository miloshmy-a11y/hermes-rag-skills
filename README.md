# Hermes RAG & Research Skills (public)

A curated set of reusable [Hermes Agent](https://github.com/NousResearch/hermes)
skills for academic literature discovery, RAG catalog building, citation
verification, and PDF processing. Authored and battle-tested on a nursing-stress
systematic-review catalog, but domain-agnostic.

## Skills included
- **openalex-skill** — OpenAlex API search + OA-PDF + citation counts (no key, CC0).
- **general-purpose-rag** — universal RAG index/search with query expansion + web fallback.
- **rag-literature-build** — grow & reconcile a local JSON paper catalog (verify-as-you-go).
- **rag-catalog-audit-rebuild** — audit/correct a corrupted RAG catalog from source PDFs.
- **verified-academic-research** — 3-step DOI verification plus honest gap scoping.
- **semanticscholar-skill** — S2 citation graph (key via S2_API_KEY env var).
- **pdf-processing** — robust PDF text extraction (PyMuPDF then pdftotext fallback).

## Notes
- Paths use HERMES_HOME / HOME placeholders — adapt to your install.
- No secrets, no personal catalog data, no bundled PDFs are included.
- Requires python3 plus requests.

## License
MIT (skill content); respect upstream licenses of bundled references.
