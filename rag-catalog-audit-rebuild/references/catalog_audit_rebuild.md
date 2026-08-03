# RAG Catalog Rebuild — Verified Recipe (from source PDFs on disk)

Tested pattern from a real session: rebuilt a 717-entry corrupted catalog into a clean 172-doc
catalog from `D:\work\sayang\OUM\RESEARCH` + `books` PDFs. All steps local; nothing destructive
(backup first).

## Step 0 — Backup
```bash
cp UNIVERSAL_CATALOG.json "backups/CAT_before_rebuild_$(date +%Y%m%d_%H%M%S).json"
```

## Step 1 — Inventory (read-only)
Walk source roots; record path, size, and `hashlib.md5()` of first 1 MB (fast dedup key). Exclude
coursework/notes trees. Output `SOURCE_INVENTORY.json`.

```python
import os, hashlib, json
roots=[r"D:\work\sayang\OUM\RESEARCH", r"D:\work\sayang\OUM\books"]
recs=[]
for root in roots:
    for dp,_,fs in os.walk(root):
        for fn in fs:
            if fn.lower().endswith('.pdf'):
                p=os.path.join(dp,fn); h=hashlib.md5()
                with open(p,'rb') as f: h.update(f.read(1024*1024))
                recs.append({'path':p,'size':os.path.getsize(p),'h1':h.hexdigest()[:12]})
```

## Step 2 — Copy good PDFs + extract text
Skip files already seen by hash. Copy to `SOURCE_PDFS/`, extract to `SOURCE_TEXT/` with the
**absolute pdftotext path** (see SKILL.md pitfalls). Flag rc!=0 as corrupt. Save `COPY_EXTRACT_MANIFEST.json`.

```python
import subprocess, shutil, os
PDFTO=r"C:\Users\<user>\scoop\apps\git\2.52.0\mingw64\bin\pdftotext.exe"
# for each rec: copy2 -> dest; subprocess.run([PDFTO,"-layout",dest,txtdest])
# if rc!=0 or size<50: corrupt (keep pdf, skip text)
```

## Step 3 — Classify by reading first page
For each extracted text, decide `doc_type` from the first ~6000 chars:
- `assignment`: "final year project", "submitted in fulfilment", "this thesis/dissertation"
- `instrument`: "questionnaire", "validity and reliability", "kuesioner", "scale for measuring" AND no own-DOI
- `ebook`: "chapter", "ISBN", "published by", "all rights reserved", no DOI
- `study`: has own DOI on title page OR (abstract + journal name)
- `other`: guides, phrasebanks, admin letters (NIH guidelines, NMRR step-by-step, etc.)

**CRITICAL:** confirm the DOI appears in the file's OWN text before trusting it (cited-DOI ≠ paper-DOI).

## Step 4 — Crossref-verify studies (authoritative metadata)
```python
import urllib.request, json, re, time
def verify(doi):
    url=f"https://api.crossref.org/works/{doi}"
    req=urllib.request.Request(url, headers={'User-Agent':'RAG-Rebuild/1.0 (mailto:x@example.com)'})
    with urllib.request.urlopen(req, timeout=25) as r:
        m=json.loads(r.read()).get('message',{})
        return {'title':m.get('title',[''])[0],
                'authors':[' '.join(p for p in [a.get('given',''),a.get('family','')] if p).strip()
                            for a in m.get('author',[])],
                'year':str(m.get('published',{}).get('date-parts',[['']])[0][0]),
                'journal':' '.join(m.get('container-title',[''])),
                'abstract':re.sub(r'<[^>]+>',' ',m.get('abstract','') or '').strip()}
```
~61/68 verified in session. Non-Crossref DOIs (e.g. `10.32549/OPI-NSC-105`) keep parsed metadata + flag.

## Step 5 — Build deduped catalog
- Key = `('doi', normalized)` if real 10.x, else `('title', norm_title+'|'+doc_type)`.
- Domain map: study→OUM_Research, ebook→OUM_Books, assignment→OUM_Assignments,
  instrument→OUM_Instruments, other→OUM_Other.
- Merge key docs (thesis) explicitly.
- `inferred_tags` derived from title+abstract keywords (workload, burnout, ENSS, Malaysia…).
- Assert: duplicate DOIs = 0.

## Step 6 — Verify
- Every doc has title/doi/doc_type/domain/files; every referenced PDF exists on disk.
- Smoke-search a few terms; confirm thesis + studies resolve.

## Things that bit us (do not repeat)
- `execute_code` Python sandbox CANNOT find pdftotext on PATH → use absolute Win path + run via `terminal`.
- `import json`/`import re` NOT auto-imported in execute_code → import explicitly.
- Mendeley export: some files corrupt, some fine → DEFER the whole set, verify later; don't nuke it.
- Don't regex-parse titles from PDF first pages for studies — Crossref is far cleaner.
