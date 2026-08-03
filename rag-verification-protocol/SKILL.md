---
name: rag-verification-protocol
description: "Two-factor RAG verification: DOI plus content match."
version: 1.0.0
author: Hermes Agent
license: MIT
---

# RAG Result Verification Protocol v1.0

## Overview
Protocol for verifying that RAG search results are genuinely relevant — not just keyword matches. Applies whenever a user asks for studies matching specific population + concept criteria.

## The Problem This Solves
DOI verification only confirms a citation is real. It says nothing about whether the paper's content matches the queried population and finding.

## Two-Factor Verification (Both Required)

### Factor 1: DOI Verified
- Crossref returns HTTP 200, metadata matches catalog entry
- Confirms the **citation is real**

### Factor 2: Content Verified  
- Population match: actual studied population matches query
- Finding match: concept explicitly reported as significant factor
- Confirms the **content is relevant**

## Common False Positive Patterns
| Pattern | Example | Action |
|---------|---------|--------|
| Instrument on wrong population | NASA-TLX on diabetes | Exclude |
| Term in background only | workload in intro | Exclude |
| Term as survey item | rate your workload | Exclude |
| Explicit "no association" | no link found | Exclude |

## Summary Statement Rules
- "X verified" means ALL X passed DOI + content verification
- Label DOI status and content status distinctly
