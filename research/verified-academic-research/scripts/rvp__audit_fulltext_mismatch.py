#!/usr/bin/env python3
"""Full-coverage full-text MISMATCH detector (reusable).
Runs FOUR independent scans on every full-text record (ALL required on a full pass):
  1. empty / banner-only file check
  2. title-overlap test (likely wrong paper)
  3. PRISMA-template signature scan (the title test MISSES these)
  4. OUM/coursework wrapper scan (student learning-kit swapped for the research article)
Plus status/disk consistency. Read-only reporter: agent reviews flags, reads the file head to
confirm, then rebuilds from Crossref/PubMed. Also reports doc_type gaps.

Usage:  python scripts/audit_fulltext_mismatch.py
(edit CAT to point at your UNIVERSAL_CATALOG.json)
"""
import os, json, re

CAT = r"C:\Users\Milos\AppData\Local\hermes\cache\web\universal_rag\UNIVERSAL_CATALOG.json"
data = json.loads(open(CAT, encoding="utf-8").read())
docs = data["documents"]

real = [d for d in docs if not str(d.get("doi", "")).startswith("local:")
        and (d.get("files") or {}).get("extracted_text")
        and os.path.exists((d.get("files") or {}).get("extracted_text"))
        and not d.get("is_duplicate_of")]
N = len(real)


def norm(s):
    return re.sub(r"[\u00a0\u2010-\u2015\u2212&]", "-", s).lower()


def title_overlap(title, text):
    words = [w for w in re.findall(r"[a-z]{4,}", norm(title))
             if w not in ("the", "and", "among", "with", "from", "between",
                          "their", "that", "this", "nurses", "nurse", "stress")]
    if not words:
        return 1.0
    uniq = set(words[:8])
    return sum(1 for w in uniq if w in text) / max(1, len(uniq))


# Separate signature scans — the title-overlap scan MISSES both of these classes
PRISMA_SIG = ["tips for reporting this item", "eligibility criteria with a rationale",
              "preferred reporting items", "identify any specific restrictions such as date",
              "describe how items were selected for charting", "data charting form"]
# OUM = Open University Malaysia; NBBS/NBNS = nursing module codes whose PDFs are student kits/exams
OUM_SIG = ["open university malaysia", "oumk", "nbbs", "nbns", "learning kit",
           "matriculation no", "matrix no", "final year project submitted", "project paper submitted"]

mismatch, empty, tmpl, coursework, dt_missing, status_bad = [], [], [], [], [], []
for d in real:
    p = (d.get("files") or {}).get("extracted_text")
    size = os.path.getsize(p)
    t = open(p, encoding="utf-8", errors="ignore").read().lower()
    if size < 800 or "this page can't be found" in t or "skip to main content" in t[:300]:
        empty.append(d.get("doi"))
        continue
    ov = title_overlap(d.get("title", ""), t)
    title_in = any(w in t for w in re.findall(r"[a-z]{5,}", d.get("title", "").lower())[:4])
    if ov < 0.25:
        mismatch.append((d.get("doi"), round(ov, 2), d.get("title", "")[:50], size))
    if any(s in t for s in PRISMA_SIG) and not title_in and size < 6000:
        tmpl.append(d.get("doi"))
    is_course = any(s in t for s in OUM_SIG) and "abstract" not in t[:2000]
    if is_course and not title_in and d.get("doc_type") != "coursework":
        coursework.append(d.get("doi"))
    if not (d.get("doc_type") or d.get("paper_category")):
        dt_missing.append(d.get("doi"))
    st = d.get("full_text_status")
    if st in ("present", "abstract_only") and not (os.path.exists(p) and os.path.getsize(p) > 200):
        status_bad.append(d.get("doi"))

print(f"FULL-COVERAGE full-text check across {N} records:")
print(f"  EMPTY/placeholder-only files: {len(empty)}")
for x in empty: print("    ", x)
print(f"  LIKELY MISMATCHED (title-overlap<25%): {len(mismatch)}")
for doi, ov, title, size in mismatch:
    print(f"    {ov} | {size}B | {doi} | {title}")
print(f"  PRISMA-TEMPLATE files (article replaced by reporting template): {len(tmpl)}")
for x in tmpl: print("    PRISMA:", x)
print(f"  OUM/COURSEWORK wrappers (student kit swapped for research): {len(coursework)}")
for x in coursework: print("    COURSE:", x)
print(f"  status/disk inconsistencies (status=present/abstract_only but file missing/small): {len(status_bad)}")
for x in status_bad: print("    STATUS:", x)
print(f"  doc_type missing: {len(dt_missing)}")
tot = len(empty) + len(mismatch) + len(tmpl) + len(coursework) + len(status_bad)
print(f"\n  => Genuine full-text problems ~ {tot} = {100*tot/N:.1f}%")
print("CAUTION: a 'LIKELY MISMATCHED' / PRISMA / COURSE flag requires READING the file head to")
print("confirm before fixing. empty/placeholder may be INTENTIONAL meta_only (verified Crossref,")
print("body not yet acquired) — do NOT 'fix' those by overwriting with guessed content.")
