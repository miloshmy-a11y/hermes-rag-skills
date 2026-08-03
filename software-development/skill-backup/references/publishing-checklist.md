# Publishing a Skills Repo to GitHub — Safe Workflow

Concrete sequence that avoids the 5 pitfalls in the parent SKILL.md. Derived from a
real session where each pitfall was hit and fixed.

## Pre-flight: decide scope
- RAG-only? Full mirror? A single engine? Pick ONE and curate the folder list.
- List the exact source skill folders you will publish (flat: `rag/`, `general-purpose-rag/`, ...).

## Step 1 — Stage by COPY + scrub (never push raw)
```python
import os, shutil
SK = r"<HERMES_HOME>/skills"          # local source
PUB = r"<HERMES_HOME>/skills-public"  # staging = public repo working copy
mapping = {
  "rag": os.path.join(SK, "rag"),
  "general-purpose-rag": os.path.join(SK, "research", "general-purpose-rag"),
  # ... one entry per skill you publish
}
for pub, src in mapping.items():
    if os.path.isdir(src):
        shutil.copytree(src, os.path.join(PUB, pub))
```
Then run the scrubber (it skips `.env` / `UNIVERSAL_CATALOG.json` / caches and reports leaks):
```bash
python3 <SKILL>/scripts/scrub_skill_paths.py <src_skill> <PUB>/<skill> --terms "Seri Manjung,Perak"
```

## Step 2 — Full wipe + re-copy when RESTRUCTURING
Do NOT edit files one-by-one. Wipe the working tree (keep `.git` + `.gitignore`), then copy fresh:
```bash
cd <PUB>
for d in $(ls -A | grep -v '^.git$' | grep -v '^.gitignore$'); do rm -rf "$d"; done
# then re-run the Step-1 copy loop
```
Verify: `git status` shows `D` for old folders + `A` for new flat ones.

## Step 3 — Remove leaked catalog / personal data (copytree bypasses .gitignore!)
```bash
cd <PUB>
find . -name "UNIVERSAL_CATALOG.json" -not -path './.git/*' -delete
find . -name "__pycache__" -type d -not -path './.git/*' -exec rm -rf {} + 2>/dev/null
```

## Step 4 — Final leak scan (paths + username + EMAIL + LOCATION words)
```python
import os, re
PUB="<PUB>"
PAT=["C:\\Users\\<you>", "D:\\work", "<USER>", "Seri Manjung", "Perak", "ghp_", "@users.noreply"]
em=re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
bad=[]
for r,_,fs in os.walk(PUB):
    if ".git" in r: continue
    for f in fs:
        if f.endswith((".md",".py",".txt",".json")):
            t=open(os.path.join(r,f),encoding="utf-8",errors="ignore").read()
            if any(p in t for p in PAT) or (em.search(t) and "example.com" not in em.search(t).group(0)):
                bad.append(os.path.relpath(os.path.join(r,f),PUB))
print("LEAKS:", bad or "NONE")
```
Must print `NONE` before pushing.

## Step 5 — Commit + push (token-free URL)
```bash
cd <PUB>
# ensure remote URL has NO token (global url.*.insteadOf may re-inject one):
git remote get-url origin      # must NOT contain ghp_ or @<token>@
git add -A
git -c user.name="<USER>" -c user.email="<USER>@users.noreply.github.com" \
    commit -q -m "RAG-only skill set: master router + curated sub-skills, scrubbed"
GIT_TERMINAL_PROMPT=0 git push -q origin HEAD
```
Auth comes from `credential.helper=store` + `~/.git-credentials` (token never in URL).
If `git remote get-url` shows a token, set it plain:
`git remote set-url origin https://github.com/<user>/<repo>.git` and rely on the credential store.
