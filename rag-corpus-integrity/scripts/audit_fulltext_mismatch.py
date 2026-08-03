#!/usr/bin/env python3
"""audit_fulltext_mismatch.py — full-coverage full-text integrity detector.
Flags empty/placeholder files and likely-MISMATCHED files (title-overlap < 25%) across all
full-text records in the catalog. Read-only: reports issues; the agent verifies + fixes via
the one-pass rebuild described in SKILL.md / references/technique.md.

Usage: python audit_fulltext_mismatch.py [catalog_path]
"""
import os, json, re, sys

CAT = (sys.argv[1] if len(sys.argv)>1
       else r"C:\Users\Milos\AppData\Local\hermes\cache\web\universal_rag\UNIVERSAL_CATALOG.json")
data = json.loads(open(CAT, encoding="utf-8").read())
docs = data["documents"]

real = [d for d in docs if not str(d.get("doi","")).startswith("local:")
        and (d.get("files") or {}).get("extracted_text")
        and os.path.exists((d.get("files") or {}).get("extracted_text"))
        and not d.get("is_duplicate_of")]
N = len(real)

def norm(s): return re.sub(r"[\u00a0\u2010-\u2015\u2212&]","-", s).lower()
def overlap(title, text):
    words=[w for w in re.findall(r"[a-z]{4,}", norm(title))
           if w not in ("the","and","among","with","from","between","their","that","this","nurses","nurse","stress")]
    if not words: return 1.0
    uniq=set(words[:8]); return sum(1 for w in uniq if w in text)/len(uniq)

empty=[]; mismatch=[]
for d in real:
    p=(d.get("files") or {}).get("extracted_text")
    size=os.path.getsize(p); t=open(p,encoding="utf-8",errors="ignore").read().lower()
    if size<800 or "this page can't be found" in t or "skip to main content" in t[:300]:
        empty.append(d.get("doi")); continue
    ov=overlap(d.get("title",""), t)
    if ov<0.25:
        mismatch.append((d.get("doi"), round(ov,2), d.get("title","")[:50], size))

print(f"FULL-COVERAGE full-text check across {N} records:")
print(f"  EMPTY/placeholder-only files: {len(empty)}")
for x in empty: print("    ", x)
print(f"  LIKELY MISMATCHED (title-overlap<25%): {len(mismatch)}")
for doi,ov,title,size in mismatch:
    print(f"    {ov} | {size}B | {doi} | {title}")
print(f"\n  => Genuine full-text problems ~ {len(empty)+len(mismatch)} = {100*(len(empty)+len(mismatch))/N:.1f}%")
print("  NOTE: meta_only placeholders (correct Crossref citation, no body yet) are NOT errors.")
