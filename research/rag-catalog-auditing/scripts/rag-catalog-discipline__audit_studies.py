#!/usr/bin/env python3
"""Read-only audit of `study` docs in a universal_rag catalog.

Mirrors rag-catalog-discipline rules 3 & 8. Catches the exact defects this user
rejects: studies with missing identifier, incomplete metadata, full-text paths
that don't resolve, duplicate DOIs, and claimed-pending entries that actually
have a file. Report-only by default (flag-don't-overwrite discipline).

Run:
  python3 scripts/audit_studies.py [--catalog PATH] [--report PATH] [--fix-meta]

  --fix-meta  Additive ONLY: if a study has no abstract but its extracted_text
              file exists, pull the first 1500 chars into `abstract`. Never
              deletes or overwrites existing metadata. Off by default.

Default catalog path is the user's universal_rag index; override with --catalog.
"""
import argparse, json, os
from collections import defaultdict

DEFAULT = r"C:\Users\Milos\AppData\Local\hermes\cache\web\universal_rag\UNIVERSAL_CATALOG.json"


def has_id(d):
    return bool(d.get("doi")) or bool(d.get("url"))


def has_meta(d):
    return (bool((d.get("title") or "").strip()) and bool(d.get("year")) and
            (bool(d.get("abstract") and len(d.get("abstract", "")) > 50) or
             bool(d.get("authors")) or bool(d.get("keywords")) or bool(d.get("tags"))))


def ft_path(d):
    f = d.get("files", {}) or {}
    return (f.get("full_text_pdf") or f.get("full_text_html") or
            f.get("extracted_text") or f.get("full_text_md"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--catalog", default=DEFAULT)
    ap.add_argument("--report", default=None)
    ap.add_argument("--fix-meta", action="store_true",
                    help="Additive only: fill missing abstract from extracted_text")
    args = ap.parse_args()

    cat = json.load(open(args.catalog, encoding="utf-8"))
    docs = cat["documents"]
    studies = [d for d in docs if d.get("doc_type") == "study"]

    no_id, incomplete, broken, pending_but_present = [], [], [], []
    for d in studies:
        if not has_id(d):
            no_id.append(d)
        if not has_meta(d):
            incomplete.append(d)
        p = ft_path(d)
        if p and not os.path.exists(p):
            broken.append(d)
        elif p and os.path.exists(p) and d.get("full_text_status") in (
                "pending", "pending_user_upload", "stub_or_empty_needs_retry"):
            pending_but_present.append(d)

    by = defaultdict(list)
    for d in docs:
        if d.get("doi"):
            by[d["doi"].lower()].append(d)
    dups = {k: [x.get("title") for x in v] for k, v in by.items() if len(v) > 1}

    report = {
        "total_docs": len(docs),
        "studies": len(studies),
        "no_identifier": [d.get("title") for d in no_id],
        "incomplete_metadata": [(d.get("domain"), d.get("title")) for d in incomplete],
        "fulltext_path_broken": [d.get("title") for d in broken],
        "pending_but_file_present": [d.get("title") for d in pending_but_present],
        "duplicate_dois": dups,
    }
    out = json.dumps(report, indent=2, ensure_ascii=False)
    if args.report:
        open(args.report, "w", encoding="utf-8").write(out)
        print("Wrote report ->", args.report)
    print(f"Studies: {len(studies)} | no_id: {len(no_id)} | incomplete: "
          f"{len(incomplete)} | broken_paths: {len(broken)} | "
          f"pending_but_present: {len(pending_but_present)} | dup_dois: {len(dups)}")

    if args.fix_meta:
        changed = 0
        for d in incomplete:
            p = ft_path(d)
            if p and os.path.exists(p) and os.path.getsize(p) > 200:
                try:
                    txt = open(p, encoding="utf-8", errors="ignore").read()
                    if len(txt) > 50:
                        d["abstract"] = d.get("abstract") or txt[:1500]
                        changed += 1
                except Exception:
                    pass
        if changed:
            json.dump(cat, open(args.catalog, "w", encoding="utf-8"),
                      indent=2, ensure_ascii=False)
            print(f"--fix-meta added abstracts to {changed} studies (additive only)")


if __name__ == "__main__":
    main()
