"""
Staged, progressive catalog search — follows the old universal_rag.py search philosophy
(targeted -> expand -> full-text scan -> web fallback) but with precise population+geo+topic
gating so it does NOT over-match (the bug that returned 170+ hits for "Malaysian nurse stress").

Design (per user spec):
  Stage 1  Targeted: match on INDEX fields (title, abstract, tags, official_keywords,
           paper_category). Population must be nurses, geography Malaysia, topic stress.
  Stage 2  If < min_results (default 3): expand query synonyms, re-search index.
  Stage 3  If still < min_results: scan full-text files (slower, higher recall).
  Stage 4  If still none: run web search, return candidates flagged
           `needs_indexing=True` so the user can decide to add them.
  Final    Rank by relevance (title + abstract + tags + keywords) then recency.
           For a TARGETED query, return top `targeted_cap` (default 15) — these are
           the ones safe to open full-text for summarisation. For a BROAD query
           (many matches), return all but set `needs_narrowing=True` and do NOT
           auto-open every full text.

KEY POINTS from user:
  - Title alone is NOT a good starting point; keywords saved in the index matter most,
    AND the abstract must be weighted too (e.g. "Why so stressed?" has a casual title
    but a core Malaysian-nurse-stress abstract — it must rank high).
  - For studies found via abstract/full-text that were MISSED by index keywords, the
    missing relevant keywords are ADDED back to that record's tags (non-destructive).
  - Every record carries `paper_category` (study/book/thesis/essay/instrument/...).
  - Students are kept but surfaced under a less-relevant tier when presenting.

Usage:
    from precise_search import staged_search
    out = staged_search(docs, query="stress among nurses in Malaysia since 2020")
    # population/geo are OPTIONAL and QUERY-DERIVED (see below). For a general topic:
    #   out = staged_search(docs, query="diabetes policy")  # no population/geo gate
    # out = dict with keys: core_results, student_results, reference_results,
    #                        ref_intent, stage_reached, terms_used, web_candidates,
    #                        keywords_added_count, breadth, needs_narrowing,
    #                        total_core_available, suggested_actions, judgment
"""
import os
import re

# --- OPTIONAL domain-tuning hints (NOT enforced unless the query matches them) ---
# These are only used to EXPAND or WEIGHT a query term when that term actually appears
# in the user's query. They do NOT gate or bias a general query. The RAG is topic-agnostic:
# a query about 'diabetes', 'wound care', or 'climate policy' is searched as-is.
EXPANSIONS = {
    'stress': ['job stress', 'occupational stress', 'work-related stress', 'psychological stress', 'nursing stress', 'work stress'],
    'burnout': ['emotional exhaustion', 'depersonalization', 'compassion fatigue', 'professional burnout', 'occupational burnout'],
    'job satisfaction': ['turnover', 'intention to leave', 'retention', 'job morale', 'job dissatisfaction'],
    'workload': ['work load', 'heavy workload', 'understaffing', 'staffing shortage', 'overwork', 'work demands'],
    'mental health': ['anxiety', 'depression', 'psychological wellbeing', 'wellbeing'],
    'wellbeing': ['well-being', 'quality of life', 'psychological wellbeing'],
    'nurse': ['nurses', 'nursing', 'registered nurses', 'nursing staff'],
    'malaysia': ['malaysian', 'kuala lumpur', 'penang', 'malaysian nursing'],
    'turnover': ['intention to leave', 'retention', 'attrition', 'staff turnover'],
    'workplace violence': ['bullying', 'harassment', 'vertical violence', 'lateral violence'],
    'resilience': ['coping', 'hardiness'],
    'moral distress': ['ethical distress', 'moral injury'],
}

# Optional ranking boosts — only applied to terms that appear in the query.
TOPIC_W = {'stress': 3, 'burnout': 3, 'workload': 2.5, 'job satisfaction': 2, 'wellbeing': 2,
           'mental health': 2, 'turnover': 1.5, 'compassion fatigue': 2, 'moral distress': 2,
           'workplace violence': 2, 'occupational stress': 3}

# Document types that are pure noise / non-content and excluded from ALL search
# (web landing pages, course modules, learning kits). NOTE: books / ebooks /
# instruments / guidelines ARE searchable — they are tiered as lower-relevance
# "reference" results for normal study queries, but surfaced when the user
# explicitly asks for an ebook / book / instrument / guideline.
EXCLUDE_DTYPES = {'web', 'module', 'course', 'learning kit'}

