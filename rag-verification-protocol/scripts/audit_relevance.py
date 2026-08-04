#!/usr/bin/env python3
"""Random RELEVANCE audit. Samples full-text records and checks whether the paper is
actually about nursing occupational stress / nurse workforce (thesis topic), using
keyword detection on title+abstract+body. Flags possible OFF-TOPIC records for agent
verification by reading. Read-only reporter; agent decides on off-topic marking.

Usage: python audit_relevance.py
Re-runnable; uses a fresh random seed each call. Pairs with audit_fulltext_mismatch.py
(file integrity) and audit_full_coverage.py (country) for full-coverage passes.
"""
import os, json, re, random

CAT = r"C:\Users\Milos\AppData\Local\hermes\cache\web\universal_rag\UNIVERSAL_CATALOG.json"
data = json.loads(open(CAT, encoding="utf-8").read())
docs = data["documents"]

real = [d for d in docs if not str(d.get("doi","")).startswith("local:")
        and (d.get("files") or {}).get("extracted_text")
        and os.path.exists((d.get("files") or {}).get("extracted_text"))
        and not d.get("is_duplicate_of")]

random.seed(random.randint(1,10**9))
sample = random.sample(real, 12)

# Nurse/workforce context
NURSE = r"\b(nurs\w*|nursing)\b"
WORKFORCE = r"\b(health\s?care worker|healthcare worker|medical staff|hospital staff|clinical staff|health\s?care professional)\b"
# Stress/work concept
STRESS = r"\b(stress|burnout|job demand|workload|occupational|work[-\s]?related|patient safety|workplace violen\w*|fatigue|shift work|job satisfaction|work engagement|turnover)\b"
# Off-topic populations (non-nurse)
OFFPOP = r"\b(student\w*|patient\w*|parent\w*|child\w*|adolescent\w*|animal\w*|rat\b|mouse|tumor|cancer|gene|cell\w*|plant\w*)\b"

def scan(d):
    p=(d.get("files") or {}).get("extracted_text")
    t=open(p,encoding="utf-8",errors="ignore").read().lower()
    nurse = bool(re.search(NURSE,t)) or bool(re.search(WORKFORCE,t))
    stress = bool(re.search(STRESS,t))
    offpop = bool(re.search(OFFPOP,t))
    return nurse, stress, offpop, t

print(f"Audited 12 random records (of {len(real)}) for nursing-stress relevance:\n")
flags=[]
for d in sample:
    nurse, stress, offpop, t = scan(d)
    # Relevant if nurse-context present (with or without explicit stress word, since many nurse papers are stress-related)
    relevant = nurse
    if not relevant:
        # Maybe a healthcare-worker stress paper without 'nurse' word
        if stress and bool(re.search(WORKFORCE,t)):
            relevant=True
    status = "RELEVANT" if relevant else "CHECK-OFFTOPIC"
    if not relevant:
        flags.append(d)
    print(f"  [{status}] nurse={nurse} stress={stress} offpop={offpop} | {d.get('title','')[:52]}")

print(f"\nFlagged for verification: {len(flags)}")
for d in flags:
    print(f"   {d.get('doi')} | {d.get('title','')[:50]}")
print("\nNOTE: off-topic records should be tagged relevance='off_topic' (keep, exclude at query time),")
print("not deleted. Verify each flag by READING the abstract before tagging.")
