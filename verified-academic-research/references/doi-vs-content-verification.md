# DOI Verification vs. Content Verification: Two Distinct Checks

## Problem
Claude's review revealed a conflation: "DOI verified via Crossref" was treated as equivalent to "content verified as matching the requested population/topic." These are two separate checks.

## Two-Tier Verification
- Tier 1 (DOI): DOI resolves, Crossref metadata matches title/authors/journal/year
- Tier 2 (Content): Study's actual population matches (e.g., nurses as studied population, not just mentioned) AND finding matches (e.g., workload as significant factor, not just keyword in tags/background)

## NASA-TLX Case Study
10.1080/00140139.2021.2006317 — DOI verified but content failed: validated NASA-TLX on 51 Type 1 diabetes patients, NOT nurses.

## Rule
Only include studies where BOTH DOI and content verification pass. Do not caveat/include with caveats.