# Reference document types: searchable, but tiered as lower-relevance "reference"
# results for normal study queries. When the user explicitly asks for an ebook /
# book / instrument / guideline, these become the PRIMARY results.
REF_DTYPES = {'book', 'ebook', 'book_chapter', 'instrument', 'tool',
              'guideline', 'org_doc', 'gov_doc'}

# Population / geography are OPTIONAL and QUERY-DERIVED. The RAG does NOT assume
# nurses or Malaysia. DEFAULT_POPULATION / DEFAULT_GEO let a deployer bias their
# personal instance (e.g. a Malaysian-nurse researcher can set these); the public
# skill ships with None (fully general). Set to None for topic-agnostic behaviour.
DEFAULT_POPULATION = None   # e.g. 'nurse' for a nurse-focused personal instance
DEFAULT_GEO = None          # e.g. 'malaysia' for a Malaysia-focused personal instance

# Detection maps: if the query mentions one of these, apply that population/geo filter.
POP_DETECT = {'nurse': 'nurse', 'nurses': 'nurse', 'nursing': 'nurse',
             'doctor': 'doctor', 'physician': 'doctor', 'physicians': 'doctor',
             'teacher': 'teacher', 'teachers': 'teacher',
             'student': 'student', 'students': 'student',
             'patient': 'patient', 'patients': 'patient'}
GEO_DETECT = {'malaysia': 'malaysia', 'malaysian': 'malaysia',
             'usa': 'usa', 'united states': 'usa', 'america': 'usa',
             'uk': 'uk', 'united kingdom': 'uk', 'britain': 'uk',
             'india': 'india', 'indian': 'india',
             'indonesia': 'indonesia', 'indonesian': 'indonesia'}

# Instrument detection — QUERY-DERIVED, topic-agnostic. An instrument is only applied
# when the user's QUERY names it (e.g. "NSS", "ENSS", "MBI"). These are matched against
# the per-study `measures` field (populated from full-text scanning). No instrument is
# ever forced; this simply boosts/filters when the query is instrument-specific.
INSTRUMENT_DETECT = {
    'nursing stress scale': ['nursing stress scale', 'nss'],
    'expanded nursing stress scale': ['expanded nursing stress scale', 'enss'],
    'brief nursing stress scale': ['brief nursing stress scale'],
    'maslach burnout inventory': ['maslach burnout inventory', 'mbi', 'burnout inventory'],
    'copenhagen burnout inventory': ['copenhagen burnout inventory', 'cbi'],
    'oldenburg burnout inventory': ['oldenburg burnout inventory', 'olbi'],
    'professional quality of life': ['professional quality of life', 'proqol'],
    'connor-davidson resilience': ['connor davidson resilience', 'cd-risc'],
    'resilience scale': ['resilience scale', 'wagnild'],
    'perceived stress scale': ['perceived stress scale', 'pss'],
    'hospital anxiety depression': ['hospital anxiety and depression', 'hads'],
    'patient safety culture': ['patient safety culture', 'hsopsc', 'safety culture'],
    'safety attitude questionnaire': ['safety attitude questionnaire', 'saq'],
    'job satisfaction scale': ['minnesota satisfaction', 'mmss', 'job satisfaction scale'],
    'turnover intention': ['turnover intention', 'intention to leave'],
    'workload nasa-tlx': ['nasa-tlx', 'nasa tlx', 'task load index'],
    'occupational stress': ['occupational stress inventory', 'occupational stress scale'],
    'general health questionnaire': ['general health questionnaire', 'ghq'],
    'depression anxiety stress': ['depression anxiety stress scales', 'dass'],
    'state-trait anxiety': ['state-trait anxiety', 'stai'],
    'practice environment': ['practice environment scale', 'nursing work index'],
    'leadership mlq': ['multifactor leadership', 'mlq'],
    'mindfulness': ['mindful attention', 'five facet mindfulness'],
    'coping brief cope': ['brief cope', 'coping orientation'],
    'compassion fatigue': ['compassion fatigue'],
    'secondary traumatic stress': ['secondary traumatic stress'],
    'quality of life whoqol': ['world health organization quality of life', 'whoqol'],
    'anxiety gad-7': ['generalized anxiety disorder 7', 'gad-7'],
    'insomnia isi': ['insomnia severity', 'isi'],
    'work engagement': ['uthrecht work engagement', 'uwes', 'work engagement scale'],
}


