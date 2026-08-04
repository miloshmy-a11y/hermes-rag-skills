import os, json, re, urllib.request, sys, datetime

# Batch-process a thesis/paper reference list against the catalog, one entry at a time,
# adding Crossref-verified missing studies. Designed for context-limited sessions:
# process N entries per call, persist progress, continue with `python ref_check_batch.py <start>`.
# Prereqs:
#   - UNIVERSAL_CATALOG.json  (catalog with 'documents' list)
#   - THESIS_REFERENCE_LIST.json  (list of raw bib strings; each must contain a 10.x DOI)
# Run:  python ref_check_batch.py 0   (then 8, 16, 24 ... until all 73 checked)
BASE = os.path.dirname(os.path.abspath(__file__))
if BASE not in (r"C:\Users\Milos\AppData\Local\hermes\cache\web\universal_rag",):
    # allow override via env if run from skill dir
    BASE = os.environ.get("RAG_BASE", BASE)
BATCH = 8

def get_doi(s):
    m = re.search(r'(10\.\d{4,}/[^\s<>"\'\}\)]+)', s)
    return m.group(1).rstrip('.,;:') if m else None

def crossref(doi):
    try:
        url = f"https://api.crossref.org/works/{doi}"
        req = urllib.request.Request(url, headers={'User-Agent': 'refcheck/1.0 (mailto:x@example.com)'})
        with urllib.request.urlopen(req, timeout=20) as r:
            if r.status == 200:
                m = json.loads(r.read()).get('message', {})
                return {'ok': True, 'title': (m.get('title') or [''])[0],
                        'authors': [' '.join(p for p in [a.get('given', ''), a.get('family', '')] if p).strip()
                                    for a in m.get('author', [])],
                        'year': str(m.get('published', {}).get('date-parts', [['']])[0][0]),
                        'journal': ' '.join(m.get('container-title', ['']))}
    except Exception as e:
        return {'ok': False, 'err': str(e)[:80]}
    return {'ok': False, 'err': 'noresp'}

cat = json.load(open(os.path.join(BASE, "UNIVERSAL_CATALOG.json"), encoding='utf-8'))
docs = cat['documents']
entries = json.load(open(os.path.join(BASE, "THESIS_REFERENCE_LIST.json"), encoding='utf-8'))

def in_catalog(doi):
    for d in docs:
        if d.get('doi', '').lower() == doi.lower():
            return d
    return None

start_idx = int(sys.argv[1]) if len(sys.argv) > 1 else 0
batch = entries[start_idx:start_idx + BATCH]
added = 0
results = []
for i, e in enumerate(batch):
    di = start_idx + i
    doi = get_doi(e)
    cr = crossref(doi) if doi else {'ok': False, 'err': 'no_doi'}
    cat_rec = in_catalog(doi) if doi else None
    status = "OK"
    notes = []
    if not cr.get('ok'):
        status = "CROSSREF_FAIL"; notes.append(cr.get('err'))
    elif cat_rec is None:
        status = "NOT_IN_CATALOG"; notes.append("cited but absent from catalog")
    else:
        ty = re.search(r'\((\d{4})\)', e)
        if ty and cr.get('year') and ty.group(1) != cr['year']:
            notes.append(f"year mismatch thesis({ty.group(1)}) vs crossref({cr['year']})")
    if status == "NOT_IN_CATALOG" and cr.get('ok'):
        docs.append({'title': cr['title'], 'authors': cr['authors'], 'year': cr['year'], 'doi': doi,
                     'journal': cr['journal'], 'abstract': '',
                     'official_keywords': [], 'inferred_tags': [],
                     'doc_type': 'study', 'domain': 'Thesis_References',
                     'verification_status': 'VERIFIED (Crossref) — cited in thesis',
                     'source_folder': 'THESIS_REFERENCE_LIST', 'cited_in_thesis': True,
                     'files': {'base_path': BASE, 'original_source': '', 'full_text_pdf': '', 'extracted_text': ''},
                     'added_date': datetime.datetime.now().isoformat()})
        added += 1
    results.append({'idx': di + 1, 'doi': doi, 'status': status, 'notes': notes})
    print(f"[{di+1}] {status} {doi} {'; '.join(notes)}")

prog = os.path.join(BASE, "REF_CHECK_PROGRESS.json")
allres = json.load(open(prog, encoding='utf-8')) if os.path.exists(prog) else []
seen = {r['idx'] for r in allres}
allres.extend(r for r in results if r['idx'] not in seen)
json.dump(allres, open(prog, 'w', encoding='utf-8'), indent=2, ensure_ascii=False)
if added:
    cat['documents'] = docs
    cat['metadata']['total_documents'] = len(docs)
    json.dump(cat, open(os.path.join(BASE, "UNIVERSAL_CATALOG.json"), 'w', encoding='utf-8'), indent=2, ensure_ascii=False)
print(f"--- batch done. Added {added}. Progress {len(allres)}/{len(entries)}. Next: python ref_check_batch.py {start_idx+BATCH} ---")
