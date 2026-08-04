---
name: skill-backup
description: Publish Hermes skills to Git without leaking secrets.
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [skills, backup, github, git, publish, privacy]
    category: software-development
    requires_tools: [terminal, python3]
---

# Skill Backup & Safe Sharing (Git/GitHub)

## Trigger
User wants Hermes skills backed up to a repo, pushed to GitHub, or prepared for
sharing. Also when you have built/improved skills and the user says "back them up",
"push to github", "make them public", or "share my skills".

## Critical rule: scrub BEFORE you commit
Skills may contain machine-specific paths (`C:\Users\<you>\...`, `D:\work\...`),
personal usernames, or references to local data folders. **Never push raw skills.**
Always copy to a staging dir, scrub personal tokens, exclude secrets/catalogs, then commit.

### Path-scrubbing pattern (Windows backslashes — USE PYTHON, not sed)
`sed` fails on Windows backslash paths because the real file content stores `\\`
(double backslash in the on-disk string) and escaping gets mangled. **Use a Python
script with literal-string replacement** instead:

```python
import os, shutil
SRC = r"C:\Users\Milos\AppData\Local\hermes\skills\research\my-skill"
DST = r"C:\Users\Milos\AppData\Local\hermes\skills-public\my-skill"
shutil.copytree(SRC, DST)
PAIRS = [
  (r"C:\Users\Milos\AppData\Local\hermes\cache\web\universal_rag", r"<HERMES_HOME>/cache/web/universal_rag"),
  (r"C:\Users\Milos\AppData\Local\hermes", r"<HERMES_HOME>"),
  (r"C:\Users\Milos", r"<HOME>"),
  (r"D:\work\sayang\OUM\RESEARCH\bsc\pdf", r"<YOUR_PDF_FOLDER>"),
  (r"D:\\work\\sayang\\OUM\\RESEARCH\\bsc\\pdf", r"<YOUR_WORK_FOLDER>/OUM"),
  (r"D:\work", r"<YOUR_WORK_FOLDER>"),
  (r"D:\\work", r"<YOUR_WORK_FOLDER>"),
]
for dp,_,fns in os.walk(DST):
    for fn in fns:
        if fn.endswith((".md",".py",".txt",".json")):
            p=os.path.join(dp,fn); s=open(p,encoding="utf-8").read()
            for a,b in PAIRS: s=s.replace(a,b)
            s=s.replace("Milos","<USER>")   # personal username token
            open(p,"w",encoding="utf-8").write(s)
```
A ready-to-run version lives in `scripts/scrub_skill_paths.py`.

### Always exclude (add to .gitignore + skip in copy)
- `.env` (Hermes credential store — API keys live here, NEVER commit)
- `UNIVERSAL_CATALOG.json` / any bundled catalog snapshot (real user data, not skill source)
- `.hub/` (84MB+ community-skill browse cache)
- `__pycache__/`, `*.pyc`, `.usage.json`, `.bundled_manifest`
- PDFs, images, large binaries

### Verification before push
```bash
git ls-files | grep -i "\.env\|UNIVERSAL_CATALOG\|s2k-\|ghp_\|<USER>\|Milos" && echo "LEAK" || echo "CLEAN"
git ls-files | grep -c "SKILL.md"   # should be > 0 (not over-ignored)
```

## Common Pitfalls (publishing) — learned the hard way

1. **`shutil.copytree` BYPASSES `.gitignore`.** If you stage a skills repo by copying
   folders with `copytree`, files the `.gitignore` would exclude (e.g.
   `UNIVERSAL_CATALOG.json`, your private catalog with FYP location data) get copied in
   anyway and then committed. **Fix:** rely on the scrub script's `SKIP_FILES` (it deletes
   them post-copy), or `git add -A` only after confirming `git status` shows no
   catalog/json secrets. Always `find . -name UNIVERSAL_CATALOG.json` in the staging dir
   before committing.

2. **A path/username scrub LEAKS location words.** Stripping `C:\Users\Milos` and the
   `Milos` username does NOT remove personal *location* strings embedded in data
   (e.g. `Seri Manjung`, `Perak` in a thesis catalog). The scrub script and your final
   pre-push scan MUST include a personal-keyword list (`--terms "Seri Manjung,Perak"`)
   and a catch-all grep for those words, not just paths/tokens.

3. **Global `url.<token>@.insteadOf` re-tokenizes `git remote set-url` AND leaks the token in plaintext.** If a global git config has `url."https://<USER>:<PAT>@github.com/".insteadOf "https://github.com/"`, then `git remote set-url origin https://github.com/...` is silently rewritten to embed the PAT in `.git/config` — anyone reading that file gets the token. **Fix:** remove the plaintext `insteadOf` block entirely; leave the remote URL token-free. Push auth is supplied by **`credential.helper=manager` (Git Credential Manager)**, which reads the token from the OS credential store (Windows Credential Manager) — encrypted, and reusable by every git/gh client and agent with no token in any config file or URL. (`credential.helper=store` is a weaker fallback: it writes the token to a plaintext `~/.git-credentials` file — avoid it.) After setting a plain URL, confirm with `git remote get-url origin` that no `ghp_`/`@` token appears. **Validated 2026-08:** setting `helper = manager` + deleting the `insteadOf` line let `git ls-remote` / `git push` authenticate via GCM with zero token in config; a throwaway-branch write test confirmed cross-agent reuse.