min_year_for_rank = 2020  # updated per call

STUDENT_TITLE = re.compile(r'\b(students?|nursing students?|undergraduate)\b', re.I)


def _topic_score(low_text, topic_terms):
    """Weighted topic match — generic variant-aware (no fixed topic list).
    e.g. query term 'stress' also matches 'stressed'/'stressors'/'stressful'."""
    score = 0
    hit = []
    variants = {}  # term -> set of substring forms
    for term in topic_terms:
        forms = {term, term + 's', term.rstrip('s')}
        for part in term.split():
            forms.add(part); forms.add(part + 's'); forms.add(part.rstrip('s'))
        variants[term] = forms
    for term, w in topic_terms.items():
        matched = False
        for v in variants[term]:
            if v and v in low_text:
                matched = True
                break
        if matched:
            score += w
            hit.append(term)
    return score, hit


def _title_has_topic(title, topic_terms):
    """Does the title contain a topic-term (generic variant-aware)?
    Derives variants from the QUERY's own topic_terms — never a fixed topic list,
    so this works for ANY domain (stress, turnover, wound care, diabetes, ...)."""
    t = title.lower()
    # build variant set generically: each term + its parts + plural/stem forms
    variants = set()
    for term in topic_terms:
        variants.add(term)
        variants.add(term + 's')
        variants.add(term.rstrip('s'))
        for part in term.split():
            variants.add(part)
            variants.add(part + 's')
            variants.add(part.rstrip('s'))
    for v in variants:
        if v and v in t:
            return True
    return False


def _is_student_study(d):
    title = str(d.get('title', ''))
    return bool(STUDENT_TITLE.search(title)) or 'student' in str(d.get('population', '')).lower()


def _index_text(d):
    """The index fields an agent should search — LLM-readable, not script-spam:
    title + official_keywords (author terms) + brief_abstract (LLM-compressed summary)
    + key_findings (per-study conclusion, indexed for finding-level queries)
    + measures (instruments used, e.g. ENSS) + abstract, so both keyword and
    finding-phrased queries resolve."""
    return ' '.join([
        str(d.get('title', '')),
        ' '.join(d.get('official_keywords', []) or []),
        str(d.get('brief_abstract', '') or ''),
        str(d.get('key_findings', '') or ''),
        ' '.join(d.get('measures', []) or []),
        str(d.get('abstract', '') or ''),
    ]).lower()



def _term_df(term, docs):
    """Document-frequency of a term across the catalog index text (for anchor selection)."""
    t = term.lower()
    n = 0
    for d in docs:
        if t in _index_text(d).lower():
            n += 1
    return n


def _passes_gate(d, population, geo, topic_terms, min_year, anchor=None):
    """Population + geography + topic gating — GENERAL / topic-agnostic.
    population and geo are OPTIONAL: they are only enforced when the caller
    (staged_search) detected them in the QUERY. If population is None / geo is
    None, that dimension is NOT gated — so a query like 'diabetes policy' or
    'wound care' is NOT forced through a nurse+Malaysia filter.
    Topic must appear in title OR abstract OR brief_abstract OR measures (weighted).
    A casual title with a core abstract is valid and ranks high.
    `anchor` (optional): when the query has several topic terms, the RAREST one is
    required to be present (prevents a common co-occurring term like 'healthcare'
    from letting through studies that don't address the SPECIFIC topic, e.g.
    'discrimination'). Topic-agnostic: the caller computes rarity from the catalog.
    Students pass the gate but are flagged for the less-relevant tier."""
    y = d.get('year')
    if not (str(y).isdigit() and int(y) >= min_year):
        return False, None
    dt = str(d.get('doc_type', '')).lower()
    if dt in EXCLUDE_DTYPES:
        return False, None
    title = str(d.get('title', ''))
    ab = str(d.get('abstract', '') or '')
    ba = str(d.get('brief_abstract', '') or '')
    ms = ' '.join(d.get('measures', []) or [])
    ta_low = (title + ' ' + ab + ' ' + ba + ' ' + ms).lower()
    # OPTIONAL population gate (only if a population was detected in the query).
    # Stem-aware: 'nurse' matches nurse/nurses/nursing; 'doctor' matches doctor/doctors.
    if population:
        if not re.search(r'\b' + re.escape(population) + r'[a-z]*\b', ta_low, re.I):
            return False, None
    # OPTIONAL geography gate (only if a geo was detected in the query).
    # Stem-aware: 'malaysia' matches malaysia/malaysian; 'usa' matches usa.
    if geo:
        geo_ok = bool(re.search(r'\b' + re.escape(geo) + r'[a-z]*\b', ta_low, re.I)) \
                 or geo.lower() in str(d.get('country', '')).lower() \
                 or geo.lower() in str(d.get('domain', '')).lower()
        if not geo_ok:
            return False, None
    # ANCHOR: if a specific (rarest) topic term was selected by the caller, it MUST be
    # present in the indexed text. This stops common co-occurring terms (e.g. 'healthcare')
    # from admitting studies that don't actually address the SPECIFIC query topic.
    if anchor:
        if anchor.lower() not in _index_text(d).lower():
            return False, None
    # topic: in title OR abstract OR brief_abstract OR measures (any weight)
    ts, terms = _topic_score(ta_low, topic_terms)
    if ts == 0:
        return False, None
    is_student = bool(STUDENT_TITLE.search(title)) or 'student' in str(d.get('population', '')).lower()
    return True, (terms, is_student)


