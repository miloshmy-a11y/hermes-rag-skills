#!/usr/bin/env python3
"""
Batch-acquire full text for a list of DOIs (or all META-only citations of a thesis),
following the RAG full-text retrieval chain steps 1-3:
  OpenAlex oa_url -> Unpaywall -> Europe PMC  (direct PDF where bot-accessible)
Then extract via the canonical helper and register files.extracted_text.

Run via TERMINAL Python (C:\Python314) — needs network + PyMuPDF.
Usage:
  python3 acquire_citations_batch.py --cat <catalog.json> --dois d1 d2 ...
  python3 acquire_citations_batch.py --cat <catalog.json> --thesis <doi>   # harvest thesis refs, fill missing
Backs up the catalog before writing.
"""
import os, json, re, sys, subprocess, urllib.request, time, argparse

HELPER = r"C:\Users\Milos\AppData\Local\hermes\skills\software-development\pdf-processing\pdf_extract.py"
EXTRACTED = r"C:\Users\Milos\AppData\Local\hermes\cache\web\universal_rag\EXTRACTED"
SOURCE_PDFS = r"C:\Users\Milos\AppData\Local\hermes\cache\web\universal_rag\SOURCE_PDFS"
UA = {"User-Agent": "Mozilla/5.0 (research; hermes-rag)"}

def get(url, timeout=30):
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read(), r.headers.get("content-type", "")
    except Exception:
        return None, ""

def is_pdf(b): return b and b[:4] == b"%PDF" and len(b) > 5000

def norm(d): return d.replace("https://doi.org/", "").lower().rstrip("/")

def acquire_pdf(doi):
    dn = norm(doi)
    # 1) OpenAlex
    try:
        data, _ = get(f"https://api.openalex.org/works/https://doi.org/{dn}")
        if data:
            j = json.loads(data)
            oa = (j.get("best_oa_location") or {}).get("pdf_url") or (j.get("open_access") or {}).get("oa_url")
            if oa:
                b, _ = get(oa)
                if is_pdf(b): return b, "openalex"
    except Exception: pass
    # 2) Unpaywall
    try:
        data, _ = get(f"https://api.unpaywall.org/v2/{dn}?email=hermes.rag@example.com")
        if data:
            j = json.loads(data)
            l = (j.get("best_oa_location") or {}).get("url_for_pdf") or (j.get("best_oa_location") or {}).get("url")
            if l:
                b, _ = get(l)
                if is_pdf(b): return b, "unpaywall"
    except Exception: pass
    # 3) Europe PMC
    try:
        data, _ = get(f"https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=DOI:{dn}&format=json")
        if data:
            res = (json.loads(data).get("resultList") or {}).get("result") or []
            if res and res[0].get("pmid"):
                b, _ = get(f"https://europepmc.org/backend/ptpmcrender?accid={res[0]['pmid']}&pdf=1")
                if is_pdf(b): return b, "europepmc"
    except Exception: pass
    return None, "failed"

def extract_and_register(pdf_path, doc):
    r = subprocess.run([sys.executable, HELPER, "--pdf", pdf_path, "--outdir", EXTRACTED],
                       capture_output=True, text=True, timeout=120)
    try:
        meta = json.loads(r.stdout.strip().splitlines()[-1])
        txt = meta.get("txt")
    except Exception:
        txt = None
    if txt and os.path.exists(txt):
        doc.setdefault("files", {})["extracted_text"] = txt
        doc["full_text_status"] = "present"
        return True
    return False

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cat", required=True)
    ap.add_argument("--dois", nargs="*", default=[])
    ap.add_argument("--thesis", default=None)
    a = ap.parse_args()

    cat = json.loads(open(a.cat, encoding="utf-8").read())
    docs = cat["documents"]
    by_norm = {norm(d.get("doi")): d for d in docs if d.get("doi")}
    os.makedirs(SOURCE_PDFS, exist_ok=True)

    if a.thesis:
        t = open((by_norm[norm(a.thesis)].get("files") or {}).get("extracted_text"), encoding="utf-8", errors="ignore").read()
        m = re.search(r"(?i)references?\s*\n", t)
        a.dois = list({x.rstrip(".,;") for x in re.findall(r"10\.\d{4,9}/[^\s)\]<>\"']+", t[m.start():])})

    targets = []
    for d in a.dois:
        doc = by_norm.get(norm(d))
        if not doc: continue
        p = (doc.get("files") or {}).get("extracted_text")
        if not (p and os.path.exists(p)):
            targets.append((d, doc))

    # backup
    open(a.cat + f".bak_{int(time.time())}", "w", encoding="utf-8").write(json.dumps(cat, ensure_ascii=False, indent=1))

    ok = 0
    for i, (doi, doc) in enumerate(targets, 1):
        fn = norm(doi).replace("/", "_").replace(".", "_")[:80]
        pdf = os.path.join(SOURCE_PDFS, fn + ".pdf")
        b, src = acquire_pdf(doi)
        if b:
            open(pdf, "wb").write(b)
            if extract_and_register(pdf, doc):
                ok += 1
                print(f"[{i}/{len(targets)}] OK {src:10} {doi}")
            else:
                print(f"[{i}/{len(targets)}] EXTRACT-FAIL {doi}")
        else:
            print(f"[{i}/{len(targets)}] NOPDF {doi}")
        time.sleep(0.3)

    open(a.cat, "w", encoding="utf-8").write(json.dumps(cat, ensure_ascii=False, indent=1))
    print(f"DONE: {ok}/{len(targets)} acquired+extracted. Remaining need S2/PubMed fallback.")

if __name__ == "__main__":
    main()
