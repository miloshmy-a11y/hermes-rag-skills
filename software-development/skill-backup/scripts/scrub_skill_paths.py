"""Scrub machine-specific paths/usernames from a skill folder before publishing.

Usage:
    python3 scrub_skill_paths.py <src_skill_dir> <dst_staging_dir> [--user Milos] [--terms "Seri Manjung,Perak"]

Copies src -> dst, replaces known local paths with generic placeholders, swaps the
personal username token, strips a caller-supplied list of extra personal keywords
(e.g. your FYP location), neutralizes emails, and SKIPS .env / catalog / cache files.
Safe: never touches src. Works on Windows backslash paths because it uses Python
literal-string replace (sed fails on doubled backslashes in on-disk content).

After copying it scans the result and prints any surviving personal signal so you can
eyeball before pushing -- a generic path/username scrub will STILL leak location words
("Seri Manjung", "Perak") that are not part of C:\\Users\\Milos.
"""
import os, shutil, sys, argparse, re as _re

# IMPORTANT: on-disk skill content often stores paths with DOUBLE backslashes
# (e.g. 'C:\\Users\\Milos' = two literals), because the file was written by a process
# that escaped them. A plain single-backslash pair ('C:\\Users\\Milos') will NOT match
# the doubled form and silently leaks. Always include BOTH single- and double-backslash
# variants. (Missed this twice in practice -> leaked D:\\work paths to a public repo.)
DEFAULT_PAIRS = [
    (r"C:\Users\Milos\AppData\Local\hermes\cache\web\universal_rag", r"<HERMES_HOME>/cache/web/universal_rag"),
    (r"C:\\Users\\Milos\\AppData\\Local\\hermes\\cache\\web\\universal_rag", r"<HERMES_HOME>/cache/web/universal_rag"),
    (r"C:\Users\Milos\AppData\Local\hermes", r"<HERMES_HOME>"),
    (r"C:\\Users\\Milos\\AppData\\Local\\hermes", r"<HERMES_HOME>"),
    (r"C:\Users\Milos", r"<HOME>"),
    (r"C:\\Users\\Milos", r"<HOME>"),
    (r"D:\work\sayang\OUM\RESEARCH\bsc\pdf", r"<YOUR_WORK_FOLDER>/OUM"),
    (r"D:\\work\\sayang\\OUM\\RESEARCH\\bsc\\pdf", r"<YOUR_WORK_FOLDER>/OUM"),
    (r"D:\work", r"<YOUR_WORK_FOLDER>"),
    (r"D:\\work", r"<YOUR_WORK_FOLDER>"),
]
SKIP_DIRS = {".hub", "__pycache__", ".git"}
SKIP_FILES = {".env", "UNIVERSAL_CATALOG.json", ".usage.json", ".bundled_manifest"}
SKIP_EXT = {".pdf", ".png", ".jpg", ".zip", ".pyc"}
# Email-like patterns to neutralize (keep example.com placeholder)
_EMAIL = _re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
# Location / personal words that a generic scrub misses (extend per-user as needed)
_DEFAULT_PROBES = ("Seri Manjung", "Perak")

def scrub(src, dst, user, extra_terms=None):
    if os.path.exists(dst):
        shutil.rmtree(dst)
    shutil.copytree(src, dst)
    pairs = [p for p in DEFAULT_PAIRS]
    hit_report = []  # (relpath, sample) of any personal value that survived
    extra_terms = [t for t in (extra_terms or []) if t]
    if user not in [p[1] for p in pairs]:
        extra_terms.append(user)
    for dp, dirs, fns in os.walk(dst):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for fn in fns:
            if fn in SKIP_FILES or os.path.splitext(fn)[1] in SKIP_EXT:
                # remove secrets/catalogs rather than ship them
                try: os.remove(os.path.join(dp, fn))
                except OSError: pass
                continue
            if not fn.endswith((".md", ".py", ".txt", ".json")):
                continue
            p = os.path.join(dp, fn)
            try: s = open(p, encoding="utf-8").read()
            except Exception: continue
            for a, b in pairs: s = s.replace(a, b)
            for term in extra_terms:
                if term and term in s:
                    s = s.replace(term, "<USER>")
            s = _EMAIL.sub("<user>@example.com", s)
            # report any surviving personal signal so the caller can eyeball before push
            rel = os.path.relpath(p, dst)
            for probe in (user,) + tuple(extra_terms) + _DEFAULT_PROBES:
                if probe and probe in s:
                    idx = s.find(probe)
                    hit_report.append((rel, s[max(0, idx-30):idx+30].replace("\n", " ")))
            open(p, "w", encoding="utf-8").write(s)
    print(f"Scrubbed {src} -> {dst}")
    if hit_report:
        print("\nWARNING -- possible personal data still present after scrub:")
        for rel, snippet in hit_report:
            print(f"  {rel}: ...{snippet}...")
    else:
        print("No personal-path/username/location/email hits detected.")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("src"); ap.add_argument("dst")
    ap.add_argument("--user", default="Milos")
    ap.add_argument("--terms", help="comma-separated extra personal keywords to strip (e.g. 'Seri Manjung,Perak')")
    a = ap.parse_args()
    terms = [t.strip() for t in (a.terms or "").split(",") if t.strip()]
    scrub(a.src, a.dst, a.user, extra_terms=terms)