def _rank(d, terms, nurse_title, my_title, year, topic_in_title, nurse_conf, my_conf):
    # population/geography confirmed ANYWHERE (title or abstract) is what matters;
    # a title mention gives a small extra precision bonus but does NOT exclude
    # studies whose relevant data is only in the abstract (e.g. "Why so stressed?").
    pop_prec = 2.0 if nurse_conf else 1.0
    geo_prec = 2.0 if my_conf else 1.0
    title_bonus = (0.3 if nurse_title else 0) + (0.3 if my_title else 0)
    topic_w = min(sum(TOPIC_W.get(t, 1) for t in terms), 6) / 2
    topic_title_bonus = 1.0 if topic_in_title else 0.0
    recency = (int(year) - min_year_for_rank) * 0.1
    key_boost = 2.5 if d.get('key_study') else 0.0  # user-flagged seminal study
    return round(pop_prec + geo_prec + title_bonus + topic_w + topic_title_bonus + recency + key_boost, 2)


def _read_fulltext(d):
    f = d.get('files') or {}
    for k, v in f.items():
        if isinstance(v, str) and not v.startswith('http') and v.lower().endswith(('.txt', '.md', '.html')):
            if os.path.exists(v):
                try:
                    return open(v, encoding='utf-8', errors='ignore').read()
                except Exception:
                    pass
    et = f.get('extracted_text')
    if et and isinstance(et, str) and et.lower().endswith('.txt') and os.path.exists(et):
        try:
            return open(et, encoding='utf-8', errors='ignore').read()
        except Exception:
            return ''
    return ''


def _backfill_keywords(d, terms_low, fulltext_low):
    """Add index keywords that the full-text revealed but the record lacked.
    Non-destructive: only appends, never overwrites."""
    d.setdefault('tags', [])
    added = []
    for t in terms_low:
        if t in fulltext_low and t not in [x.lower() for x in d['tags']]:
            d['tags'].append(t)
            added.append(t)
    return added


def _search_index(docs, terms_low, population, geo, topic_terms, min_year, fulltext=False, instruments=None, anchor=None):
    global min_year_for_rank
    min_year_for_rank = min_year
    instruments = instruments or []
    out = []
    for d in docs:
        ok, matched = _passes_gate(d, population, geo, topic_terms, min_year, anchor=anchor)
        if not ok:
            continue
        terms, is_student = matched
        title = str(d.get('title', ''))
        ab = str(d.get('abstract', ''))
        idx = _index_text(d)
        found_via = 'index'
        if not any(t in idx for t in terms_low):
            if not fulltext:
                continue
            ft = _read_fulltext(d)
            if not any(t in ft.lower() for t in terms_low):
                continue
            _backfill_keywords(d, terms_low, ft.lower())
            found_via = 'fulltext'
        # Population/geo confidence — derived from the QUERY's population/geo (or
        # generic detection), not a hardcoded nurse/Malaysia regex.
        pop_re = re.compile(r'\b' + re.escape(population) + r'[a-z]*\b', re.I) if population else None
        geo_re = re.compile(r'\b' + re.escape(geo) + r'[a-z]*\b', re.I) if geo else None
        nurse_title = bool(pop_re.search(title)) if pop_re else False
        my_title = bool(geo_re.search(title)) if geo_re else False
        nurse_abs = bool(pop_re.search(ab)) if (pop_re and ab) else False
        my_abs = bool(geo_re.search(ab)) if (geo_re and ab) else False
        nurse_conf = nurse_title or nurse_abs
        my_conf = my_title or my_abs or str(d.get('country', '')).lower() == 'my' or 'malaysia' in str(d.get('domain', '')).lower()
        topic_in_title = _title_has_topic(title, topic_terms)
        score = _rank(d, terms, nurse_title, my_title, d.get('year', min_year), topic_in_title, nurse_conf, my_conf)
        # Instrument boost: if the query named an instrument and this study's `measures`
        # contains it, strongly boost. This makes instrument queries (e.g. "NSS") return
        # instrument users instead of generic text matches.
        inst_boost = 0.0
        inst_hit = False
        if instruments:
            measures = [m.lower() for m in (d.get('measures') or [])]
            for inst in instruments:
                if any(inst in m for m in measures):
                    inst_boost += 5.0
                    inst_hit = True
                    break
        score += inst_boost
        out.append({
            'doc': d, 'score': score, 'matched_terms': terms,
            'nurse_in_title': nurse_title, 'malaysia_in_title': my_title,
            'is_student': is_student, 'found_via': found_via,
            'instrument_hit': inst_hit,
        })
    out.sort(key=lambda x: -x['score'])
    return out


