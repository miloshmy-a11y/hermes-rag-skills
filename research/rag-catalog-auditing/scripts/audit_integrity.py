#!/usr/bin/env python3
"""
audit_integrity.py — READ-ONLY catalog integrity audit.

Classifies every real-DOI study in a RAG catalog by opening its local full text
(existing TEXT_ file, or PDF extracted via pdftotext) and checking:
  - is the file a real paper (own DOI on title page) or an instrument/assignment?
  - do the index's instrument/population tags match what the text actually uses?

WRITES ONLY a JSON report. NEVER mutates UNIVERSAL_CATALOG.json.
Back up the catalog yourself before any follow-up edit.

Usage:
  python3 audit_integrity.py [CATALOG.json] [BASE_DIR]
If args omitted, auto-detects the universal_rag base dir.
"""
import json, os, re, subprocess, sys
from collections import Counter

def find_pdftotext():
    for p in ("/mingw64/bin/pdftotext", "/usr/bin/pdftotext", "pdftotext"):
        try:
            subprocess.run([p, "-v"], capture_output=True)
            return p
        except Exception:
            continue
    return None

PDFTO = find_pdftotext()

# "used as a tool" phrases per instrument (NOT bare citations)
USED = {
 "ENSS": ["expanded nursing stress scale", " enss ", "ennis"],
 "NSS": ["nursing stress scale"],
 "PSS": ["perceived stress scale"],
 "ERI": ["effort-reward imbalance", "effort reward imbalance", "effort–reward imbalance"],
 "MBI": ["maslach burnout inventory", "maslach burnout", "mbi-hs", "mbi-gs"],
 "NASA-TLX": ["nasa-tlx", "task load index", "nasa task load"],
 "NWSQ": ["nursing worklife survey", "nursing work-life"],
 "STAI": ["state-trait anxiety inventory", "spielberger"],
 "JCQ": ["job content questionnaire"],
 "JS-Q": ["job stress questionnaire"],
 "JDI": ["job descriptive index"],
}

def get_text(base, d):
    files = d.get("files", {})
    for k, v in files.items():
        if isinstance(v, str) and v.startswith("TEXT_"):
            p = os.path.join(base, v)
            if os.path.exists(p):
                return open(p, encoding="utf-8", errors="ignore").read()
    # try PDF via pdftotext (run from terminal in constrained envs)
    if PDFTO:
        for key in ("full_text_pdf", "pdf"):
            v = files.get(key)
            if v:
                for cand in (os.path.join(base, v), v):
                    if os.path.exists(cand):
                        try:
                            r = subprocess.run([PDFTO, "-layout", cand, "-"],
                                               capture_output=True, text=True, timeout=60)
                            if r.returncode == 0:
                                return r.stdout
                        except Exception:
                            pass
    # original_source (external drive) — read only
    osrc = files.get("original_source")
    if osrc and os.path.exists(osrc):
        try:
            if osrc.lower().endswith(".pdf") and PDFTO:
                r = subprocess.run([PDFTO, "-layout", osrc, "-"], capture_output=True, text=True, timeout=60)
                return r.stdout if r.returncode == 0 else ""
            return open(osrc, encoding="utf-8", errors="ignore").read()
        except Exception:
            return ""
    return ""

def index_instruments(d):
    out = set()
    for ins in d.get("instrument", []):
        if ins in ("Not specified",):
            continue
        for c in USED:
            if c.lower() in ins.lower():
                out.add(c); break
    return out

def classify(d, text):
    doi = (d.get("doi") or "").lower().strip()
    head = text[:4000].lower()
    instr_sig = bool(re.search(r"(questionnaire|validity and reliability|user manual|"
                               r"assessment tool|kuesioner|instrument was|we developed)", head))
    assign_sig = bool(re.search(r"(final year project|submitted in fulfilment|partial fulfilment|"
                                r"this assignment|this thesis|in partial fulfilment)", head))
    own = doi[:16] in head.replace("\n", " ")
    if not text:
        return "NO_TEXT"
    if assign_sig:
        return "ASSIGNMENT/THESIS"
    if instr_sig and not own:
        return "INSTRUMENT/TOOL?"
    if own:
        return "PAPER(own DOI)"
    return "PAPER?"

def main():
    cat_path = sys.argv[1] if len(sys.argv) > 1 else None
    base = sys.argv[2] if len(sys.argv) > 2 else None
    if base is None:
        cands = [os.getcwd(),
                 os.path.join(os.path.expanduser("~"), "AppData", "Local", "hermes",
                              "cache", "web", "universal_rag")]
        for c in cands:
            if cat_path is None and os.path.exists(os.path.join(c, "UNIVERSAL_CATALOG.json")):
                base = c; cat_path = os.path.join(c, "UNIVERSAL_CATALOG.json"); break
    if cat_path is None:
        cat_path = os.path.join(base or ".", "UNIVERSAL_CATALOG.json")
    with open(cat_path, encoding="utf-8") as f:
        cat = json.load(f)
    docs = cat["documents"]
    rows = []
    for d in docs:
        doi = (d.get("doi") or "").lower().strip()
        if not doi.startswith("10.") or "bad_doi" in d.get("flags", []):
            continue
        if d.get("doc_class") == "working_file":
            continue
        text = get_text(base, d)
        verdict = classify(d, text)
        used = set(c for c, ph in USED.items() if any(p in text.lower() for p in ph)) if text else set()
        idx = index_instruments(d)
        spurious = sorted(idx - used)
        rows.append({
            "doi": doi, "title": d.get("title", ""), "domain": d.get("domain"),
            "verified": "VERIFIED" in str(d.get("verification_status", "")),
            "index_instruments": sorted(idx), "instruments_in_text": sorted(used),
            "spurious_instrument_tags": spurious,
            "verdict": verdict,
            "own_doi_on_title_page": (verdict == "PAPER(own DOI)"),
        })
    out_path = os.path.join(base or ".", "FILE_BY_FILE_VERIFICATION.json")
    json.dump({"pdftotext_available": bool(PDFTO), "entries": rows},
              open(out_path, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    vc = Counter(r["verdict"] for r in rows)
    print("pdftotext:", PDFTO)
    print("Classification:")
    for k, n in vc.most_common():
        print(f"  {k}: {n}")
    suspects = [r for r in rows if r["verdict"] in ("INSTRUMENT/TOOL?", "ASSIGNMENT/THESIS")
                or r["spurious_instrument_tags"]]
    print(f"\nSUSPECT (non-paper or spurious tags): {len(suspects)} -> review before any edit")
    for s in suspects[:20]:
        print(f"  {s['verdict']:17} {s['doi'][:32]} | {s['title'][:40]}")
    print(f"\nReport: {out_path}")

if __name__ == "__main__":
    main()
