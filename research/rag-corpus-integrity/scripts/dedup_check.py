"""
dedup_check.py — RAG catalog duplicate detector (READ-ONLY report).

RULE (validated 2026-08-04): two records sharing a DOI is NOT automatically a
true duplicate. One of them may be a DIFFERENT study carrying a WRONG DOI, or a
preprint/published pair of the SAME study under two DOIs. This script reports
candidates and classifies them; it NEVER deletes. Deletion/merge is a separate,
human-confirmed step via the merge recipe in SKILL.md.

Usage:
  python3 dedup_check.py [path/to/UNIVERSAL_CATALOG.json]

Output:
  - Exact DOI collisions (same DOI, >1 record) -> inspect both for wrong-DOI
  - Same normalized title under DIFFERENT DOIs -> usually true dup (preprint/published)
  - Near-duplicate titles (Jaccard>=0.6 on title tokens, diff DOI) -> review
Exit 0 always (report only).
"""
import json
import os
import re
import sys
from collections import Counter, defaultdict

DEFAULT = os.environ.get(
    "UNIVERSAL_CATALOG",
    os.path.join(
        os.environ.get("HERMES_HOME", os.path.expanduser("~")),
        "AppData", "Local", "hermes", "cache", "web", "universal_rag",
        "UNIVERSAL_CATALOG.json",
    ),
)



def norm_title(t):
    t = str(t or "").lower()
    t = re.sub(r"[^a-z0-9 ]", " ", t)
    stop = {"the", "a", "an", "of", "in", "on", "among", "and", "for", "to",
            "with", "at", "by", "from", "between", "vs", "versus", "study",
            "cross", "sectional", "version", "v"}
    return re.sub(r"\s+", " ", t).strip()


def title_tokens(t):
    return set(w for w in norm_title(t).split() if w not in stop and len(w) > 2)


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT
    if not os.path.exists(path):
        print("CATALOG NOT FOUND:", path)
        return 1
    docs = json.load(open(path, encoding="utf-8"))
    print(f"Catalog: {len(docs)} docs\n")

    # 1) Exact DOI collisions
    by_doi = defaultdict(list)
    for i, d in enumerate(docs):
        doi = d.get("doi")
        if doi:
            by_doi[doi].append(i)
    collisions = {k: v for k, v in by_doi.items() if len(v) > 1}
    print(f"=== 1) EXACT DOI COLLISIONS: {len(collisions)} ===")
    for doi, idxs in collisions.items():
        print(f"  DOI={doi}")
        for ix in idxs:
            d = docs[ix]
            print(f"    [{ix}] title={str(d.get('title'))[:60]} | yr={d.get('year')} | auth={str(d.get('authors'))[:40]}")
        print("    >> ACTION: compare titles/authors. If DIFFERENT -> one has a WRONG DOI (flag for review, do NOT delete). If SAME -> true dup, merge.")

    # 2) Same normalized title, different DOIs (usually true dup)
    by_title = defaultdict(list)
    for i, d in enumerate(docs):
        nt = norm_title(d.get("title"))
        if nt:
            by_title[nt].append(i)
    exact_dup = {}
    for nt, idxs in by_title.items():
        if len(idxs) > 1:
            doies = set(docs[ix].get("doi") for ix in idxs)
            if len(doies) > 1:
                exact_dup[nt] = [docs[ix].get("doi") for ix in idxs]
    print(f"\n=== 2) SAME TITLE / DIFFERENT DOI (likely true dup): {len(exact_dup)} ===")
    for nt, doies in exact_dup.items():
        print(f"  '{nt[:60]}' -> {doies}")
        print("    >> ACTION: verify same study (authors/year match), then merge: keep published DOI, remove preprint/local stub, record merged_from.")

    # 3) Near-dup titles (Jaccard>=0.6, diff DOI)
    N = len(docs)
    near = []
    for i in range(N):
        ti = title_tokens(docs[i].get("title"))
        if not ti:
            continue
        for j in range(i + 1, N):
            tj = title_tokens(docs[j].get("title"))
            if not tj or docs[i].get("doi") == docs[j].get("doi"):
                continue
            inter = ti & tj
            union = ti | tj
            if union and len(inter) / len(union) >= 0.6:
                near.append((i, j, round(len(inter) / len(union), 2)))
    print(f"\n=== 3) NEAR-DUP TITLES (Jaccard>=0.6, diff DOI): {len(near)} ===")
    for i, j, sc in near:
        print(f"  [{i}]<->[{j}] j={sc}")
        print(f"      A: {str(docs[i].get('title'))[:60]}")
        print(f"      B: {str(docs[j].get('title'))[:60]}")
        print("    >> ACTION: read both; if same study -> merge; if different studies -> KEEP BOTH (do not merge).")

    print("\nDone. Report only — no files modified.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