def staged_search(docs, query="stress among nurses in Malaysia",
                  population=None, geo=None,
                  topic_terms=None, min_year=2000, min_results=3,
                  targeted_cap=15, broad_threshold=25):
    """Progressive staged search — GENERAL / topic-agnostic.

    Population and geography are OPTIONAL. By default they are derived from the
    query (POP_DETECT / GEO_DETECT). If the query says nothing about a population
    or place, NO population/geo gate is applied — a query like 'diabetes policy'
    or 'wound care' is searched across the whole catalog. A deployer can bias
    their personal instance via DEFAULT_POPULATION / DEFAULT_GEO (the public skill
    ships with None).

    Targeted query (final core <= broad_threshold): return TOP `targeted_cap`
    studies, ranked by relevance then recency — safe to open full text.
    Broad query (many matches): return all but set `needs_narrowing=True`;
    caller should NOT open every full text, just report and offer to narrow.
    """
    # Derive population/geo from the query if not explicitly passed.
    if population is None:
        population = DEFAULT_POPULATION
    if geo is None:
        geo = DEFAULT_GEO
    q_low = query.lower()
    # Derive instrument(s) from the query (topic-agnostic: only applied if the query
    # names an instrument). Used to boost/filter studies whose `measures` contain it.
    instruments = []
    for canon, variants in INSTRUMENT_DETECT.items():
        if any(v in q_low for v in variants):
            instruments.append(canon)
    if population is None:
        for k, v in POP_DETECT.items():
            if k in q_low:
                population = v
                break
    if geo is None:
        for k, v in GEO_DETECT.items():
            if k in q_low:
                geo = v
                break

    if topic_terms is None:
        topic_terms = {}   # derive purely from the query below (no stress bias)

    # Extract seed topic terms from the QUERY (topic-agnostic):
    # 1) prefer terms present in the caller's topic_terms dict
    seed = [t for t in topic_terms if t in q_low]
    # 2) if the query names a topic NOT in topic_terms (e.g. "wound care"),
    #    derive topic terms from the query words themselves, dropping population/geo
    #    stopwords. This avoids the old bug of falling back to stress/burnout.
    if not seed:
        STOP = {'nurse','nurses','nursing','among','in','of','the','a','an','and','or','for',
                'malaysia','malaysian','since','from','to','with','on','at','by','study','studies',
                'population','care','health','patient',
                'quality','safety','practice','staff','work','role','impact','level','scale'}
        qt = [w for w in re.findall(r"[a-z][a-z\-]+", q_low) if w not in STOP and len(w) >= 3]
        # build a topic_terms dict from query words (weight by length as a proxy for specificity)
        topic_terms = {w: 2.0 for w in qt}
        seed = qt
    terms_low = list(seed)

    # ANCHOR: pick the RAREST seed term (by document-frequency) as the required topic
    # anchor. Prevents a common co-occurring term (e.g. 'healthcare' in a nursing
    # catalog) from admitting studies that don't address the SPECIFIC topic
    # (e.g. 'discrimination'). Topic-agnostic: computed from the catalog, not hardcoded.
    anchor = None
    if len(terms_low) > 1:
        anchor = min(terms_low, key=lambda t: _term_df(t, docs))

    # Stage 1: targeted index search
    r1 = _search_index(docs, terms_low, population, geo, topic_terms, min_year, instruments=instruments, anchor=anchor)
    stage = 1

    # Stage 2: expand synonyms if thin
    if len(r1) < min_results:
        stage = 2
        extra = []
        for s in seed:
            for exp in EXPANSIONS.get(s, []):
                if exp not in terms_low and len(exp.split()) <= 2:
                    extra.append(exp)
        terms_low = terms_low + extra[:6]
        r2 = _search_index(docs, terms_low, population, geo, topic_terms, min_year, instruments=instruments, anchor=anchor)
        seen = {x['doc'].get('doi') for x in r1}
        for x in r2:
            if x['doc'].get('doi') not in seen:
                r1.append(x)
        r1.sort(key=lambda x: -x['score'])

    # Stage 3: full-text scan if still thin
    if len(r1) < min_results:
        stage = 3
        r3 = _search_index(docs, terms_low, population, geo, topic_terms, min_year, fulltext=True, instruments=instruments, anchor=anchor)
        seen = {x['doc'].get('doi') for x in r1}
        for x in r3:
            if x['doc'].get('doi') not in seen:
                r1.append(x)
        r1.sort(key=lambda x: -x['score'])

    # Instrument filtering: if the query named an instrument and we have instrument-hit
    # results, prioritize them (an instrument query should return instrument USERS, not
    # generic text matches). Keep non-instrument results only if too few instrument hits.
    if instruments:
        inst_hits = [x for x in r1 if x.get('instrument_hit')]
        if inst_hits:
            non_inst = [x for x in r1 if not x.get('instrument_hit')]
            if len(inst_hits) >= min_results:
                r1 = inst_hits + non_inst  # surface instrument users first
            else:
                r1 = inst_hits + non_inst  # few instrument hits: show them on top, rest after
            r1.sort(key=lambda x: (-(1 if x.get('instrument_hit') else 0), -x['score']))

    # Tier: split into content (studies/theses/students) vs reference (books/ebooks/
    # instruments/guidelines). References are lower-relevance for study queries, but
    # become PRIMARY when the query explicitly asks for them.
    student_results = []
    reference_results = []
    content_results = []
    for x in r1:
        dt = str(x['doc'].get('doc_type', '')).lower()
        if x.get('is_student'):
            student_results.append(x)
        elif dt in REF_DTYPES:
            reference_results.append(x)
        else:
            content_results.append(x)

    # Reference-intent: did the user explicitly ask for a book/ebook/instrument/guideline?
    # Reference-intent: did the user explicitly ask for a BOOK / EBOOK / INSTRUMENT /
    # GUIDELINE / QUESTIONNAIRE as the OBJECT of the query? (e.g. "find me an ebook about
    # stress", "what does the ENSS instrument measure"). Deliberately EXCLUDES bare
    # 'scale'/'measure'/'measurement' — those collide with "Nursing Stress Scale" and would
    # wrongly flip an instrument-USAGE query into a reference request.
    REF_INTENT = re.compile(r'\b(ebook|e-book|book|books|instrument|questionnaire|'
                             r'guideline|guidelines|manual|tool|measurements?)\b', re.I)
    ref_intent = bool(REF_INTENT.search(query))

    # Stage 4: web fallback if STILL nothing in content or reference
    web_candidates = []
    if len(content_results) == 0 and len(reference_results) == 0:
        stage = 4
        web_candidates = [{'needs_indexing': True, 'query': query,
                           'note': 'No local match; run web_search and ask user to add.'}]

    keywords_added = sum(1 for x in r1 if x.get('found_via') == 'fulltext')

    # LLM-style JUDGMENT layer on content results (don't just dump hits — reason).
    j = judge_results(content_results, population=population, geo=geo, topic_terms=topic_terms, instruments=instruments)
    judge_counts = {'n_on_topic': j['n_on_topic'], 'n_peripheral': j['n_peripheral'],
                    'n_dropped': j['n_dropped']}
    judged_core = j['keep']

    # References also judged (only on-topic/peripheral kept) so a "find ebook" query
    # returns the relevant ones, not everything tagged book.
    jr = judge_results(reference_results, population=population, geo=geo, topic_terms=topic_terms, instruments=instruments)
    judged_ref = jr['keep']

    # Order: if reference-intent, references lead; else content leads, refs follow.
    if ref_intent:
        core_results = judged_ref + judged_core
    else:
        core_results = judged_core + judged_ref

    # ---- Dynamic presentation (NOT a hard cap) ----
    # Judge how narrow/wide the query is from the JUDGED match pool:
    #   narrow   : pool <= 8   -> show ALL, safe to open every full text
    #   moderate : 9..broad_threshold -> show ALL (or top ~20), still openable
    #   wide     : > broad_threshold -> preview top `preview_n`, do NOT auto-open;
    #              return suggested_actions and ask the user what to do next
    pool = len(core_results)
    if pool <= 8:
        breadth = 'narrow'
    elif pool <= broad_threshold:
        breadth = 'moderate'
    else:
        breadth = 'wide'

    preview_n = min(15, pool)
    if breadth == 'wide':
        presented_core = core_results[:preview_n]
        open_fulltext = False
        suggested_actions = [
            f"Search returned {len(core_results)} candidates. After LLM-style judgment, "
            f"~{judge_counts['n_on_topic']} are ON_TOPIC (actually study the topic), "
            f"{judge_counts['n_peripheral']} peripheral, {judge_counts['n_dropped']} dropped as off-topic/duplicate.",
            "Options: (a) I open & summarise the ON_TOPIC set now, (b) narrow the query "
            "(e.g. add a sub-topic), (c) filter by population/year, (d) you name specific DOIs.",
        ]
    else:
        presented_core = core_results               # show everything when it's few/moderate
        open_fulltext = True
        suggested_actions = []

    return {
        'core_results': presented_core,
        'student_results': student_results,
        'reference_results': reference_results,
        'ref_intent': ref_intent,
        'stage_reached': stage,
        'terms_used': terms_low,
        'web_candidates': web_candidates,
        'keywords_added_count': keywords_added,
        'breadth': breadth,                    # 'narrow' | 'moderate' | 'wide'
        'open_fulltext': open_fulltext,        # False when wide -> agent must ask first
        'needs_narrowing': breadth == 'wide',
        'total_core_available': pool,
        'suggested_actions': suggested_actions,
        'judgment': judge_counts,              # LLM-style on-topic/peripheral/dropped breakdown
    }