4. **Restructuring a published skills repo = full wipe + re-copy, not piecemeal.** When
   flattening `research/X` -> `X` or deleting redundant sibling skills, do NOT edit files
   one-by-one. Wipe the working tree (keep `.git` + `.gitignore`), then copy the curated
   skill set fresh from local `~/skills`. This avoids orphaned old paths and stale
   duplicates. Verify with `git status` (expect D + A for the moved folders).

5. **Verify BEFORE push with a personal-term grep, not just `git grep ghp_`.** Run a Python
   walk that checks for paths, username, email, AND your location words; the scrub script
   already prints surviving hits — read that output and confirm "NONE" before `git push`.

6. **`git reset --hard FETCH_HEAD` + delta-commit + `--force` WIPES the remote tree (hit 2026-08).**
   When pushing to a repo that ALREADY has commits, the naive "fetch, reset --hard to remote,
   copy in new files, add -A, commit, force-push" sequence is dangerous:
   - `git reset --hard FETCH_HEAD` **deletes untracked local files** (e.g. a new skill folder
     you copied into the working tree but had not committed) — they silently vanish.
   - After the reset, `git add -A` only stages what DIFFERS from the remote tip. Your commit
     therefore contains a *partial* file set (e.g. 67 files) — NOT the full tree.
   - `git push --force` then replaces the **entire** remote branch with that partial set,
     deleting every other skill previously on the remote.
   **Correct restore pattern (validated):** clone (or `git fetch` WITHOUT reset), overlay the
   FULL local `skills/` tree on top of the working copy (keep `.git` + `.gitignore`), scrub
   PII, `git add -A`, commit, then `git push --force HEAD:<branch>`. This makes the commit a
   superset of history and the force-push restores completeness. Always confirm the remote
   file count afterwards (see post-push verification below) — in this session the partial
   push was caught and recovered via re-clone + full overlay.

### Verify AFTER push (catch partial/clobbered pushes)
`git ls-tree` on a remote URL fails ("not a git repository"); you must fetch first. After
pushing, confirm the remote actually holds what you intend:
```bash
cd /tmp && rm -rf _verify && mkdir _verify && cd _verify
git init -q && git remote add origin <URL> && git fetch origin <branch> --depth 1
git ls-tree -r origin/<branch> | awk '{print $4}' | cut -d/ -f1 | sort -u   # top-level dirs present?
git ls-tree -r origin/<branch> | grep -c "SKILL.md"                          # skill count sane?
git ls-tree -r origin/<branch> | grep "<expected-new-file>" && echo "PRESENT" || echo "MISSING"
cd /tmp && rm -rf _verify
```
In this session a force-push had replaced `main` with only 67 files (the new skill was
missing); the post-push fetch+ls-tree caught it and a full-overlay re-push fixed it.

## GitHub push authentication (PAT gotcha — learned the hard way)
A Personal Access Token (PAT, `ghp_...`) **cannot be used as a URL password**:
```
git push https://miloshmy-a11y:ghp_xxxx@github.com/...   # FAILS:
# remote: Invalid username or token. Password authentication is not supported.
```
Use ONE of:
1. **`x-access-token` form** (works with PAT):
   ```bash
   TOK=$(grep '^GITHUB_TOKEN=' ~/.env | cut -d= -f2-)
   git push "https://x-access-token:${TOK}@github.com/<user>/<repo>.git" main
   ```
2. **Git credential helper** (avoids token in URL/process list):
   ```bash
   printf 'protocol=https\nhost=github.com\nusername=<user>\npassword=%s\n' "$TOK" | git credential approve
   git push origin main
   ```
3. **`gh` CLI** (browser OAuth, no token copy): `gh auth login` → `gh repo create ... --push`.
   NOTE: `gh` is often NOT installed by default — check with `gh --version` first.

4. **Prefer Hermes' own secure credential store over plaintext config (user preference, 2026-08).**
   Do NOT leave the token in plaintext in `~/.gitconfig` via a
   `url."https://<user>:<PAT>@github.com/".insteadOf` line — this was observed in the wild
   and is a real leak risk (anyone reading the file gets the token; and the same insteadOf
   silently re-injects the token into every `git remote set-url`, see Pitfall #3). The user
   reported a recent Hermes update added native credential handling — use
   `hermes credentials` (or the desktop app's credential store) to hold the GitHub PAT, and
   remove the plaintext `insteadOf` block from `~/.gitconfig`. Auth then flows through the
   credential helper without the token ever sitting in a readable config file.

### Creating the repo
```bash
curl -X POST -H "Authorization: Bearer $TOK" -H "Content-Type: application/json" \
  -d '{"name":"hermes-rag-skills","visibility":"public","private":false}' \
  https://api.github.com/user/repos
```

## Local originals stay intact
Copy to a staging folder (`skills-public/`) for the public version. The live skills in
`AppData\Local\hermes\skills` are NEVER modified by the scrub — only the copy is.

## References
- `references/github-pat-auth.md` — full auth failure transcript + working commands.
- `references/publishing-checklist.md` — step-by-step publish workflow with the 5 pitfalls above applied (copytree-bypass, location-word scan, insteadOf re-tokenization, full-wipe rebuild).
- `scripts/scrub_skill_paths.py` — reusable path-scrubber (copy + replace + exclude + personal-term scan + post-scrub leak report). Run with `--terms "Seri Manjung,Perak"`.
