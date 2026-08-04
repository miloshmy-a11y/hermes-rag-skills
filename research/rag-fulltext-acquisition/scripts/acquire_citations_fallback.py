#!/usr/bin/env python3
"""
Fallback full-text acquisition for DOIs that failed direct PDF (paywalled publishers:
Wiley / Elsevier / SAGE / Wolters Kluwer / APA PsycNet / Karger). Follows the RAG chain
steps 6-7: Semantic Scholar paper-page HTML + PubMed abstract. Verified this session:
filled 50/53 paywalled FYP citations.

Run via TERMINAL Python. Usage:
  python3 acquire_citations_fallback.py --cat <catalog.json> --thesis <doi>
  python3 acquire_citations_fallback.py --cat <catalog.json> --dois d1 d2 ...
Registers files.extracted_text (markdown) + full_text_status: pending_s2_page / pending_pubmed
(mark for later LLM content-verification — do NOT trust as full text until verified).
"""
import os, json, re, sys, urllib.request, urllib.parse, time, argparse

EXTRACTED = r"C:\Users\Milos\AppData\Local\hermes\cache\web\universal_rag\EXTRACTED"
UA = {"User-Agent": "Mozilla/5.0 (research; hermes-rag)"}

def get(url, timeout=30):
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read().decode("utf-8", "ignore"), r.headers.get("content-type", "")
    except Exception:
        return None, ""

def norm(d): return d.replace("https://doi.org/", "").lower().rstrip("/")

def s2_fetch(dn):
    j, _ = get(f"https://api.semanticscholar.org/graph/v1/paper/DOI:{dn}?fields=paperId,abstract,title")
    if not j: return None
    try: pid = json.loads(j).get("paperId")
    except Exception: return None
    if not pid: return None
    page, _ = get(f"https://www.semanticscholar.org/paper/{pid}")
    return page if page and len(page) > 2000 else None

def pubmed_fetch(dn):
    j, _ = get(f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term={urllib.parse.quote(dn)}&retmode=json")
    if not j: return None
    try: pmids = json.loads(j)["esearchresult"]["idlist"]
    except Exception: return None
    if not pmids: return None
    ab, _ = get(f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id={pmids[0]}&rettype=abstract&retmode=text")
    return ab if ab and len(ab) > 500 else None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cat", required=True)
    ap.add_argument("--dois", nargs="*", default=[])
    ap.add_argument("--thesis", default=None)
    a = ap.parse_args()
    cat = json.loads(open(a.cat, encoding="utf-8").read())
    docs = cat["documents"]
    by_norm = {norm(d.get("doi")): d for d in docs if d.get("doi")}
    if a.thesis:
        t = open((by_norm[norm(a.thesis)].get("files") or {}).get("extracted_text"), encoding="utf-8", errors="ignore").read()
        m = re.search(r"(?i)references?\s*\n", t)
        a.dois = list({x.rstrip(".,;") for x in re.findall(r"10\.\d{4,9}/[^\s)\]<>\"']+", t[m.start():])})
    targets = [(d, by_norm.get(norm(d))) for d in a.dois if by_norm.get(norm(d))
               and not ((by_norm[norm(d)].get("files") or {}).get("extracted_text"))]
    ok = 0
    for i, (doi, doc) in enumerate(targets, 1):
        dn = norm(doi)
        out = os.path.join(EXTRACTED, dn.replace("/", "_").replace(".", "_")[:80] + ".txt")
        got, src = None, None
        s2 = s2_fetch(dn)
        if s2: got, src = s2, "s2_page"
        if not got:
            pm = pubmed_fetch(dn)
            if pm: got, src = pm, "pubmed"
        if got:
            open(out, "w", encoding="utf-8").write(got)
            doc.setdefault("files", {})["extracted_text"] = out
            doc["full_text_status"] = f"pending_{src}"
            ok += 1
            print(f"[{i}/{len(targets)}] OK {src:9} {doi}")
        else:
            print(f"[{i}/{len(targets)}] FAIL {doi}")
        time.sleep(0.4)
    open(a.cat, "w", encoding="utf-8").write(json.dumps(cat, ensure_ascii=False, indent=1))
    print(f"Fallback DONE: {ok}/{len(targets)} got text (S2/PubMed). Rest remain META.")

if __name__ == "__main__":
    main()
