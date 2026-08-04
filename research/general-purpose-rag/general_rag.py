"""
Universal RAG System v4.5 - Smart Search with Query Expansion & Web Fallback
Key improvements over v4.4:
1. Query expansion with synonyms/concept expansion
2. Low-recall trigger for deeper search
3. Web fallback with clear separation
4. Result labeling (source, match type, verification)
5. Low-recall logging for tag dictionary review
6. Offer to index web-found studies
"""
import os
import json
import re
import shutil
import argparse
import hashlib
from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple, Optional

class UniversalRAG:
    def __init__(self, base_dir=None):
        """Initialize with automatic base directory detection"""
        if base_dir:
            self.base_dir = self._normalize_path(base_dir)
        else:
            # Multi-level detection
            candidates = [
                os.getcwd(),
                os.path.join(os.path.expanduser('~'), '.hermes', 'cache', 'web', 'universal_rag'),
                os.path.join(os.path.expanduser('~'), 'AppData', 'Local', 'hermes', 'cache', 'web', 'universal_rag'),
                # Windows native paths
                os.path.normpath(os.path.join(os.environ.get('USERPROFILE', os.environ.get('HOME', '')), 'AppData', 'Local', 'hermes', 'cache', 'web', 'universal_rag')),
            ]
            for candidate in candidates:
                norm_candidate = self._normalize_path(candidate)
                if os.path.exists(os.path.join(norm_candidate, 'UNIVERSAL_CATALOG.json')):
                    self.base_dir = norm_candidate
                    break
            else:
                # Default to local directory
                self.base_dir = self._normalize_path('C:\\Users\\Milos\\AppData\\Local\\hermes\\cache\\web\\universal_rag')
                os.makedirs(self.base_dir, exist_ok=True)
        
        # Normalize path
        self.base_dir = self._normalize_path(self.base_dir)
        self.index_path = os.path.join(self.base_dir, 'UNIVERSAL_CATALOG.json')
        self.backup_dir = os.path.join(self.base_dir, 'backups')
        os.makedirs(self.backup_dir, exist_ok=True)
        self.catalog = self._load_catalog()
    
    def _normalize_path(self, path):
        """Normalize paths - handle both forward and backslashes, double escaping"""
        path = os.path.normpath(path)
        path = os.path.normpath(path.replace('\\\\', '\\'))
        # Convert to native format
        return os.path.abspath(path)
    
    # Query expansion dictionary — OPTIONAL DOMAIN-TUNING, NOT a topic gate.
    # IMPORTANT (topic-agnostic design): this dict is only consulted when a QUERY TERM
    # literally matches one of its KEYS. A query like "diabetes" or "wound care" matches
    # no key here, so it gets NO nursing/stress expansion — the catalog is searched as-is.
    # For a fully general ("universal") instance you may EMPTY this dict; expansion simply
    # becomes a no-op. It is intentionally kept separate from ranking/config so a deployer
    # can swap domain vocabulary without touching search logic. Kept here (not a separate
    # file) for portability of the legacy script; precise_search.py is the active,
    # fully topic-agnostic search and does not depend on this dict.
    QUERY_EXPANSIONS = {
        "workload": ["work load", "work-load", "heavy workload", "excessive workload",
                     "task load", "staffing shortage", "understaffing", "overwork",
                     "work demands", "nasa-tlx"],
        "burnout": ["emotional exhaustion", "depersonalization", "cynicism",
                    "compassion fatigue", "professional burnout", "occupational burnout",
                    "exhaustion"],
        "emotional exhaustion": ["burnout", "compassion fatigue", "cynicism"],
        "depersonalization": ["burnout", "emotional detachment", "cynicism"],
        "job satisfaction": ["turnover", "turnover intention", "retention",
                             "intention to leave", "job contentment", "job morale",
                             "job dissatisfaction"],
        "stress": ["job stress", "occupational stress", "work-related stress",
                   "psychological stress", "work stress", "nursing stress"],
        "nursing stress": ["occupational stress", "job stress", "work-related stress",
                            "nursing workplace stress"],
        "patient safety": ["safety culture", "safety climate", "medication error",
                           "adverse event", "medical error", "safety climate",
                           "error rate", "preventable adverse event"],
        "supervisor": ["supervisory", "management style", "conflict with doctor",
                       "conflict with physicians", "physician-nurse conflict",
                       "hierarchical conflict"],
        "nurses": ["nursing", "registered nurses", "ICU nurses", "ward nurses",
                   "nurses' perception", "nursing staff"],
        "malaysia": ["malaysian", "kuala lumpur", "penang", "malaysian nursing",
                     "east coast", "hospital"],
        "icu": ["intensive care", "critical care", "ccu", "intensive care unit"],
        "bullying": ["workplace bullying", "harassment", "mistreatment",
                     "vertical violence", "lateral violence", "abuse"],
        "discrimination": ["discriminatory", "bias", "prejudice", "racism"],
        "turnover": ["intention to leave", "retention", "attrition", "staff turnover"],
        "shift work": ["night shift", "rotating shift", "shift schedule"],
        "moral distress": ["ethical distress", "moral injury", "ethical dilemma",
                           "ethical conflict"],
    }
    
    def _expand_query(self, query):
        """Expand query with related terms/concepts"""
        original_terms = query.lower().split()
        expanded_terms = list(original_terms)  # Start with original terms
        
        for term in original_terms:
            if term in self.QUERY_EXPANSIONS:
                for expansion in self.QUERY_EXPANSIONS[term]:
                    if expansion not in expanded_terms:
                        expanded_terms.append(expansion)
        
        # Track which terms matched for evidence labeling
        expansion_map = {}
        for term in original_terms:
            if term in self.QUERY_EXPANSIONS:
                expansion_map[term] = self.QUERY_EXPANSIONS[term]
        
        return original_terms, expanded_terms, expansion_map
    
    def _log_low_recall_query(self, query, expansions_used, results_count):
        """Log low-recall queries for tag dictionary review"""
        log_path = os.path.join(self.base_dir, 'low_recall_log.json')
        entry = {
            'query': query,
            'timestamp': datetime.now().isoformat(),
            'expansions_used': expansions_used,
            'results_count': results_count,
            'fulltext_triggered': len(expansions_used) > 0,
        }
        
        existing = []
        if os.path.exists(log_path):
            try:
                with open(log_path, 'r') as f:
                    existing = json.load(f)
            except:
                existing = []
        
        existing.append(entry)
        with open(log_path, 'w') as f:
            json.dump(existing, f, indent=2)
    
    def _search_web_fallback(self, query, original_terms, expanded_terms, limit=5):
        """Search web for studies not in local collection
        
        Uses the Hermes web_search tool when available (interactive mode).
        When running standalone, this returns an empty list so the user
        knows to use the interactive client for web fallback.
        """
        # Build search query for academic databases
        web_query = query
        if len(expanded_terms) > len(original_terms):
            web_query = ' OR '.join([t for t in expanded_terms[:5]])
        
        results = []
        try:
            # When running inside Hermes agent, web_search is available as a tool
            # When running standalone, this will raise NameError
            search_results = web_search(web_query + ' research study', limit=limit)
            for item in search_results.get('data', {}).get('web', []):
                title = item.get('title', '')
                url = item.get('url', '')
                doi_match = re.search(r'(10\.\d{4,}/[^\s]+)', title + ' ' + url)
                doi = doi_match.group(1) if doi_match else ''
                
                results.append({
                    'doi': doi,
                    'title': title,
                    'url': url,
                    'authors': [],
                    'year': '',
                    'journal': '',
                    'verification_status': 'UNVERIFIED_WEB',
                    'source': 'web_fallback',
                    'match_type': 'web_search',
                    'evidence': [f"Web search result for '{query}'"],
                })
        except NameError:
            # web_search tool not available in this context
            pass
        except Exception:
            pass
        
        return results
    
    def _backup_catalog(self):
        """Create timestamped backup, keep only last 3 versions"""
        if not os.path.exists(self.index_path):
            return None
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = os.path.join(self.backup_dir, f'UNIVERSAL_CATALOG_{timestamp}.json')
        
        try:
            shutil.copy2(self.index_path, backup_path)
            
            # Keep only last 3 backups
            backups = sorted(
                [f for f in os.listdir(self.backup_dir) if f.startswith('UNIVERSAL_CATALOG_')],
                key=lambda x: os.path.getmtime(os.path.join(self.backup_dir, x))
            )
            
            while len(backups) > 3:
                old_backup = os.path.join(self.backup_dir, backups.pop(0))
                os.remove(old_backup)
                print(f"  🗑️ Removed old backup: {os.path.basename(old_backup)}")
            
            print(f"  💾 Backup created: {os.path.basename(backup_path)}")
            return backup_path
        except Exception as e:
            print(f"  ⚠️ Backup failed: {e}")
            return None
    
    def _load_catalog(self):
        """Load catalog with automatic integrity check"""
        if not os.path.exists(self.index_path):
            print(f"⚠️ Catalog not found at {self.index_path}")
            self.catalog = self._create_empty_catalog()
            return self.catalog
        
        try:
            with open(self.index_path, 'r', encoding='utf-8') as f:
                catalog = json.load(f)
        except json.JSONDecodeError:
            print("❌ Corrupted catalog, restoring from backup...")
            self._restore_latest_backup()
            try:
                with open(self.index_path, 'r', encoding='utf-8') as f:
                    catalog = json.load(f)
            except:
                self.catalog = self._create_empty_catalog()
                return self.catalog
        
        # Set catalog BEFORE repair so save_catalog works
        self.catalog = catalog
        # Auto-fix common issues
        self._repair_catalog(catalog)
        return catalog
    
    def _create_empty_catalog(self):
        """Create empty catalog structure"""
        return {
            'documents': [],
            'search_index': {},
            'metadata': {
                'total_documents': 0,
                'verified_dois': 0,
                'domains': [],
                'last_updated': datetime.now().isoformat(),
                'version': '4.4.0'
            },
            'stats': {
                'by_domain': {},
                'by_instrument': {},
                'by_tag': {},
                'by_year': {}
            }
        }
    
    def _repair_catalog(self, catalog):
        """Repair common catalog issues"""
        repaired = False
        
        if 'documents' not in catalog:
            catalog['documents'] = []
            repaired = True
        
        if 'metadata' not in catalog:
            catalog['metadata'] = {}
            repaired = True
        
        if 'stats' not in catalog:
            catalog['stats'] = {}
            repaired = True
        
        # Fix missing fields in documents
        for doc in catalog.get('documents', []):
            if 'inferred_tags' not in doc:
                doc['inferred_tags'] = doc.get('tags', [])
                repaired = True
            if 'files' not in doc:
                doc['files'] = {}
                repaired = True
            if 'verification_status' not in doc:
                doc['verification_status'] = 'UNKNOWN'
                repaired = True
        
        if repaired:
            catalog['metadata']['last_updated'] = datetime.now().isoformat()
            self.save_catalog()
            print(f"🔧 Auto-repaired catalog issues")
    
    def _restore_latest_backup(self):
        """Restore from latest backup"""
        if not os.path.exists(self.backup_dir):
            return None
        
        backups = sorted(
            [f for f in os.listdir(self.backup_dir) if f.startswith('UNIVERSAL_CATALOG_')],
            key=lambda x: os.path.getmtime(os.path.join(self.backup_dir, x)),
            reverse=True
        )
        
        if backups:
            latest = os.path.join(self.backup_dir, backups[0])
            shutil.copy2(latest, self.index_path)
            print(f"✅ Restored from backup: {backups[0]}")
            return latest
        return None
    
    def save_catalog(self):
        """Save catalog with automatic backup"""
        # Backup first
        self._backup_catalog()
        
        # Update metadata
        self.catalog['metadata']['total_documents'] = len(self.catalog.get('documents', []))
        self.catalog['metadata']['last_updated'] = datetime.now().isoformat()
        
        # Save to temp file first (atomic write)
        temp_path = self.index_path + '.tmp'
        with open(temp_path, 'w', encoding='utf-8') as f:
            json.dump(self.catalog, f, indent=2, ensure_ascii=False)
        os.replace(temp_path, self.index_path)
    
    def verify_doi_metadata(self, doi):
        """Always resolve and verify DOI before presenting results"""
        try:
            import urllib.request
            url = f"https://api.crossref.org/works/{doi}"
            req = urllib.request.Request(url, headers={'User-Agent': 'RAG-System/4.4'})
            with urllib.request.urlopen(req, timeout=30) as response:
                if response.status == 200:
                    data = json.loads(response.read())
                    message = data.get('message', {})
                    
                    # Return full verified metadata
                    return {
                        'status': 'VERIFIED',
                        'title': message.get('title', [''])[0] if message.get('title') else '',
                        'authors': self._extract_authors(message.get('author', [])),
                        'year': str(message.get('published', {}).get('date-parts', [['']])[0][0]),
                        'journal': ' '.join(message.get('container-title', [''])),
                        'volume': str(message.get('volume', '')),
                        'issue': str(message.get('issue', '')),
                        'pages': message.get('page', ''),
                        'doi': doi,
                        'official_url': f"https://doi.org/{doi}",
                        'abstract': message.get('abstract', ''),
                        'verified_at': datetime.now().isoformat()
                    }
        except Exception as e:
            return {'status': 'VERIFICATION_FAILED', 'error': str(e)[:100]}
        
        return {'status': 'CITED_ONLY', 'note': 'DOI verification failed'}
    
    def _extract_authors(self, authors_list):
        """Extract authors from Crossref response - filters out affiliations/organizations"""
        authors = []
        for author in authors_list:
            given = author.get('given', '')
            family = author.get('family', '')
            # Skip entries that are just affiliations (have 'name' but no 'given'/'family')
            if 'name' in author and not (given or family):
                continue
            full_name = ' '.join(part for part in [given, family] if part).strip()
            if full_name:
                authors.append(full_name)
        return authors
    
    def extract_doi_from_text(self, text):
        """Extract DOI from text - prioritizes first page / early occurrences"""
        doi_pattern = r'(10\.\d{4,}/[^\s<>"\']+)'
        matches = re.findall(doi_pattern, text)
        
        valid_dois = []
        for doi in matches:
            doi = doi.strip('.').strip(',').strip(')')
            if len(doi) > 10 and '/' in doi.replace('10.', '', 1):
                valid_dois.append(doi)
        
        # Also check for URL-style DOIs
        url_pattern = r'https?://(?:dx\.)?doi\.org/(10\.\d{4,}/[^\s<>"\')]+)'
        url_matches = re.findall(url_pattern, text)
        for doi in url_matches:
            if doi.strip('.').strip(',') not in valid_dois:
                valid_dois.append(doi.strip('.').strip(','))
        
        # Prioritize DOI from first part of document (first page)
        # Split at common boundaries that indicate we've moved past the header
        early_text = text[:2000]  # First 2000 chars
        early_dois = []
        for match in re.finditer(doi_pattern, early_text):
            doi = match.group(1).strip('.').strip(',').strip(')')
            if len(doi) > 10:
                early_dois.append(doi)
        
        if early_dois:
            # Return early DOIs first (more likely to be the paper's own DOI)
            return early_dois + [d for d in valid_dois if d not in early_dois]
        
        return valid_dois
    
    def extract_text_from_pdf(self, pdf_path):
        """Extract text from PDF using PyMuPDF - reads ALL pages, not just first 12"""
        try:
            import fitz  # PyMuPDF
            doc = fitz.open(pdf_path)
            text = ""
            total_pages = doc.page_count  # Read ALL pages, not just first 12
            
            for page_num in range(total_pages):
                page = doc.load_page(page_num)
                text += page.get_text()
            
            # Extract abstract
            abstract = ""
            for page_num in range(min(3, doc.page_count)):
                page = doc.load_page(page_num)
                content = page.get_text()
                lines = content.split('\n')
                in_abstract = False
                for line in lines:
                    if 'abstract' in line.lower():
                        in_abstract = True
                    elif in_abstract and line.strip() and line.isupper() and len(line) > 5:
                        break
                    elif in_abstract:
                        abstract += line + ' '
            
            doc.close()
            return text.strip(), abstract.strip()[:2000]
        except ImportError:
            # Fallback to basic PDF parsing
            try:
                with open(pdf_path, 'rb') as f:
                    content = f.read()
                text = ""
                # Basic text extraction fallback
                try:
                    text = content.decode('utf-8', errors='ignore')
                except:
                    text = ""
                return text[:5000], text[:500]
            except:
                return "", ""
        except Exception as e:
            print(f"  ⚠️ PDF extraction error: {e}")
            return "", ""
    
    def infer_tags(self, text, instruments, population, domain="general"):
        """Infer tags from content with domain-specific keyword matching
        
        Domain-specific keyword dictionaries allow this to work across any research field,
        not just nursing/occupational stress. The default 'general' domain includes
        cross-domain keywords. Domain-specific sets are loaded from domain_tags.json.
        """
        text_lower = text.lower()
        tags = []
        
        # Load domain-specific tag keywords
        tag_keywords = self._load_domain_tags(domain)
        
        for tag, keywords in tag_keywords.items():
            for kw in keywords:
                if kw in text_lower:
                    tags.append(tag)
                    break
        
        # Instrument-based tags
        for instr in instruments:
            if instr not in ["Not specified"]:
                tags.append(instr)
        
        # Population-based tags
        pop_lower = population.lower()
        if 'malaysia' in pop_lower:
            tags.append('Malaysia')
            tags.append('Malaysian Nursing Stress')
        if 'icu' in pop_lower:
            tags.append('ICU')
        
        # Deduplicate while preserving order
        seen = set()
        unique_tags = []
        for tag in tags:
            if tag not in seen:
                seen.add(tag)
                unique_tags.append(tag)
        
        return unique_tags
    
    def _load_domain_tags(self, domain="general"):
        """Load domain-specific tag keywords from config file or defaults"""
        config_path = os.path.join(self.base_dir, 'domain_tags.json')
        
        # Default cross-domain tags
        default_tags = {
            "Workload": ["work load", "workload", "work-load", "excessive workload",
                        "heavy workload", "staffing shortage", "overwork"],
            "Burnout": ["burnout", "emotional exhaustion", "depersonalization", "cynicism"],
            "Job Satisfaction": ["job satisfaction", "turnover", "retention", "intention to leave"],
            "Patient Safety": ["patient safety", "safety culture", "medication error",
                              "adverse event", "error rate"],
            "Job Stress": ["job stress", "occupational stress", "work-related stress"],
            "Mental Health": ["mental health", "anxiety", "depression", "psychological"],
            "Workplace Issues": ["supervisor", "supervis", "management", "conflict",
                               "bullying", "harassment", "discrimination"],
        }
        
        # Domain-specific extensions
        domain_tags = {
            "ENSS": {
                "Problems With Supervisors": ["supervisor", "supervisory", "management style",
                                              "conflict with doctor"],
                "Discrimination": ["discrimin", "racism", "prejudice", "bias"],
                "ICU": ["icu", "intensive care", "critical care"],
                "New Graduate": ["new grad", "newly graduated", "novice nurse"],
                "COVID-19": ["covid", "pandemic", "coronavirus"],
                "Moral Distress": ["moral distress", "ethical distress"],
                "Moral Injury": ["moral injury"],
                "Shift Work": ["shift work", "night shift", "rotating shift"],
            },
            "OUM_Research": {
                "Workload": ["work load", "workload", "heavy workload", "staffing shortage"],
                "Problems With Supervisors": ["supervisor", "supervisory", "management style"],
                "Discrimination": ["discrimin", "racism", "prejudice"],
                "Burnout": ["burnout", "emotional exhaustion"],
                "Job Satisfaction": ["job satisfaction", "turnover", "retention"],
                "Patient Safety": ["patient safety", "safety culture"],
                "ICU": ["icu", "intensive care", "critical care"],
                "New Graduate": ["new grad", "newly graduated", "novice"],
                "COVID-19": ["covid", "pandemic", "coronavirus"],
                "Moral Distress": ["moral distress", "ethical distress"],
                "Workplace Bullying": ["workplace bullying", "bullying"],
                "Shift Work": ["shift work", "night shift"],
            },
            "Selected Studies": {
                "Workload": ["workload", "task load", "nasa-tlx"],
                "Burnout": ["burnout", "exhaustion", "cynicism"],
                "Job Satisfaction": ["job satisfaction", "turnover"],
                "Patient Safety": ["patient safety", "safety culture", "error"],
            },
            "Mendeley Import": {
                "Workload": ["work load", "workload", "heavy workload", "workload"],
                "Burnout": ["burnout", "exhaustion", "emotional"],
                "Job Satisfaction": ["job satisfaction", "turnover", "retention"],
                "Patient Safety": ["patient safety", "safety culture"],
                "ICU": ["icu", "intensive care"],
                "New Graduate": ["new grad", "novice"],
                "COVID-19": ["covid", "pandemic"],
                "Workplace Bullying": ["bullying", "harassment"],
                "Shift Work": ["shift work", "night shift", "rotating"],
                "Moral Distress": ["moral distress", "ethical"],
            },
        }
        
        # Check for user config file
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    user_config = json.load(f)
                if domain in user_config:
                    default_tags.update(user_config[domain])
            except:
                pass
        
        # Merge default with domain-specific
        if domain in domain_tags:
            default_tags.update(domain_tags[domain])
        
        return default_tags
    
    def identify_instruments(self, text):
        """Identify research instruments used in the study"""
        text_lower = text.lower()
        instruments = []
        
        instrument_patterns = {
            "ENSS": ["ennis", "ennis scale", "ennis-", "expanded nursing stress"],
            "NSS": ["nss", "nursing stress scale", "nss-"],
            "PSS": ["pss", "perceived stress scale", "pss-"],
            "ERI": ["eri", "effort-reward imbalance", "effort-reward model"],
            "MBI": ["mbi", "maslach burnout", "mbi-gs", "mbi-hss"],
            "NASA-TLX": ["nasa-tlx", "nasa tlx", "task load index"],
            "NWSQ": ["nwsq", "nursing worklife", "worklife survey"],
            "STAI": ["stai", "state-trait anxiety", "anxiety inventory"],
        }
        
        for name, patterns in instrument_patterns.items():
            for pattern in patterns:
                if pattern in text_lower:
                    instruments.append(name)
                    break
        
        return instruments if instruments else ["Not specified"]
    
    def identify_population(self, text, title):
        """Identify population studied"""
        combined = (text + ' ' + title).lower()
        
        populations = []
        
        # Nurses
        if 'nurse' in combined:
            prof = "Nurses"
            if 'icu' in combined or 'intensiv' in combined:
                prof = f"{prof} (ICU)"
            elif 'registered' in combined:
                prof = f"{prof} (Registered)"
            elif 'new grad' in combined or 'newly graduated' in combined:
                prof = f"{prof} (New graduates)"
            populations.append(prof)
        
        if 'doctor' in combined or 'physician' in combined:
            populations.append("Doctors")
        if 'student' in combined:
            populations.append("Students")
        if 'public health' in combined:
            populations.append("Public Health Workers")
        
        # Countries
        countries = ['malaysia', 'indonesia', 'china', 'australia', 'italy', 
                    'palestine', 'thailand', 'india']
        for country in countries:
            if country in combined:
                populations.append(country.capitalize())
        
        return '; '.join(set(populations)) if populations else "Not specified"
    
    def check_doi_duplicate(self, doi):
        """Check if DOI already exists (case-insensitive)"""
        existing = [d for d in self.catalog.get('documents', []) if d.get('doi', '').lower() == doi.lower()]
        return existing[0] if existing else None
    
    def _is_recently_verified(self, doc):
        """Check if document was verified within last 30 days"""
        if doc.get('verification_status') != 'VERIFIED':
            return False
        verified_at = doc.get('verified_at')
        if not verified_at:
            return False
        try:
            verified_date = datetime.fromisoformat(verified_at)
            diff = datetime.now() - verified_date
            return diff.days < 30
        except:
            return False
    
    def enhance_metadata(self, doc):
        """Always verify DOI and enhance metadata"""
        doi = doc.get('doi', '')
        if not doi or doi.startswith('local:') or not doi.startswith('10.'):
            return doc
        
        # Check if already verified recently (within 30 days)
        if self._is_recently_verified(doc):
            return doc
        
        # Verify with Crossref
        verified = self.verify_doi_metadata(doi)
        if verified.get('status') == 'VERIFIED':
            doc['title'] = verified.get('title', doc.get('title', ''))
            doc['authors'] = verified.get('authors', doc.get('authors', []))
            doc['year'] = verified.get('year', doc.get('year', ''))
            doc['journal'] = verified.get('journal', doc.get('journal', 'Not specified'))
            doc['volume'] = verified.get('volume', doc.get('volume', ''))
            doc['issue'] = verified.get('issue', doc.get('issue', ''))
            doc['pages'] = verified.get('pages', doc.get('pages', ''))
            doc['abstract'] = verified.get('abstract', doc.get('abstract', ''))
            doc['verification_status'] = 'VERIFIED'
            doc['verification_note'] = 'Crossref DOI resolved successfully'
            doc['files']['base_path'] = self.base_dir
            return doc
        else:
            doc['verification_status'] = 'PARTIALLY_VERIFIED'
            doc['verification_note'] = verified.get('note', 'DOI verification issue')
            return doc
    
    def search(self, query, max_results=20, domains=None, tags=None, instruments=None,
               verify_results=True, fulltext_search=False, debug=False, use_expansion=True,
               threshold=5):
        """Smart search with query expansion, low-recall trigger, and web fallback
        
        Steps:
        1. Query expansion - generate related terms
        2. Local search with expanded terms
        3. If results < threshold: deeper full-text search + more expansions
        4. If still < threshold: web fallback (clearly labeled)
        """
        search_trace = {
            'original_query': query,
            'expansion_used': False,
            'expansion_terms': [],
            'deeper_search_triggered': False,
            'web_fallback_used': False,
            'web_results_count': 0,
        }
        
        # Step 1: Query expansion
        if use_expansion:
            original_terms, expanded_terms, expansion_map = self._expand_query(query)
            if expanded_terms != original_terms:
                search_trace['expansion_used'] = True
                search_trace['expansion_terms'] = [t for t in expanded_terms if t not in original_terms]
        else:
            original_terms = query.split()
            expanded_terms = list(original_terms)
            expansion_map = {}
        
        # Step 2: Initial local search
        results = self._do_local_search(
            expanded_terms, original_terms, expansion_map, domains, tags, instruments,
            verify_results, fulltext_search, debug
        )
        
        # Step 3: Low-recall trigger
        if len(results) < threshold:
            search_trace['deeper_search_triggered'] = True
            
            # Try additional expansions
            extra_terms = self._get_additional_expansions(query, original_terms)
            all_terms = list(expanded_terms) + [t for t in extra_terms if t not in expanded_terms]
            
            # Deeper full-text search
            deeper_results = self._do_local_search(
                all_terms, original_terms, expansion_map, domains, tags, instruments,
                verify_results, fulltext_search=True, debug=debug  # Forced fulltext
            )
            
            # Merge results (avoid duplicates by DOI)
            existing_dois = set(r.get('doi', '') for r in results)
            for r in deeper_results:
                if r.get('doi', '') not in existing_dois:
                    results.append(r)
        
        # Step 4: Web fallback
        web_results = []
        if len(results) < threshold:
            search_trace['web_fallback_used'] = True
            print(f"\n🔍 Local coverage is thin ({len(results)} results for '{query}')")
            print(f"   Triggering web fallback search...")
            web_results = self._search_web_fallback(query, original_terms, list(expanded_terms + self._get_additional_expansions(query, original_terms)))
            search_trace['web_results_count'] = len(web_results)
            
            if web_results:
                print(f"\n   Found {len(web_results)} additional result(s) from web search")
                print(f"   (These are NOT in your local catalog)\n")
            else:
                self._log_low_recall_query(query, search_trace['expansion_terms'] + self._get_additional_expansions(query, original_terms), len(results))
        
        # Combine results with clear labeling
        all_results = results + [{'source': 'web_fallback', **r} for r in web_results]

        # NOTE: low-recall logging is already handled above (inside the web-fallback
        # branch) — do NOT log again here, or the same query gets logged twice.
        
        # Sort and limit
        all_results.sort(key=lambda x: x.get('match_score', 0) if isinstance(x.get('match_score'), (int, float)) else 0, reverse=True)
        final_results = all_results[:max_results]
        
        # Attach search trace to results for transparency
        if final_results and len(final_results) > 0:
            final_results[0]['_search_trace'] = search_trace
        
        return final_results
    
    def _get_additional_expansions(self, query, original_terms):
        """Get additional expansion terms beyond initial expansion"""
        additional = []
        for term in original_terms:
            if term in self.QUERY_EXPANSIONS:
                # Use next batch of expansions
                expansions = self.QUERY_EXPANSIONS[term]
                # For deeper search, also try word-by-word expansion
                for exp in expansions:
                    if exp not in additional and len(exp.split()) <= 2:
                        additional.append(exp)
        # Also try splitting query into individual concepts
        return additional[:5]
    
    def _do_local_search(self, search_terms, original_terms, expansion_map, domains, tags, 
                          instruments, verify_results, fulltext_search, debug):
        """Execute local catalog search with given terms"""
        candidates = []
        for doc in self.catalog.get('documents', []):
            # Domain filter
            if domains:
                if isinstance(domains, str):
                    domains_list = [domains]
                else:
                    domains_list = domains
                if doc.get('domain', 'general') not in domains_list:
                    continue
            
            # Tag filter
            if tags:
                doc_tags = set(t.lower() for t in doc.get('inferred_tags', []))
                if isinstance(tags, str):
                    tags_list = [tags]
                else:
                    tags_list = tags
                if not any(t.lower() in doc_tags for t in tags_list):
                    continue
            
            # Instrument filter
            if instruments:
                doc_instrs = set(str(i).lower() for i in doc.get('instrument', []))
                if isinstance(instruments, str):
                    instr_list = [instruments]
                else:
                    instr_list = instruments
                if not any(i.lower() in doc_instrs for i in instr_list):
                    continue
            
            # Searchable text - includes metadata + cached keyword index
            searchable_parts = [
                doc.get('title', ''),
                doc.get('abstract', ''),
                doc.get('journal', ''),
                ' '.join(doc.get('inferred_tags', [])),
                ' '.join(doc.get('official_keywords', []))
            ]
            
            # Optional: check full text if enabled (slower but higher recall)
            if fulltext_search:
                text_file = doc.get('files', {}).get('extracted_text', '')
                if text_file:
                    for path_candidate in [os.path.join(doc.get('files', {}).get('base_path', self.base_dir), text_file),
                                            os.path.join(self.base_dir, text_file)]:
                        if os.path.exists(path_candidate):
                            try:
                                with open(path_candidate, 'r', encoding='utf-8', errors='ignore') as f:
                                    searchable_parts.append(f.read(10000))
                                break
                            except:
                                pass
            
            searchable = ' '.join(searchable_parts).lower()
            
            # Debug: explain why document was excluded
            if debug and not any(term.lower() in searchable for term in search_terms):
                reasons = [f"no match for '{term}'" for term in search_terms if term.lower() not in searchable]
                print(f"  [EXCLUDED] {doc.get('title', '')[:40]}... | {', '.join(reasons)}")
            
            if any(term.lower() in searchable for term in search_terms):
                candidates.append(doc)
        
        # Confirm matches against full text
        results = []
        for doc in candidates:
            confidence, evidence, score = self._confirm_match(doc, search_terms)
            if confidence != "low":
                # Verify DOI before presenting (but skip if already verified recently)
                if verify_results and doc.get('doi', '').startswith('10.'):
                    needs_verification = False
                    if doc.get('verification_status') != 'VERIFIED':
                        needs_verification = True
                    elif doc.get('verification_note', '').find('Crossref') == -1:
                        needs_verification = True
                    elif not self._is_recently_verified(doc):
                        needs_verification = True
                    
                    if needs_verification:
                        verified = self.verify_doi_metadata(doc['doi'])
                        if verified.get('status') == 'VERIFIED':
                            doc = self.enhance_metadata(doc)
                
                # Label which terms matched (original vs expanded)
                matched_evidence = []
                for ev in evidence[:3]:
                    # Check if evidence refers to an original or expanded term
                    is_expanded = False
                    for orig_term, expansions in expansion_map.items():
                        if any(exp_term in ev.lower() for exp_term in expansions):
                            is_expanded = True
                            matched_evidence.append(f"[EXPANSION of '{orig_term}']: {ev}")
                            break
                    if not is_expanded:
                        matched_evidence.append(ev)
                
                results.append({
                    "doi": doc.get('doi', ''),
                    "title": doc.get('title', ''),
                    "year": doc.get('year', ''),
                    "journal": doc.get('journal', ''),
                    "authors": doc.get('authors', []),
                    "volume": doc.get('volume', ''),
                    "issue": doc.get('issue', ''),
                    "pages": doc.get('pages', ''),
                    "instrument": doc.get('instrument', []),
                    "population": doc.get('population', 'Not specified'),
                    "domain": doc.get('domain', 'general'),
                    "verification_status": doc.get('verification_status', 'Unknown'),
                    "confidence": confidence,
                    "match_score": score,
                    "tags": doc.get('inferred_tags', []),
                    "official_keywords": doc.get('official_keywords', []),
                    "scope_note": doc.get('scope_notes', ''),
                    "evidence": matched_evidence,
                    "has_file": 'extracted_text' in doc.get('files', {}) or 'full_text_pdf' in doc.get('files', {}),
                    "abstract": doc.get('abstract', '')[:200],
                    "source": "local_catalog",
                    # match_type is per-RESULT (not per-search): an expansion tag in THIS
                    # document's matched_evidence means it matched via an expanded term.
                    "match_type": "expanded" if any(
                        str(e).startswith("[EXPANSION") for e in matched_evidence) else "literal"
                })
        
        # Sort by score
        results.sort(key=lambda x: x['match_score'], reverse=True)
        return results
    
    def _confirm_match(self, doc, query_terms):
        """Confirm match against actual file content"""
        evidence = []
        score = 1.0
        
        text = doc.get('title', '') + ' ' + doc.get('abstract', '')
        
        files = doc.get('files', {})
        base_path = files.get('base_path', self.base_dir)
        
        # Try extracted text file
        text_file = files.get('extracted_text', '')
        if text_file:
            text_path = os.path.join(base_path, text_file)
            if not os.path.exists(text_path):
                text_path = os.path.join(self.base_dir, text_file)
            if os.path.exists(text_path):
                try:
                    with open(text_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read(10000)
                        text += ' ' + content
                except:
                    pass
        
        # Also check full text PDF
        full_file = files.get('full_text_pdf', '')
        if full_file:
            full_path = os.path.join(base_path, full_file)
            if not os.path.exists(full_path):
                full_path = os.path.join(self.base_dir, full_file)
            if os.path.exists(full_path):
                try:
                    extracted, _ = self.extract_text_from_pdf(full_path)
                    text += ' ' + extracted[:5000]
                except:
                    pass
        
        text_lower = text.lower()
        
        # Check each query term
        for term in query_terms:
            if term.lower() in text_lower:
                count = text_lower.count(term.lower())
                score += count
                evidence.append(f"'{term}' found {count}x in content")
        
        # Instrument match (high weight)
        for term in query_terms:
            for instr in doc.get('instrument', []):
                if term.lower() in str(instr).lower():
                    score += 5
                    evidence.append(f"Instrument match: {instr}")
        
        # Tag match
        for term in query_terms:
            for tag in doc.get('inferred_tags', []):
                if term.lower() in tag.lower():
                    score += 2
                    evidence.append(f"Tag match: {tag}")
        
        # Verification boost
        if doc.get('verification_status') == 'VERIFIED':
            score += 0.5
        
        if score >= 5:
            confidence = "exact"
        elif score >= 3:
            confidence = "high"
        elif score >= 1:
            confidence = "medium"
        else:
            confidence = "low"
        
        return confidence, evidence, score
    
    def deduplicate_catalog(self):
        """Comprehensive deduplication using DOI (case-insensitive) and checksum"""
        docs = self.catalog.get('documents', [])
        
        # Deduplicate by DOI
        seen_dois = set()
        unique_docs = []
        removed_by_doi = 0
        
        # Also track checksums
        seen_checksums = set()
        removed_by_checksum = 0
        
        # Also track title duplicates
        seen_titles = set()
        removed_by_title = 0
        
        for doc in docs:
            doi = doc.get('doi', '').lower()
            
            # Skip DOI duplicates
            if doi and doi in seen_dois:
                removed_by_doi += 1
                # Remove associated files
                self._cleanup_doc_files(doc)
                continue
            
            # Check checksum
            files = doc.get('files', {})
            pdf_file = files.get('full_text_pdf', '')
            if pdf_file:
                pdf_path = os.path.join(files.get('base_path', self.base_dir), pdf_file)
                if not os.path.exists(pdf_path):
                    pdf_path = os.path.join(self.base_dir, pdf_file)
                
                if os.path.exists(pdf_path):
                    try:
                        with open(pdf_path, 'rb') as f:
                            checksum = hashlib.md5(f.read()).hexdigest()
                        if checksum in seen_checksums:
                            removed_by_checksum += 1
                            self._cleanup_doc_files(doc)
                            if doi:
                                seen_dois.add(doi)
                            continue
                        seen_checksums.add(checksum)
                    except:
                        pass
            
            # Check title duplicates using Jaccard similarity (0.85 threshold)
            title_key = self._normalize_title(doc.get('title', ''))
            if title_key:
                if self._is_duplicate_title(doc.get('title', ''), list(seen_titles), threshold=0.85):
                    removed_by_title += 1
                    self._cleanup_doc_files(doc)
                    if doi:
                        seen_dois.add(doi)
                    continue
            
            # Add to unique
            if doi:
                seen_dois.add(doi)
            if title_key:
                seen_titles.add(title_key)
            unique_docs.append(doc)
        
        self.catalog['documents'] = unique_docs
        
        # Update stats
        self._update_stats()
        self.save_catalog()
        
        print(f"📊 Deduplication complete:")
        print(f"  Removed by DOI: {removed_by_doi}")
        print(f"  Removed by checksum: {removed_by_checksum}")
        print(f"  Removed by title: {removed_by_title}")
        print(f"  Remaining documents: {len(unique_docs)}")
    
    def _normalize_title(self, title):
        """Normalize title for comparison"""
        if not title:
            return ""
        normalized = re.sub(r'[^\w\s]', '', title.lower()).strip()
        normalized = re.sub(r'\s+', ' ', normalized)
        return normalized[:80]
    
    def _jaccard_similarity(self, a, b):
        """Calculate Jaccard similarity between two strings"""
        if not a or not b:
            return 0.0
        set_a = set(a.lower().split())
        set_b = set(b.lower().split())
        if not set_a or not set_b:
            return 0.0
        intersection = len(set_a.intersection(set_b))
        union = len(set_a.union(set_b))
        return intersection / union if union > 0 else 0.0
    
    def _is_duplicate_title(self, title, existing_titles, threshold=0.85):
        """Check if title is a near-duplicate of any existing title"""
        normalized = self._normalize_title(title)
        for existing in existing_titles:
            if self._jaccard_similarity(normalized, existing) >= threshold:
                return True
        return False
    
    def _cleanup_doc_files(self, doc):
        """Remove files associated with a document"""
        files = doc.get('files', {})
        base_path = files.get('base_path', self.base_dir)
        
        for key in ['full_text_pdf', 'extracted_text', 'full_text_file']:
            filename = files.get(key, '')
            if filename:
                path = os.path.join(base_path, filename)
                if not os.path.exists(path):
                    path = os.path.join(self.base_dir, filename)
                if os.path.exists(path):
                    try:
                        os.remove(path)
                    except:
                        pass
    
    def _update_stats(self):
        """Update catalog statistics"""
        docs = self.catalog.get('documents', [])
        
        by_domain = {}
        by_instrument = {}
        by_tag = {}
        by_year = {}
        
        verified_count = 0
        
        for doc in docs:
            # By domain
            domain = doc.get('domain', 'unknown')
            by_domain[domain] = by_domain.get(domain, 0) + 1
            
            # By instrument
            for instr in doc.get('instrument', []):
                if instr != "Not specified":
                    by_instrument[instr] = by_instrument.get(instr, 0) + 1
            
            # By tag
            for tag in doc.get('inferred_tags', []):
                by_tag[tag] = by_tag.get(tag, 0) + 1
            
            # By year
            year = doc.get('year', '')
            if year and year.isdigit():
                by_year[year] = by_year.get(year, 0) + 1
            
            # Verified count
            if doc.get('verification_status') == 'VERIFIED':
                verified_count += 1
        
        self.catalog['stats'] = {
            'by_domain': by_domain,
            'by_instrument': by_instrument,
            'by_tag': by_tag,
            'by_year': by_year
        }
        
        self.catalog['metadata']['total_documents'] = len(docs)
        self.catalog['metadata']['verified_dois'] = verified_count
        self.catalog['metadata']['domains'] = sorted(by_domain.keys())
    
    @staticmethod
    def _extract_official_keywords(text):
        """Best-effort extraction of the paper's explicit 'Keywords:' list from PDF text.
        Returns a list of keyword strings (empty if none found)."""
        if not text:
            return []
        # Common keyword-section markers
        for marker in ['keywords:', 'key words:', 'keyword list:', 'index terms:']:
            idx = text.lower().find(marker)
            if idx == -1:
                continue
            tail = text[idx + len(marker): idx + len(marker) + 400]
            # Stop at the next likely section heading / sentence boundary
            for stop in ['\n\n', 'abstract', 'introduction', 'intro', 'background',
                         'methods', 'methodology', 'method', 'results', 'findings',
                         'discussion', 'conclusion', 'conclusions', 'references',
                         'doi', '©', 'volume', 'issue', 'pp', 'pages', '1.']:
                si = tail.lower().find(stop)
                if si > 0:
                    tail = tail[:si]
                    break
            # Split on common separators
            parts = re.split(r'[;,\n]', tail)
            kws = [p.strip(' .:-').strip() for p in parts if p.strip(' .:-').strip()]
            kws = [k for k in kws if 2 <= len(k) <= 60][:15]
            if kws:
                return kws
        return []

    @staticmethod
    def _title_similarity(a, b):
        """Jaccard similarity of token sets (lowercased). Used for duplicate detection
        when a paper has no real DOI (local: ID)."""
        def toks(s):
            return set(re.findall(r'[a-z0-9]+', (s or '').lower()))
        ta, tb = toks(a), toks(b)
        if not ta or not tb:
            return 0.0
        return len(ta & tb) / len(ta | tb)

    def add_documents_from_folder(self, folder_path, domain="general", auto_verify=True):
        """Add all documents from a folder recursively"""
        folder_path = self._normalize_path(folder_path)
        
        if not os.path.exists(folder_path):
            print(f"❌ Folder not found: {folder_path}")
            return 0
        
        print(f"📁 Scanning: {folder_path}")
        
        added = 0
        skipped = 0
        verified = 0
        enhanced = 0
        
        for root, dirs, files in os.walk(folder_path):
            for filename in files:
                if not filename.lower().endswith(('.pdf', '.docx', '.doc', '.txt')):
                    continue
                
                # Skip index files
                if filename.lower() == 'index.pdf':
                    continue
                
                src_path = os.path.join(root, filename)
                
                try:
                    filesize = os.path.getsize(src_path)
                except:
                    continue
                
                print(f"\n📄 Processing: {filename[:50]}... ({filesize/1024:.1f} KB)")
                
                # Copy file first (never touch originals)
                safe_name = re.sub(r'[^\w\-\.]', '_', filename)
                dst = os.path.join(self.base_dir, f"{domain}_{safe_name}" if domain != "general" else safe_name)
                
                # Ensure unique filename
                counter = 0
                base_dst = dst
                while os.path.exists(dst):
                    counter += 1
                    name_part, ext = os.path.splitext(base_dst)
                    dst = f"{name_part}_{counter}{ext}"
                
                try:
                    shutil.copy2(src_path, dst)
                except Exception as e:
                    print(f"  ⚠️ Copy failed: {e}")
                    continue
                
                # Extract content
                if filename.lower().endswith('.pdf'):
                    extracted_text, abstract = self.extract_text_from_pdf(dst)
                    text_filename = os.path.basename(dst).replace('.pdf', '.txt')
                    text_path = os.path.join(self.base_dir, text_filename)
                    with open(text_path, 'w', encoding='utf-8') as tf:
                        tf.write(extracted_text)
                elif filename.lower().endswith('.txt'):
                    with open(dst, 'r', encoding='utf-8', errors='ignore') as f:
                        extracted_text = f.read()
                    abstract = ""
                    text_path = dst
                    text_filename = os.path.basename(dst)
                else:
                    extracted_text = ""
                    abstract = ""
                    text_path = None
                    text_filename = None
                
                # Extract DOI
                dois = []
                if extracted_text:
                    dois = self.extract_doi_from_text(extracted_text)[:1]
                
                doi = dois[0] if dois else f"local:{hashlib.md5(dst.encode()).hexdigest()[:8]}"
                
                # Check for duplicates (exact DOI)
                existing = self.check_doi_duplicate(doi)
                # FIX #3: for papers WITHOUT a real DOI (local: pseudo-ID, which is a
                # hash of the *path* not content), also do a title-similarity check so
                # the same paper under a different filename/path is caught.
                if not existing and doi.startswith('local:'):
                    src_title = os.path.splitext(filename)[0]
                    for d in self.catalog.get('documents', []):
                        if self._title_similarity(src_title, d.get('title', '')) >= 0.6:
                            existing = d
                            break
                if existing:
                    # FIX #4: staleness / re-scan. If the source file changed since this
                    # entry was added (mtime or size differs), re-extract + update instead
                    # of silently skipping — so corrected/OCR-fixed PDFs actually refresh.
                    changed = False
                    try:
                        if existing.get('file_size') and existing['file_size'] != filesize:
                            changed = True
                        if existing.get('file_mtime'):
                            cur_mtime = datetime.fromtimestamp(os.path.getmtime(src_path)).isoformat()
                            if existing['file_mtime'] != cur_mtime:
                                changed = True
                    except:
                        pass
                    if changed:
                        print(f"  ♻️ Source changed — re-scanning: {filename[:40]}")
                        # Remove old extracted text artifact if present
                        old_txt = existing.get('files', {}).get('extracted_text')
                        if old_txt:
                            try: os.remove(os.path.join(self.base_dir, old_txt))
                            except: pass
                        # Update in place: re-extract text + metadata onto the existing entry
                        instruments = self.identify_instruments(extracted_text)
                        population = self.identify_population(extracted_text, filename)
                        tags = self.infer_tags(extracted_text, instruments, population, domain)
                        existing['instrument'] = instruments
                        existing['population'] = population
                        existing['inferred_tags'] = tags
                        existing['official_keywords'] = self._extract_official_keywords(extracted_text)
                        existing['abstract'] = abstract
                        existing['files'] = {
                            'base_path': self.base_dir,
                            'full_text_pdf': os.path.basename(dst),
                            'extracted_text': text_filename
                        }
                        existing['file_mtime'] = datetime.fromtimestamp(os.path.getmtime(src_path)).isoformat() if os.path.exists(src_path) else existing.get('file_mtime','')
                        existing['file_size'] = filesize
                        existing['added_date'] = datetime.now().isoformat()
                        if doi.startswith('10.') and auto_verify:
                            vm = self.verify_doi_metadata(doi)
                            if vm.get('status') == 'VERIFIED':
                                existing['verified_at'] = vm.get('verified_at')
                                existing['verification_status'] = 'VERIFIED'
                        print(f"  ✅ Updated existing entry")
                        continue
                    print(f"  ⏭️ Duplicate skipped: {doi}")
                    # Remove copied file
                    try:
                        os.remove(dst)
                        if text_path and text_path != dst:
                            os.remove(text_path)
                    except:
                        pass
                    skipped += 1
                    continue
                
                # Extract metadata
                instruments = self.identify_instruments(extracted_text)
                population = self.identify_population(extracted_text, filename)
                tags = self.infer_tags(extracted_text, instruments, population, domain)
                
                official_keywords = self._extract_official_keywords(extracted_text)
                
                doc_entry = {
                    'doi': doi,
                    'title': os.path.splitext(filename)[0],
                    'abstract': abstract,
                    'authors': [],
                    'year': '',
                    'journal': 'Not specified',
                    'volume': '',
                    'issue': '',
                    'pages': '',
                    'instrument': instruments,
                    'population': population,
                    'inferred_tags': tags,
                    'official_keywords': official_keywords,
                    'scope_notes': '',
                    'domain': domain,
                    'verification_status': 'UNVERIFIED',
                    'verification_note': 'Pending Crossref verification',
                    'file_mtime': datetime.fromtimestamp(os.path.getmtime(src_path)).isoformat() if os.path.exists(src_path) else '',
                    'file_size': filesize,
                    'files': {
                        'base_path': self.base_dir,
                        'full_text_pdf': os.path.basename(dst),
                        'extracted_text': text_filename
                    },
                    'added_date': datetime.now().isoformat()
                }
                
                # Verify DOI via Crossref (if auto_verify)
                if doi.startswith('10.') and auto_verify:
                    print(f"  🔍 Verifying DOI with Crossref...")
                    verified_meta = self.verify_doi_metadata(doi)
                    if verified_meta.get('status') == 'VERIFIED':
                        doc_entry['title'] = verified_meta.get('title', doc_entry['title'])
                        doc_entry['authors'] = verified_meta.get('authors', [])
                        doc_entry['year'] = verified_meta.get('year', '')
                        doc_entry['journal'] = verified_meta.get('journal', 'Not specified')
                        doc_entry['volume'] = verified_meta.get('volume', '')
                        doc_entry['issue'] = verified_meta.get('issue', '')
                        doc_entry['pages'] = verified_meta.get('pages', '')
                        if verified_meta.get('abstract'):
                            doc_entry['abstract'] = verified_meta['abstract']
                        doc_entry['verification_status'] = 'VERIFIED'
                        doc_entry['verification_note'] = 'Crossref DOI resolved successfully'
                        # BUG FIX #1: persist verified_at so _is_recently_verified() works
                        # for freshly-ingested docs (otherwise they get re-verified on 1st search).
                        doc_entry['verified_at'] = verified_meta.get('verified_at')
                        verified += 1
                        enhanced += 1
                        print(f"  ✅ VERIFIED with Crossref metadata")
                    else:
                        doc_entry['verification_status'] = 'PARTIALLY_VERIFIED'
                        doc_entry['verification_note'] = verified_meta.get('note', 'DOI verification failed')
                        print(f"  ⚠️ {doc_entry['verification_note']}")
                
                self.catalog['documents'].append(doc_entry)
                added += 1
                
                print(f"  📥 Added: {doc_entry['title'][:40]}...")
                print(f"     DOI: {doi} | Status: {doc_entry['verification_status']}")
                print(f"     Domain: {domain} | Instruments: {instruments}")
        
        # Update stats
        self._update_stats()
        self.save_catalog()
        
        print(f"\n=== Import Complete ===")
        print(f"Added: {added} documents")
        print(f"Skipped (duplicates): {skipped}")
        print(f"DOI-verified: {verified}")
        print(f"Metadata enhanced: {enhanced}")
        return added
    
    def print_stats(self):
        """Print catalog statistics"""
        stats = self.catalog.get('stats', {})
        meta = self.catalog.get('metadata', {})
        
        print(f"=== Universal RAG System v4.4 ===")
        print(f"Documents: {meta.get('total_documents', 0)}")
        print(f"Verified DOIs: {meta.get('verified_dois', 0)}")
        print(f"Version: {meta.get('version', 'unknown')}")
        print(f"Last updated: {meta.get('last_updated', 'unknown')}")
        print()
        
        print("--- By Domain ---")
        for domain, count in sorted(stats.get('by_domain', {}).items(), key=lambda x: -x[1]):
            print(f"  {domain}: {count}")
        
        print("\n--- Top Tags ---")
        for tag, count in sorted(stats.get('by_tag', {}).items(), key=lambda x: -x[1])[:15]:
            print(f"  {tag}: {count}")
        
        print("\n--- By Year ---")
        for year, count in sorted(stats.get('by_year', {}).items()):
            print(f"  {year}: {count}")
        
        print(f"\nBackups: {len([f for f in os.listdir(self.backup_dir)]) if os.path.exists(self.backup_dir) else 0}")


def format_authors_apa(authors):
    """Format authors in APA 7th edition style"""
    if not authors:
        return "Author, A. A."
    
    formatted = []
    for author in authors:
        parts = str(author).strip().split()
        if len(parts) >= 2:
            last = parts[-1]
            first_parts = parts[:-1]
            # Build initials - each first name part becomes an initial
            initials_list = []
            for p in first_parts:
                if p and len(p) > 0 and p[0].isalpha():
                    initials_list.append(p[0].upper() + '.')
            initials = ' '.join(initials_list)
            formatted.append(f"{last}, {initials}")
        elif len(parts) == 1:
            formatted.append(parts[0])
        elif len(parts) == 0:
            formatted.append("Author, A. A.")
    
    if len(formatted) >= 2:
        if len(formatted) <= 20:
            if len(formatted) == 2:
                return f"{formatted[0]} & {formatted[1]}"
            else:
                return ', '.join(formatted[:-1]) + f", & {formatted[-1]}"
        else:
            return ', '.join(formatted[:19]) + f", & {formatted[-1]}"
    return formatted[0] if formatted else "Author, A. A."


def main():
    rag = UniversalRAG()
    
    parser = argparse.ArgumentParser(description="Universal RAG System v4.5")
    parser.add_argument('--search', '-s', type=str, help="Search query")
    parser.add_argument('--stats', action='store_true', help="Show statistics")
    parser.add_argument('--add-folder', type=str, help="Add documents from folder")
    parser.add_argument('--domain', action='append', type=str, help="Filter by domain")
    parser.add_argument('--tag', action='append', type=str, help="Filter by tag")
    parser.add_argument('--instrument', action='append', type=str, help="Filter by instrument")
    parser.add_argument('--max', type=int, default=20, help="Max results")
    parser.add_argument('--dedup', action='store_true', help="Run deduplication")
    parser.add_argument('--update', action='store_true', help="Update all metadata via Crossref")
    parser.add_argument('--debug', action='store_true', help="Show exclusion reasons for debugging")
    parser.add_argument('--no-expansion', action='store_true', help="Disable query expansion")
    parser.add_argument('--fulltext', action='store_true', help="Enable full-text body search (slower)")
    
    args = parser.parse_args()
    
    if args.stats:
        rag.print_stats()
    elif args.search:
        results = rag.search(
            query=args.search,
            max_results=args.max,
            domains=args.domain,
            tags=args.tag,
            instruments=args.instrument,
            fulltext_search=args.fulltext,
            debug=args.debug,
            use_expansion=not args.no_expansion
        )
        
        if results:
            # Show search trace
            trace = results[0].get('_search_trace', {})
            if trace:
                print(f"🔍 Search trace for '{args.search}':")
                if trace.get('expansion_used'):
                    print(f"  • Query expansion: +{len(trace.get('expansion_terms', []))} related terms")
                    if trace.get('expansion_terms'):
                        print(f"    Terms: {', '.join(trace['expansion_terms'][:8])}")
                else:
                    print(f"  • Query expansion: off (exact terms only)")
                if trace.get('deeper_search_triggered'):
                    print(f"  • Deeper full-text search: triggered")
                if trace.get('web_fallback_used'):
                    print(f"  • Web fallback: used ({trace.get('web_results_count', 0)} results)")
                else:
                    print(f"  • Web fallback: not needed")
                print()
            
            print(f"Found {len(results)} confirmed matches for '{args.search}'\n")
            for i, result in enumerate(results):
                authors = format_authors_apa(result['authors'])
                verif_badge = "✅" if result['verification_status'] == 'VERIFIED' else "📄"
                conf_badge = {"exact": "🎯", "high": "✅", "medium": "⚠️"}.get(result['confidence'], "❓")
                
                # Source indicator
                source_badge = "🌐" if result.get('source') == 'web_fallback' else "📁"
                match_badge = "🔍" if result.get('match_type') == 'expanded' else ""
                
                title_display = result['title'][:60] + "..." if len(result['title']) > 60 else result['title']
                print(f"  {i+1}. {source_badge} {conf_badge} {match_badge} {result['match_score']:.1f} | {result['doi']}")
                print(f"     {title_display}")
                if result['authors']:
                    print(f"      | Authors: {authors}")
                if result['journal'] and result['journal'] != 'Not specified':
                    print(f"      | Journal: {result['journal']}")
                print(f"      | Population: {result['population']}")
                if result['tags']:
                    print(f"      | Tags: {', '.join(result['tags'][:8])}")
                if result['evidence']:
                    print(f"      | Evidence: {', '.join(result['evidence'])}")
                print(f"      | {verif_badge} {result['verification_status']}")
                print()
        else:
            print(f"No confirmed matches found for '{args.search}'")
            print("💡 Web search recommended for new topics.")
            print("   (Run this search through the Hermes agent interface for web fallback)")
    elif args.add_folder:
        rag.add_documents_from_folder(args.add_folder, 'Mendeley Import')
    elif args.dedup:
        rag.deduplicate_catalog()
    elif args.update:
        print("Updating all metadata via Crossref...")
        updated = 0
        for doc in rag.catalog.get('documents', []):
            if doc.get('doi', '').startswith('10.'):
                doc = rag.enhance_metadata(doc)
                updated += 1
        rag._update_stats()
        rag.save_catalog()
        print(f"Updated {updated} documents")
    else:
        print("Universal RAG System v4.4")
        print("Usage: python3 universal_rag.py --stats")
        print("       python3 universal_rag.py --search 'query' --tag 'Malaysia'")
        print("       python3 universal_rag.py --add-folder '/path/to/papers'")
        print("       python3 universal_rag.py --dedup")
        print("       python3 universal_rag.py --update")


if __name__ == '__main__':
    main()