# Skill Library Audit Checklist (end-of-pass verification)

Run this after any skill-library maintenance pass. Each item must assert PASS on the
LIVE files (local + public mirror) before you declare done. Copy the checks into an
`execute_code` block scanning the public repo root.

## 1. Divergent logic (Dedup completeness)
- [ ] For every pipeline/chain that appears in >1 skill, there is exactly ONE
      `references/<topic>.md` single-source-of-truth file.
- [ ] Every skill that uses that pipeline POINTS to the shared file (no inline redefinition).
- [ ] The redundant per-skill copies / files are DELETED (not just superseded by a pointer).
- [ ] Grep the public repo for the pipeline's step keywords; confirm they appear only in the
      shared file + short pointers, never as a full standalone chain in a SKILL.md.

## 2. Broken cross-references
- [ ] Every relative link/path in every SKILL.md resolves in the PUBLISHED repo layout
      (flat, not the local category tree). Test: does the path exist at that location?
- [ ] For paths valid only in the local tree, a parenthetical notes the published-repo equivalent.

## 3. Stale/contradictory metadata
- [ ] No hardcoded catalog size (counts must be live-computed or clearly dated+labeled estimate).
- [ ] Front-matter `version:` matches the H1 version string in the same file.
- [ ] No two different counts for the same thing within one file.

## 4. Leftover edit fragments
- [ ] Grep for tell-tale remnants: dangling parens, orphaned domain lists, old version strings,
      half-removed sentences. Search the whole repo, not just edited files.

## 5. README ↔ content drift
- [ ] Every skill named in README exists as a folder in the repo (or the README line is removed).
- [ ] Every skill folder of consequence is listed (or intentionally omitted).

## 6. Personal-data / local-path leaks (PUBLIC repo only)
Scan for: `C:\Users\`, `/c/Users/`, `D:\work`, `D:/work`, `D:\\work`, the username, token prefixes
(`ghp_`, `s2k-`), and `UNIVERSAL_CATALOG.json` if accidentally copied.
- [ ] 0 matches in the public repo. CRITICAL: scrub both `D:\\work` (raw, on-disk double-backslash)
      AND `D:/work` AND `D:\work` — one replace misses the others.

## 7. Dead capabilities
- [ ] Any tool/feature documented as available was actually TESTED working this session.
- [ ] If tested and broken, it is REMOVED from local + public (no "last resort" language for dead code).

## 8. Secret hygiene (if pushing)
- [ ] PAT used as `https://x-access-token:<TOK>@github.com/...` (not bare in URL password).
- [ ] Token not hardcoded in any skill file; lives only in `.env`.
- [ ] User told to REVOKE the PAT after the push.

## Final assertion
Print one line per check: `PASS` / `FAIL`. If any FAIL, fix and re-run. Do not declare done
with outstanding FAILs. The dedup is rarely complete on the first pass — check ALL consumers.
