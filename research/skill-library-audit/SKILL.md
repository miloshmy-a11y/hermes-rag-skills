---
name: skill-library-audit
description: "Audit skill libraries for drift and leaks before publishing."
version: 1.0.0
author: Hermes Agent
license: MIT
---

# Skill Library Audit & Consolidation

## Trigger
Use this skill when:
- You maintain a skill library across local disk AND a public GitHub mirror, and need it
  safe for reuse (no personal paths, no local-only paths, no secrets).
- A review (human or another agent) flags redundancy, contradictions, or broken links
  in your skills — and you must verify each claim against LIVE files, not memory.
- You just finished a large project that spawned several skills and suspect drift between them
  (e.g. three skills each define the same pipeline with different step orderings).

## Core principle: VERIFY BEFORE FIXING
Never trust a review's claims at face value — even a good external review can be reading a
stale cached version. For EVERY flagged issue, read the actual current file and confirm
the claim is real BEFORE editing. In this session, a respected external reviewer flagged
several issues that were already fixed, plus several that were real — the only way to tell
was reading the live files. Pattern:
1. Copy the exact flagged string into a `re.search`/`in` check on the live file.
2. If present → fix. If absent → note "reviewer's copy was stale on this one" and move on.
3. After fixing, re-read and assert the fix landed (don't trust your own edit returned OK).

## The 7 bug classes to hunt (and what fixed them this session)
1. **Divergent copies of the same logic.** Three skills each defined a full-text retrieval
   chain with DIFFERENT orderings. Fix: ONE `references/<topic>-priority.md` as single source
   of truth; every skill points to it, none redefine it. (A prior edit had "finished" the
   dedup but left `verified-academic-research` still holding its own section + a 2nd file —
   the dedup was only 2/3 done. Always check ALL skills, not just the two the review named.)
2. **Broken cross-references / dead links.** A skill linked
   `../software-development/pdf-processing/...` — correct in Hermes' category-organized LOCAL
   tree, but 404 in the FLAT public GitHub repo where `pdf-processing` is top-level. Fix: use
   the path valid in the PUBLISHED repo, and note the local-tree variant in parentheses.
3. **Stale/contradictory metadata.** Front-matter said "721+ papers" while the body said
   "~381 documents"; version `4.5.3` in front-matter vs `v4.5.2` in H1. Fix: make counts
   LIVE-COMPUTED at query time (never hardcode a catalog size in docs); unify version strings.
4. **Leftover edit fragments.** Dangling clauses ("ebook, 47 other, 6 org_doc..."),
   orphaned domain lists ("4 domains: Selected Studies, ENSS...") from old schemes. Fix:
   grep for tell-tale remnants after any multi-edit pass; don't assume one edit cleaned all.
5. **README ↔ content drift.** README listed `rag-catalog-audit-rebuild` but the folder was
   never synced to public. Fix: either add the missing folder, or remove the README line —
   prefer adding the real skill so the README isn't a lie.
6. **Personal-data / local-path leaks in a PUBLIC repo.** `D:\work\sayang\OUM`, `C:\Users\Milos`,
   username tokens. Critical: the escaped form `D:\\work` and forward-slash `D:/work` BOTH
   occur and a naive `.replace("D:\\work", ...)` (single backslash) misses the on-disk
   double-backslash form. Fix: scrub with BOTH `r'D:\\work'` (raw, matches on-disk) and
   `'D:/work'` and `'D:\work'`. Replace with `<YOUR_WORK_FOLDER>` / `<HERMES_HOME>` / `<USER>`.
7. **Capability that doesn't actually work.** A skill chain included Sci-Hub "as last resort."
   Direct test proved it non-functional (anti-bot walls, 403s from all mirrors). Fix: TEST the
   capability before keeping it in documentation; if dead, remove it everywhere (local + public),
   don't leave "approved last resort" language for something that never succeeds.

## Consolidation pattern (the actual workflow used)
1. Read all relevant SKILL.md files in one pass (batch the reads).
2. For each review claim, confirm-or-refute against live content (see Core principle).
3. Create the shared `references/<topic>.md` single-source-of-truth file.
4. In each skill: REPLACE the inline duplicated block with a 1-2 line pointer to the shared file.
   (Don't just ADD a pointer — DELETE the old inline copy, or drift returns.)
5. Fix broken paths, stale fragments, version/count contradictions.
6. Sync to public mirror: `shutil.copytree` each skill dir → public repo, then SCRUB personal
   paths/tokens (handle all 3 backslash variants), delete any `UNIVERSAL_CATALOG.json` copied
   by accident, verify 0 leaks, then `git commit` + `git push` via x-access-token URL form.
7. Final verification: grep the PUBLIC repo for each bug class; assert 0 remaining.

## Token / secret hygiene for public push
- GitHub PAT must be pushed as `https://x-access-token:<TOKEN>@github.com/...` (the `x-access-token`
  form is accepted; a bare PAT in the URL password field is rejected since 2021).
- NEVER hardcode the token in skill files. Keep it in `.env` (`GITHUB_TOKEN`) only.
- After pushing, tell the user to REVOKE the PAT at github.com/settings/tokens — it is exposed
  in chat once used.
- A `git push` that previously worked can later fail with "Password authentication is not
  supported" if the token was deleted from `.env` — re-issue a fresh PAT for each push session.

## Pitfalls
- **The dedup is never "done" on the first pass.** A pointer added to 2 of 3 skills while the
  3rd still holds the full inline block = only partial fix. Verify ALL consumers point to the
  shared file and the redundant files are DELETED.
- **Stale-review trap:** an external reviewer may be reading an older committed state. Verify
  live, don't reflexively apply. Some flagged items will already be fixed; some will be new.
- **Scrub both `D:\\work` and `D:/work`.** One replace misses the other; leaks survive the push.
- **Don't leave dead capabilities documented as "available."** If you tested it and it's broken,
  remove it — documenting a non-working fallback as "last resort" misleads the next agent.

## Linked resources
- `references/audit-checklist.md` — copy-paste verification checklist covering all 7 bug classes, for use at the end of any skill-library maintenance pass.
