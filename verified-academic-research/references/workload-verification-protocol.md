# Workload-Specific Content Verification Protocol

## Overview
When searching for studies about "workload as the most significant factor among nurses," the search must distinguish between studies where workload is:
- **✅ A measured finding** (statistically significant predictor, ranked most important)
- **🟡 A contextual factor** (workload mentioned as environmental driver, patient ratio consequence)
- **❌ A keyword artifact** (workload as instrument name, no nursing population, cross-field pattern match)

## Verification Protocol for Workload Studies

### Step 1: DOI Verification
- DOI resolves via Crossref with matching metadata
- Check: title, authors, journal, year all match

### Step 2: Population Verification
- Confirm the **studied population** is nurses (check Methods/Objective/Background)
- NOT just nurses mentioned as authors, citations, or in background
- ❌ NASA-TLX (10.1080/00140139.2021.2006317) — validated on 51 Type 1 diabetes patients, nurses never mentioned as population

### Step 3: Finding Relevance Verification
Check which tier applies:

**✅ DIRECT — Significant Finding:**
- Explicit statements: "workload was a significant predictor", "workload contributed the most", "at the top of the list was excessive workload"
- Statistical results: p-values, OR values, β coefficients for workload
- Must appear in Results/Findings section, not Introduction/Background

**🟡 CONTEXTUAL — Environmental Factor:**
- Workload mentioned in context: "high patient-to-nurse ratios worsen workload", "workload increased due to expanded scope"
- Not a study finding, but relevant environmental context
- Keep but label as "contextual mention"

**❌ FALSE POSITIVE — Must Exclude:**
- Workload as instrument only (NASA-T LX validation on non-nursing population)
- Cross-field pattern matches: "significant" in abstract + "workload" in tags, no co-occurrence
- Background mentions: "amplifying the workload on remaining nurses" — not a finding
- No actual co-occurrence in content (pattern artifact)

## False Positive Catalog

| DOI | Pattern That Failed | Why Excluded |
|-----|------|-------------|
| 10.1080/00140139.2021.2006317 | "workload" + "instrument" in title | NASA-TLX validated on diabetes patients, NOT nurses |
| 10.1186/s12912-024-02203-5 | "significant.*workload" cross-field match | Pattern matched "significant" in abstract + "workload" in tags; no co-occurrence in content |
| 10.1080/20479700.2024.2417641 | "workload" keyword + "significant" | Background mention only: "amplifying the workload on remaining nurses" |
| 10.3389/fpubh.2024.1370052 | "workload" in tags + "important" | Workload appears as survey question item, not as finding |
| 10.1155/jonm/6160674 | "workload" + "significant" | Background only: "patient-nurse ratio significantly influences nursing workloads" — ratio influences workload, not workload as finding |

## Tag Dictionary Improvement Notes

Queries that triggered fallback to low-recall logging:
- "workload most significant factor nurses" → 10 results, 4 false positives, 6 verified

Suggested tag additions:
- "workload_as_finding" (studies where workload IS the significant finding)
- "workload_as_context" (studies where workload is environmental context)
- "workload_instrument_only" (workload measurement tools)
- "nursing_population" (explicit population descriptor)
