#!/usr/bin/env python3
"""Fetch open-access full text for catalog entries that lack a local PDF.

Legitimate sources only (Unpaywall / PMC / publisher OA). No Sci-Hub/LibGen.
Run:  python3 download_fulltext.py            # first pass (Thesis_References lacking PDF)
      python3 download_fulltext.py --retry     # only re-attempt logged failures
Backs up the catalog to backups/CAT_before_download_<ts>.json before writing.
"""
import os, sys, json, gzip, time, urllib.request, urllib.error
from datetime import datetime

BASE = os.path.dirname(os.path.abspath(__file__))
CAT = os.path.join(BASE, "UNIVERSAL_CATALOG.json")
DEST = os.path.join(BASE, "SOURCE_PDFS")
os.makedirs(DEST, exist_ok=True)
EMAIL = "rag.rebuild@example.org"
UA = f"hermes-rag/1.0 (mailto:{EMAIL})"
BROWSER_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
ACCEPT = "application/pdf,*/*"


def unpaywall(doi):
    url = f"https://api.unpaywall.org/v2/{doi}?email={EMAIL}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=25) as r:
            return json.loads(r.read())
    except Exception as e:
        return {"_err": str(e)[:80]}


def fetch(url, ua=BROWSER_UA):
    req = urllib.request.Request(url, headers={"User-Agent": ua, "Accept": ACCEPT})
    return urllib.request.urlopen(req, timeout=40)


def try_get(doi):
    up = unpaywall(doi)
    if up.get("_err"):
        return None, up["_err"]
    locs = up.get("oa_locations", [])
    if up.get("best_oa_location"):
        locs = [up["best_oa_location"]] + locs
    cands = []
    pmcid = up.get("pmcid") or up.get("best_oa_location", {}).get("pmcid")
    if pmcid:
        cands.append(f"https://www.ncbi.nlm.nih.gov/pmc/articles/{pmcid}/pdf")
    for l in locs:
        if l.get("url_for_pdf"):
            cands.append(l["url_for_pdf"])
        if l.get("url"):
            cands.append(l["url"])
    # publisher-specific
    if doi.startswith("10.1186/"):
        cands.append(f"https://link.springer.com/content/pdf/{doi}.pdf")
    if doi.startswith("10.3390/"):
        parts = doi.split("/")
        if len(parts) >= 3:
            cands.append(f"https://www.mdpi.com/{parts[1]}/{parts[2]}/{parts[2]}.pdf")
    if doi.startswith("10.1371/"):
        cands.append(f"https://journals.plos.org/plosone/article/file?id={doi}&type=printable")
    for c in cands:
        try:
            r = fetch(c)
            data = r.read()
            if len(data) > 5000 and data[:5] == b"%PDF-":
                return data, c
        except Exception:
            continue
    return None, f"{len(cands)} candidates tried, none gave PDF"


def main():
    retry = "--retry" in sys.argv
    cat = json.load(open(CAT, encoding="utf-8"))
    docs = cat["documents"]
    log = json.load(open(os.path.join(BASE, "FULLTEXT_DOWNLOAD_LOG.json"), encoding="utf-8")) \
        if os.path.exists(os.path.join(BASE, "FULLTEXT_DOWNLOAD_LOG.json")) else []
    if retry:
        targets = [l["doi"] for l in log if l["status"] == "retry_fail"]
    else:
        targets = [d["doi"] for d in docs
                   if d.get("domain") == "Thesis_References"
                   and not d.get("files", {}).get("full_text_pdf")]
    done = {l["doi"] for l in log if "downloaded" in l["status"]}
    got = fail = 0
    for doi in targets:
        if doi in done:
            continue
        try:
            data, res = try_get(doi)
        except Exception as e:
            fail += 1
            log.append({"doi": doi, "status": "retry_fail", "note": f"exception:{e}"[:60]})
            continue
        if data:
            fn = f"REF_{doi.replace('/', '_').replace('.', '_')}.pdf"
            open(os.path.join(DEST, fn), "wb").write(data)
            for d in docs:
                if d["doi"] == doi:
                    d["files"]["full_text_pdf"] = "SOURCE_PDFS/" + fn
                    d["verification_status"] = d.get("verification_status", "") + "; FULLTEXT_DOWNLOADED"
            got += 1
            log.append({"doi": doi, "status": "downloaded"})
        else:
            fail += 1
            log.append({"doi": doi, "status": "retry_fail", "note": res})
        time.sleep(0.3)
    # backup + save
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    open(os.path.join(BASE, "backups", f"CAT_before_download_{ts}.json"), "w").write(
        open(CAT).read()) if os.path.exists(os.path.join(BASE, "backups")) else None
    cat["metadata"]["last_updated"] = datetime.now().isoformat()
    json.dump(cat, open(CAT, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    json.dump(log, open(os.path.join(BASE, "FULLTEXT_DOWNLOAD_LOG.json"), "w", encoding="utf-8"),
              indent=2, ensure_ascii=False)
    print(f"Targets: {len(targets)} | downloaded this run: {got} | failed: {fail}")


if __name__ == "__main__":
    main()
