# Catalog JSON Field-Safety — worked examples

All from a 435-doc nursing-stress RAG. These bugs cost real turns; the safe pattern is
always `.get()` + coercion. Match tags case-insensitively.

## 1. Case-sensitive tag filter → false "0 results"
```python
# WRONG (returns 0 even though 54 Malaysian studies exist):
my = [d for d in docs if 'malaysia' in (d.get('tags') or [])]
# RIGHT:
my = [d for d in docs if 'malaysia' in [t.lower() for t in (d.get('tags') or [])]]
# or match on domain='Malaysian_Nursing_Studies' when that domain is used.
```

## 2. Missing key → KeyError
```python
# WRONG: 'country' absent on international/legacy entries
if d['country'] == 'MY': ...
# RIGHT:
if d.get('country') == 'MY': ...
```

## 3. year as string → TypeError on negation
```python
# WRONG: year stored as "2022" (str) in some entries
hits.sort(key=lambda x: -x.get('year'))
# RIGHT:
def yint(d):
    try: return int(d.get('year') or 0)
    except: return 0
hits.sort(key=lambda x: -yint(x))
```

## 4. tags may be None
```python
tags = set(d.get('tags') or [])          # never d.get('tags') alone
tags.add('workload'); d['tags'] = sorted(tags)
```

## 5. Duplicate local IDs across domains
```python
if (d.get('doi') or '').startswith('local:user'):
    d['id'] = d.get('id', d['doi']) + "_" + str(d.get('domain',''))
    d['doi'] = d['doi'] + "_" + str(d.get('domain',''))
```

## 6. Integrity check after every bulk op
```python
from collections import Counter
dois = [d.get('doi','').lower() for d in docs if d.get('doi')]
dup = [k for k,v in Counter(dois).items() if v > 1]   # must be []
# dangling file check:
for d in docs:
    p = (d.get('files',{}).get('full_text_pdf')
          or d.get('files',{}).get('full_text_html'))
    if p and not os.path.exists(p): flag(d)
```

## 7. MSYS/git-bash path mangling (Python)
`/c/Users/...` passed to python3 → becomes `C:\c\Users\...` (double prefix), breaking
paper-fetch and any `--out`. Pass NATIVE Windows paths: `C:\Users\Milos\...`. Feed DOIs
via stdin (`cat file | python3 <native-script> --batch - --out <native>`), never
`--batch <msys-path>`.