def judge_results(core_results, population=None, geo=None, topic_terms=None, instruments=None):
    """LLM-style JUDGMENT layer over mechanical search results — TOPIC-AGNOSTIC.

    A pure search engine returns N hits; an LLM reasons over them. This function
    mimics that reasoning transparently so the agent can apply final judgment:
      - classify each study as ON_TOPIC / PERIPHERAL / OFF_TOPIC
        (does it actually STUDY the queried topic, or just mention it incidentally?)
      - flag DUPLICATES (same study, different DOI/version)
      - return a judgment-filtered 'keep' list = what an LLM would actually open.

    Signals (derive from the ACTUAL query terms, never hardcode a topic):
      ON_TOPIC  : a queried topic-term is the STUDIED OUTCOME — appears in title, OR the
                  abstract frames it as a measured/modelled variable for the population.
      PERIPHERAL: a topic-term appears in abstract but as a secondary/contextual factor.
      OFF_TOPIC : topic only incidental (population/geo mismatch sneaks through, or the
                  study is about something else that merely co-occurs with the terms).

    `topic_terms` = the matched term dict from the search (e.g. {'stress':3,'burnout':3});
    we use its KEYS as the outcome vocabulary so this works for ANY domain.
    """
    if topic_terms is None:
        topic_terms = TOPIC_W
    # outcome vocabulary = the QUERIED topic terms + generic morphological variants
    # (singular/plural/stem). Derived from the query, NEVER a fixed topic list.
    outcome_words = set()
    for t in topic_terms:
        outcome_words.add(t)
        outcome_words.add(t + 's')
        outcome_words.add(t.rstrip('s'))
        # split multi-word terms into their parts too (e.g. 'job satisfaction')
        for part in t.split():
            outcome_words.add(part)
            outcome_words.add(part + 's')
            outcome_words.add(part.rstrip('s'))
    outcome_re = re.compile(r'\b(' + '|'.join(re.escape(w) for w in outcome_words) + r')\b', re.I)

    # OFF_TOPIC tell-tales are GENERIC structural signals, not topic-specific:
    # a study whose TITLE is dominated by an unrelated construct AND does not put a
    # queried term in the title is likely incidental. We do NOT hardcode any topic
    # (no 'stress'/'burnout'/'nursing') here — only format/structural noise markers.
    OFF_TELL = re.compile(
        r'\b(table of contents|editorial|erratum|corrigendum|abstract book|conference program|'
        r'issue highlights|in this issue)\b', re.I)

    judged = []
    seen_keys = {}
    for x in core_results:
        d = x['doc']
        title = str(d.get('title', ''))
        ab = str(d.get('abstract', ''))
        t_low = title.lower()
        a_low = ab.lower()
        # duplicate detection: same normalized title (first 40 chars) + same year
        dup_key = (re.sub(r'[^a-z0-9]', '', t_low)[:40], str(d.get('year')))
        is_dup = dup_key in seen_keys
        if not is_dup:
            seen_keys[dup_key] = d.get('doi')
        # classification — driven by the QUERY's own terms, not a fixed topic
        topic_in_title = _title_has_topic(title, topic_terms)
        # studied-outcome signal: a queried term framed as measured/associated/factor
        outcome_signal = bool(re.search(
            r'(' + '|'.join(re.escape(w) for w in outcome_words) + r')\b.{0,45}'
            r'(among|in|of|between|and|associated|predict|factor|level|scale|questionnaire|measure|prevalence|risk)', a_low))
        if OFF_TELL.search(t_low) and not topic_in_title:
            cls = 'OFF_TOPIC'
        elif topic_in_title or (outcome_signal and not OFF_TELL.search(t_low)):
            cls = 'ON_TOPIC'
        elif outcome_signal:
            cls = 'PERIPHERAL'
        else:
            cls = 'PERIPHERAL'
        # Instrument awareness (topic-agnostic): if the query named an instrument and
        # this study's `measures` contain it, it is ON_TOPIC for an instrument query
        # regardless of generic text signals — this preserves instrument-first ordering.
        inst_hit = bool(x.get('instrument_hit'))
        if instruments and inst_hit:
            cls = 'ON_TOPIC'
        # Attach the EVIDENCE an LLM needs to make the FINAL relevance call (per user rule:
        # the regex layer is only a first pass — the agent must judge using real metadata +
        # abstract + full text, not the regex). Each item carries title, year, population,
        # measures, an abstract snippet, and a plain-language reason for its classification.
        d = x['doc']
        ab = str(d.get('abstract', ''))
        evidence = {
            'title': d.get('title', ''),
            'year': d.get('year', ''),
            'population': d.get('population', ''),
            'measures': d.get('measures', []) or [],
            'abstract_snippet': (ab[:320] + ('…' if len(ab) > 320 else '')),
            'full_text_available': 'extracted_text' in (d.get('files', {}) or {}) or 'full_text_pdf' in (d.get('files', {}) or {}),
            'reason': f"{cls}: " + (
                "instrument match for query" if (instruments and inst_hit)
                else ("topic term in title/abstract as studied outcome" if topic_in_title or outcome_signal
                      else "topic appears only incidentally / contextual")
            ),
        }
        judged.append({**x, 'judgment': cls, 'is_duplicate': is_dup,
                       'instrument_hit': inst_hit, 'evidence': evidence})
    keep = [x for x in judged if not x['is_duplicate'] and x['judgment'] in ('ON_TOPIC', 'PERIPHERAL')]
    # Instrument-first: when the query is instrument-specific, surface instrument users
    # ahead of incidental text matches.
    if instruments:
        keep.sort(key=lambda x: (0 if x.get('instrument_hit') else 1,))
    on_topic = [x for x in keep if x['judgment'] == 'ON_TOPIC']
    peripheral = [x for x in keep if x['judgment'] == 'PERIPHERAL']
    dropped = [x for x in judged if x['judgment'] == 'OFF_TOPIC' or x['is_duplicate']]
    return {
        'judged': judged,
        'keep': keep,
        'on_topic': on_topic,
        'peripheral': peripheral,
        'dropped': dropped,
        'n_on_topic': len(on_topic),
        'n_peripheral': len(peripheral),
        'n_dropped': len(dropped),
        # The agent (LLM) should treat the above as a FIRST-PASS only and re-adjudicate
        # using each item's `evidence` (real abstract/metadata/full-text), not the regex.
        'note': 'First-pass heuristic judgment. LLM must confirm using evidence (abstract/metadata/full text) before citing.',
    }


def _web_fallback(query, terms_low):
    return [{'needs_indexing': True, 'query': query,
             'note': 'No local match; run web_search and ask user to add.'}]
