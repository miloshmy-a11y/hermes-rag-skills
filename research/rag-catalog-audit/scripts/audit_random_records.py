#!/usr/bin/env python3
"""Read-only random-sample catalog auditor (mutates NOTHING).
Picks 10 random full-text records, verifies indexed title/year/country/measures against
the actual text, and reports flags. The agent reviews flags and fixes ONLY genuine issues.

Usage: python audit_random_records.py   (run from the catalog dir, or set CAT below)
"""
import os, json, random, re

CAT = r"C:\Users\Milos\AppData\Local\hermes\cache\web\universal_rag\UNIVERSAL_CATALOG.json"

COUNTRY_WORDS = ["malaysia","pakistan","saudi","bangladesh","iran","china","taiwan","nigeria",
 "indonesia","italy","thailand","jordan","india","japan","united states","usa","u.s.",
 "united kingdom","england","scotland","australia","turkey","korea","greece","germany",
 "brazil","canada","iraq","lebanon","oman","qatar","kuwait","uae","kenya","south africa",
 "ethiopia","egypt","philippines","vietnam","spain","netherlands","france","mexico","chile"]
CCODE = {"malaysia":"MY","pakistan":"PK","saudi":"SA","bangladesh":"BD","iran":"IR","china":"CN",
 "taiwan":"TW","nigeria":"NG","indonesia":"ID","italy":"IT","thailand":"TH","jordan":"JO",
 "india":"IN","japan":"JP","united states":"US","usa":"US","u.s.":"US","united kingdom":"GB",
 "england":"GB","scotland":"GB","australia":"AU","turkey":"TR","korea":"KR","greece":"GR",
 "germany":"DE","brazil":"BR","canada":"CA","iraq":"IQ","lebanon":"LB","oman":"OM","qatar":"QA",
 "kuwait":"KW","uae":"AE","kenya":"KE","south africa":"ZA","ethiopia":"ET","egypt":"EG",
 "philippines":"PH","vietnam":"VN","spain":"ES","netherlands":"NL","france":"FR","mexico":"MX","chile":"CL"}

def norm(s):
    return re.sub(r"[\u00a0\u2010-\u2015\u2212]","-", s).lower()

data = json.loads(open(CAT, encoding="utf-8").read())
docs = data["documents"]
real = [d for d in docs if not str(d.get("doi","")).startswith("local:")
        and (d.get("files") or {}).get("extracted_text")
        and os.path.exists((d.get("files") or {}).get("extracted_text"))
        and not d.get("is_duplicate_of")]
random.seed(random.randint(1, 10**9))
sample = random.sample(real, 10)

print(f"Audited 10 of {len(real)} full-text records:\n")
for d in sample:
    p = (d.get("files") or {}).get("extracted_text")
    t = open(p, encoding="utf-8", errors="ignore").read()
    tl = t.lower()
    idx_title = (d.get("title") or "").strip()
    title_ok = norm(idx_title[:35]) in norm(t)
    body = re.sub(r"downloaded from.*?wiley.*?on \[.*?\]", " ", tl)
    body = re.sub(r"terms and conditions.*?wiley", " ", body)
    ctry_found = sorted(set(m.group(1) for m in re.finditer(r"\b("+"|".join(COUNTRY_WORDS)+r")\b", body)))
    cc = [CCODE[c] for c in ctry_found if c in CCODE]
    meas = d.get("measures") or []
    meas_missing = [m for m in meas if m and m.lower() not in tl]
    kw = d.get("keywords_llm") or []
    flags = []
    if not title_ok: flags.append("TITLE-NOT-IN-TEXT")
    if d.get("country") not in (None,"") and cc and d["country"] not in cc:
        flags.append(f"COUNTRY-MISMATCH(idx={d['country']},text={cc})")
    if d.get("country") in (None,"") and cc:
        flags.append(f"COUNTRY-MISSING(text={cc})")
    if meas_missing: flags.append(f"MEASURES-NOT-IN-TEXT({meas_missing})")
    if len(kw) == 0: flags.append("KW-EMPTY")
    status = "OK" if not flags else " | ".join(flags)
    print(f"  [{status}] {d.get('year')} | {idx_title[:55]}")
    if flags:
        print(f"        doi={d.get('doi')} | country(idx)={d.get('country')} text={cc} | meas={meas}")
print("\nAudit complete. Review flags; fix only genuine issues (ignore review/multi-country/download-IP false positives).")
