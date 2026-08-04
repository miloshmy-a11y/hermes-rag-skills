"""OpenAlex API helper — free, no key, no rate limit, CC0 data.

Public surface:
  oa_search(query, filters="", per_page=10, select=None) -> dict (OpenAlex response)
  oa_by_doi(doi, select=None) -> dict (first work matching the DOI)
  oa_bulk_dois(dois, select="cited_by_count,open_access") -> list[dict]
  oa_citations(id_or_doi, per_page=10) -> list[dict]   (forward citations)
  oa_concepts(query, per_page=5) -> list[str]

Safety: read-only GET. Polite-pool email from OPENALEX_MAIL env (recommended).
Only returns OA PDF URLs (open_access.oa_url); never fetches paywalled content.
"""
import os, time, json, urllib.parse, urllib.request

BASE = "https://api.openalex.org"
_MAIL = os.environ.get("OPENALEX_MAIL", "<user>@example.com").strip()
_last = 0
_MIN_GAP = 0.1  # OpenAlex is generous; tiny gap avoids bursts

def _get(endpoint, params):
    global _last
    params = dict(params)
    params.setdefault("mailto", _MAIL)
    elapsed = time.time() - _last
    if elapsed < _MIN_GAP:
        time.sleep(_MIN_GAP - elapsed)
    _last = time.time()
    url = BASE + endpoint + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": f"mailto:{_MAIL}"})
    with urllib.request.urlopen(req, timeout=40) as r:
        return json.loads(r.read())

def oa_search(query, filters="", per_page=10, select=None, page=1):
    params = {"search": query, "per_page": per_page, "page": page}
    if filters:
        params["filter"] = filters
    if select:
        params["select"] = select
    return _get("/works", params)

def oa_by_doi(doi, select=None):
    params = {"filter": f"doi:{doi}"}
    if select:
        params["select"] = select
    r = _get("/works", params)
    return (r.get("results") or [{}])[0]

def oa_bulk_dois(dois, select="cited_by_count,open_access"):
    # OpenAlex supports filter=doi:10.x,10.y (up to 50 per request via OR syntax)
    out = {}
    for i in range(0, len(dois), 45):
        chunk = dois[i:i+45]
        filt = "doi:" + "|".join(chunk)
        r = _get("/works", {"filter": filt, "select": "id,doi," + select, "per_page": 50})
        for w in r.get("results", []):
            d = (w.get("doi") or "").lower()
            if d:
                out[d] = w
    return out

def oa_citations(id_or_doi, per_page=10):
    # id_or_doi: OpenAlex id (Wxxxx) or DOI (10.x/...)
    ident = id_or_doi if id_or_doi.startswith("W") else f"doi:{id_or_doi}"
    r = _get("/works", {"filter": f"cites:{ident}", "per_page": per_page,
                        "select": "id,doi,title,publication_year,cited_by_count,open_access"})
    return r.get("results", [])

def oa_concepts(query, per_page=5):
    r = _get("/concepts", {"search": query, "per_page": per_page, "select": "id,display_name,works_count"})
    return [c["display_name"] for c in r.get("results", [])]

if __name__ == "__main__":
    import sys
    q = " ".join(sys.argv[1:]) or "nursing stress Malaysia"
    res = oa_search(q, filters="from_publication_date:2018-01-01", per_page=5)
    print(f"count~{res.get('meta',{}).get('count')}")
    for w in res.get("results", []):
        oa_url = (w.get("open_access") or {}).get("oa_url", "")
        print(f"  {w.get('publication_year')} | cited={w.get('cited_by_count')} | {w.get('title','')[:55]}")
        if oa_url:
            print(f"      PDF: {oa_url[:80]}")
