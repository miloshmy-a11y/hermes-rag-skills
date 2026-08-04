"""
crossref_backfill.py — Non-destructive metadata + BibTeX backfill for a RAG catalog.

Use when catalog study entries are missing venue / apa_citation / abstract / authors /
year / DOI and you want to fill them from Crossref (authoritative) WITHOUT overwriting
the user's manually-verified fields.

KEY RULE (verified-academic-research preference): the user's existing title/authors/year
are AUTHORITATIVE. Only fill EMPTY fields. Guard every write.

Usage (run via execute_code or terminal python3):
    python3 crossref_backfill.py <CATALOG_JSON> [--min-year 2020] [--domains Thesis_References Malaysian_Nursing_Studies]

Rewrites only the catalog JSON in place after backfill. Idempotent: re-running fills
only still-empty fields.
"""
import sys, os, json, re, time, urllib.request, urllib.parse

def norm_doi(d):
    m = re.search(r'10\.\d{4,9}/[^\s]+', d.get('doi') or '')
    return m.group(0) if m else None

def yi(d):
    try: return int(d.get('year'))
    except: return 0

def cr(doi):
    try:
        req = urllib.request.Request(
            f"https://api.crossref.org/works/{urllib.parse.quote(doi)}",
            headers={"User-Agent": "HermesRAG/1.0 (mailto:<user>@example.com)"})
        return json.loads(urllib.request.urlopen(req, timeout=15).read())['message']
    except Exception:
        return None

def apa(m):
    auths = m.get('author', [])
    names = []
    for a in auths[:20]:
        g = a.get('given', ''); f = a.get('family', '')
        if f: names.append(f if not g else f"{g} {f}")
    if len(names) > 20: names = names[:20] + ["et al."]
    auth = ", ".join(names) if names else "Unknown"
    yr = (m.get('issued', {}).get('date-parts', [[None]])[0][0]
          or m.get('published', {}).get('date-parts', [[None]])[0][0] or 'n.d.')
    tl = m.get('title') or ['']
    ti = tl[0] if tl else ''
    ct = m.get('container-title') or ['']
    container = ct[0] if ct else ''
    return f"{auth} ({yr}). {ti}. {container}. https://doi.org/{m.get('DOI','')}"

def bibtex_from_cr(m):
    """Authoritative BibTeX via DOI content negotiation (better than generating)."""
    try:
        req = urllib.request.Request(
            f"https://doi.org/{m.get('DOI','')}",
            headers={"Accept": "application/x-bibtex"})
        return urllib.request.urlopen(req, timeout=15).read().decode('utf-8', 'replace')
    except Exception:
        return None

def main():
    if len(sys.argv) < 2:
        print("usage: crossref_backfill.py <CATALOG.json> [--min-year N] [--domains a b c]")
        sys.exit(1)
    cat_path = sys.argv[1]
    args = sys.argv[2:]
    min_year = 0
    domains = None
    if '--min-year' in args:
        i = args.index('--min-year'); min_year = int(args[i+1])
    if '--domains' in args:
        i = args.index('--domains'); domains = args[i+1:]
    cat = json.load(open(cat_path, encoding='utf-8'))
    docs = cat['documents']
    studies = [d for d in docs if d.get('doc_type') == 'study']
    if domains:
        studies = [d for d in studies if d.get('domain') in domains]
    if min_year:
        studies = [d for d in studies if yi(d) >= min_year]
    targets = [d for d in studies if norm_doi(d)]
    print(f"Backfilling {len(targets)} studies (min_year={min_year}, domains={domains})")
    stats = {'venue':0,'apa':0,'abs':0,'authors':0,'year':0}
    seen = list(dict.fromkeys(norm_doi(d) for d in targets))  # unique DOIs
    for i, doi in enumerate(seen, 1):
        m = cr(doi)
        if not m: continue
        bib = bibtex_from_cr(m)
        for d in targets:
            if norm_doi(d) != doi: continue
            if not d.get('venue'):
                ct = m.get('container-title') or []
                if ct: d['venue'] = ct[0]; stats['venue'] += 1
            if not d.get('apa_citation'):
                d['apa_citation'] = apa(m); stats['apa'] += 1
            if not (d.get('authors') and [a for a in d['authors'] if a]):
                fa = [a.get('family','') for a in m.get('author',[]) if a.get('family')]
                if fa: d['authors'] = fa; stats['authors'] += 1
            if not yi(d):
                yr = m.get('issued', {}).get('date-parts', [[None]])[0][0]
                if yr: d['year'] = yr; stats['year'] += 1
            if not d.get('abstract'):
                ab = m.get('abstract')
                if ab and len(ab) > 40:
                    d['abstract'] = re.sub(r'<[^>]+>', '', ab); stats['abs'] += 1
            if bib and not d.get('bibtex'):
                d['bibtex'] = bib
        if i % 40 == 0:
            json.dump(cat, open(cat_path, 'w', encoding='utf-8'), indent=2, ensure_ascii=False)
            print(f"  {i}/{len(seen)} venue={stats['venue']} apa={stats['apa']} abs={stats['abs']}", flush=True)
        time.sleep(0.1)
    json.dump(cat, open(cat_path, 'w', encoding='utf-8'), indent=2, ensure_ascii=False)
    print(f"DONE. Filled -> venue:{stats['venue']} apa:{stats['apa']} abs:{stats['abs']} authors:{stats['authors']} year:{stats['year']}")

if __name__ == '__main__':
    main()
