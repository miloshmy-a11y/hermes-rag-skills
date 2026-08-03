# GitHub PAT push authentication — failure transcript + working fix

## What failed
Pushing with a PAT as a URL password:
```
git push https://miloshmy-a11y:ghp_xxxx@github.com/miloshmy-a11y/hermes-rag-skills.git main
# remote: Invalid username or token. Password authentication is not supported for Git operations.
# fatal: Authentication failed for 'https://github.com/miloshmy-a11y/hermes-rag-skills.git/'
```
Also tried `x-access-token:` form and it STILL failed with "Invalid username or token"
because the token had already been **revoked/deleted** by the user — the 401 on
`api.github.com/user` confirmed it. A revoked token looks identical to a bad URL.

## Diagnosis checklist
1. Confirm the token is still VALID: `curl -s -o /dev/null -w "%{http_code}\n" -H "Authorization: Bearer $TOK" https://api.github.com/user` → must be `200`, not `401`.
2. If 200 but push still fails → URL form issue. Use `x-access-token:` (not `user:pat`).
3. If 401 → token is dead. Generate a new PAT (Settings → Tokens → classic → `repo` scope).

## Working commands (valid token)
```bash
TOK=$(grep '^GITHUB_TOKEN=' ~/.env | head -1 | cut -d= -f2-)
# create repo
curl -X POST -H "Authorization: Bearer $TOK" -H "Content-Type: application/json" \
  -d '{"name":"hermes-rag-skills","visibility":"public"}' https://api.github.com/user/repos
# push (x-access-token form)
git push "https://x-access-token:${TOK}@github.com/<user>/<repo>.git" main
```
## Cleanup
After pushing, the user should delete the PAT (Settings → Tokens). The repo stays public.
