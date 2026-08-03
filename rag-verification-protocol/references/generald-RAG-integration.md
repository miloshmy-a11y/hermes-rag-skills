# Integration with general-purpose-rag

## When results are presented from search(), ALWAYS show two verification dimensions:

### Result Labels
- ❌ NOT VERIFIED: DOI not resolved via Crossref
- ✅ DOI VERIFIED: DOI resolves and metadata matches
- ✅ CONTENT VERIFIED: Population + finding confirmed from full text
- ✅ VERIFIED: Both DOI + Content verified (green checkmark)

### When DOI verified but content not verified:
- Still show in results with ⚠️ label and explicit caveat about population/finding
- Never claim "verified" in summary counts

### Summary Statement Template
```
Found X results total:
  - Y fully verified (DOI + content)
  - Z DOI-verified only (content pending)  
  - W local-only (DOI not verified)
```
NEVER say "All Y verified" when it means only DOI verification.

### Workflow Integration
1. Search → expand → confirm candidates against text → rank
2. For ranked results: verify DOIs via Crossref (30-day skip cache)
3. For results with full text: additional content verification
4. Label each result with both statuses
5. Summary: distinguish "DOI verified" from "content verified"