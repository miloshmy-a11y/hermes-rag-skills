#!/usr/bin/env python3
"""Robust PDF text + metadata extractor for the Hermes RAG pipeline.

WHY THIS EXISTS:
  The Hermes execute_code venv (Python 3.11) has NO PDF libraries and no pip.
  The system Python 3.14 (C:/Python314/python.exe) HAS PyMuPDF (fitz) 1.28,
  and MinGW provides a pdftotext CLI. So PDF work must run via terminal(),
  never via import fitz inside execute_code.

USAGE (from execute_code, via terminal):
  terminal(f'python3 "{SCRIPT}" --pdf "{src}" --outdir "{outdir}"')

STRATEGY (in order, first that yields text wins):
  1. PyMuPDF (fitz)  -> best text + layout
  2. pdftotext -layout (poppler/mingw CLI)
  3. OCR stub (tesseract) -> prints WARNING, does NOT silently fail
Outputs:
  <outdir>/<stem>.txt          full extracted text
  <outdir>/<stem>_meta.json    recovered {title, authors, year, abstract, keywords, pages, empty_pages}
Exit code 0 on success; non-zero only if NOTHING could be extracted.
"""
import argparse, json, os, re, subprocess, sys

def extract_pymupdf(pdf):
    import fitz
    doc = fitz.open(pdf)
    pages = [p.get_text() for p in doc]
    full = "\n".join(pages)
    empty = sum(1 for p in pages if not p.strip())
    return full, doc.page_count, empty

def extract_pdftotext(pdf):
    r = subprocess.run(["pdftotext", "-layout", pdf, "-"],
                       capture_output=True, text=True, timeout=120)
    if r.returncode == 0 and r.stdout.strip():
        return r.stdout, None, None
    return None, None, None

def recover_metadata(text, filename_stem):
    """Heuristic metadata recovery from extracted text."""
    meta = {"title": None, "authors": None, "year": None,
            "abstract": None, "keywords": None, "pages_text": len(text)}
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    # Year: 4-digit 19xx/20xx
    yrs = re.findall(r"\b(19\d{2}|20\d{2})\b", text)
    yrs_int = [int(y) for y in yrs if 1900 <= int(y) <= 2026]
    if yrs_int:
        meta["year"] = max(yrs_int)
    # Abstract block (between ABSTRACT and KEYWORDS/INTRODUCTION/ABSTRAK)
    m = re.search(r"ABSTRACT\s*(.*?)\s*(KEYWORDS|INTRODUCTION|ABSTRAK)", text, re.IGNORECASE | re.DOTALL)
    if m:
        meta["abstract"] = re.sub(r"\s+", " ", m.group(1))[:2000].strip()
        # Keywords often follow the abstract delimiter
        km = re.search(r"KEYWORDS?:?\s*(.+)", text[m.end():m.end()+400], re.IGNORECASE)
        if km:
            meta["keywords"] = [x.strip().rstrip(";,") for x in re.split(r"[;,]", km.group(1)) if x.strip()][:12]
    # Authors + Title: look at the top block (first ~12 lines before ABSTRACT/INTRODUCTION)
    head = "\n".join(lines[:12])
    head_clean = "\n".join(lines[:12])
    # Title: ALL-CAPS line (length > 10, no 'journal'/'vol'/'doi') in first 6 lines
    for ln in lines[:6]:
        if len(ln) > 10 and ln == ln.upper() and not re.search(r"JOURNAL|VOL\.|DOI|HTTP|ORIGINAL ARTICLE", ln):
            meta["title"] = ln.title()
            break
    # Authors: line(s) containing numbered affiliations like "1Name, Place" or "Name1, Name2*"
    am = re.search(r"([A-Z][\w.\-]+(?:\s+[A-Z][\w.\-]+){1,3}(?:,| and |&|\n)[^\n]*(?:University|Hospital|School|College|Department|Institute|Malaysia|Korea)[^\n]*)", head, re.IGNORECASE)
    if am:
        raw = re.split(r",\s*(?=\d)| and |&", am.group(1))
        meta["authors"] = [a.strip().rstrip(",").strip() for a in raw if a.strip() and len(a.strip()) > 3][:12]
    return meta

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--meta-only", action="store_true", help="skip writing full text, only meta json")
    args = ap.parse_args()

    pdf = args.pdf
    if not os.path.exists(pdf):
        print("ERROR: pdf not found:", pdf, file=sys.stderr); sys.exit(2)
    os.makedirs(args.outdir, exist_ok=True)
    stem = os.path.splitext(os.path.basename(pdf))[0]
    txt_path = os.path.join(args.outdir, stem + ".txt")
    meta_path = os.path.join(args.outdir, stem + "_meta.json")

    full, pages, empty = None, None, None
    method = None
    try:
        full, pages, empty = extract_pymupdf(pdf); method = "pymupdf"
    except Exception as e:
        print(f"pymupdf failed: {e}", file=sys.stderr)
    if not full or not full.strip():
        try:
            full, pages, empty = extract_pdftotext(pdf); method = "pdftotext" if full else None
        except Exception as e:
            print(f"pdftotext failed: {e}", file=sys.stderr)

    if not full or not full.strip():
        # Image-only / OCR needed
        print("WARNING: no text layer found — OCR (tesseract) not configured. "
              "Mark as needs_ocr and upload a text version or run OCR.", file=sys.stderr)
        meta = {"title": None, "authors": None, "year": None,
                "abstract": None, "keywords": None, "pages": pages,
                "empty_pages": empty, "needs_ocr": True, "method": "none"}
        json.dump(meta, open(meta_path, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
        sys.exit(3)

    if not args.meta_only:
        open(txt_path, "w", encoding="utf-8").write(full)
    meta = recover_metadata(full, stem)
    meta["pages"] = pages; meta["empty_pages"] = empty; meta["method"] = method
    meta["char_count"] = len(full)
    json.dump(meta, open(meta_path, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print(json.dumps({"ok": True, "method": method, "chars": len(full),
                      "pages": pages, "empty_pages": empty,
                      "txt": txt_path if not args.meta_only else None,
                      "meta": meta_path}, ensure_ascii=False))
    sys.exit(0)

if __name__ == "__main__":
    main()
