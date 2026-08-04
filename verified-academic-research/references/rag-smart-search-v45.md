# Universal RAG System v4.5.1 — Smart Search Implementation Notes

## Query Expansion Strategy (Dynamic Preferred)
The v4.5 system includes a static `QUERY_EXPANSIONS` dictionary for common nursing/occupational health terms. However, **user feedback preference**: Claude should dynamically generate contextually appropriate expansion terms for any query topic when local results are insufficient. The static dictionary provides a starting point but is NOT exhaustive.

### When to Use Dynamic vs Static Expansion
- **Static dictionary**: Good for first-pass local search (common nursing terms)
- **Dynamic expansion**: When results < 5 AND user is searching a novel/unexpected topic. Claude generates semantically related terms based on understanding the query concept.
- **Never auto-expand to unrelated topics** — keep expansion within the same concept domain.

## Low-Recall Trigger Logic
1. Initial search uses original query + first wave of expansions
2. If result count < 5 (configurable threshold):
   - Re-run with full-text body search enabled (not just title/abstract/tags)
   - Add additional expansion terms (up to 5 more, dynamically generated)
3. If still < 5 after deeper search:
   - Trigger web fallback via `web_search` tool
   - Results clearly labeled as "🌐 NOT IN LOCAL COLLECTION"
   - NEVER auto-index web results — ask user first

## Result Labeling Convention
Each result includes:
- **Source**: `📁 local_catalog` vs `🌐 web_fallback`
- **Match type**: `literal` (exact query term) vs `expanded` (related concept term)
- **Verification**: `✅ VERIFIED` (Crossref confirmed) vs `📄 LOCAL` (not verified)
- **Evidence**: Shows whether match was on content text, tag, or instrument
- **Relevance level**: `DIRECT` (workload as finding) vs `CONTEXTUAL` (workload mentioned in background/environmental description)

## Crossref Author Extraction Fix
When extracting authors from Crossref API `author` array:
- Skip entries with `name` but no `given`/`family` fields (institutional affiliations)
- Preserve multi-part surnames like "WAN ZAINODIN" or "AHMAD SHARONI" using the `family` field as-is
- Handle empty/None author entries gracefully

## DOI Verification Caching
To reduce API calls:
- Documents verified within 30 days skip re-verification
- Cache stored in `verified_at` timestamp field in catalog

## Low-Recall Log
Queries that needed expansion or web fallback are logged to `low_recall_log.json` for tag dictionary review.

## Relevance Classification (Key Learning)
When presenting results, distinguish:
1. **DIRECT**: Workload is a measured finding (significant predictor, key factor, etc.) — primary results list
2. **CONTEXTUAL**: Workload mentioned in background, discussion, or as environmental challenge — secondary/supporting section, clearly noted
3. **INSTRUMENT**: Study about workload measurement tools but on non-target population — excluded
4. **FALSE POSITIVE**: Cross-field pattern match without actual semantic relationship — excluded

This prevents conflating "keyword match" with "relevant finding."