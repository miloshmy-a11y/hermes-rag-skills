# Windows / MSYS Environment Notes (SINGLE SOURCE OF TRUTH)

Shared by general-purpose-rag, pdf-processing, rag-literature-build. Edit here, not per-skill.

## The MSYS path gotcha
When Hermes' terminal runs under MSYS/git-bash, Windows paths get mangled:
- `C:\Users\<USER>\...` may be rewritten to `/c/Users/<USER>/...` by the shell.
- Inline `python3 -c "..."` with backslash paths triggers `UnicodeDecodeError` (`\U` seen as
  unicode escape). Use **forward slashes** or call a script file. Inside `execute_code`, `os.path`
  handles native paths fine.

**Mitigation (don't re-discover this):**
- Pass paths as forward slashes: `C:/Users/<USER>/...` works in both `terminal()` and Python.
- Prefer `execute_code` + `os.path.join` over inline `-c` one-liners with backslashes.
- The real fix belongs in the underlying script (normalize paths with `pathlib.Path`), not in
  documentation — flagged for script-level fix.

## Two Python interpreters (pdf-processing gotcha)
- `terminal` `python3` → `C:\Python314` (3.14): HAS PyMuPDF + pdftotext. Use for PDF work.
- `execute_code` venv → `hermes-agent\venv` (3.11): NO pdf libs, no pip. `import fitz` FAILS here.
- Run all PDF extraction via `terminal()` calling `pdf_extract.py`, never inside execute_code.

## web_extract / hermes_tools availability
- `hermes_tools` (web_search, web_extract, terminal, read_file, etc.) is importable ONLY inside
  `execute_code`, NOT from terminal Python. This is environment-specific and may change with
  Hermes updates — re-verify if tool calls start failing from execute_code.

## Backslash in search_files / grep
- `search_files` translates paths to MSYS form and may miss matches. Use terminal `grep -rIn`
  with native Windows paths when search_files returns nothing unexpectedly.
