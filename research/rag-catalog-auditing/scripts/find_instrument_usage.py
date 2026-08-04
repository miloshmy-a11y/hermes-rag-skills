#!/usr/bin/env python3
"""find_instrument_usage.py — deep full-text scan for an instrument in UNIVERSAL_CATALOG.json.

Reports ADMINISTERED (study used the instrument as a tool) vs CITED-ONLY mentions, so you
never exclude a genuine user (keyword/title-only search drops body-only mentions) and never
over-count a study that merely cites the instrument.

USAGE:
  python find_instrument_usage.py --instrument "expanded nursing stress scale|enss"
  python find_instrument_usage.py --instrument "nursing stress scale|nss" --catalog <PATH>

Prints two lists of DOIs + a short table of administered studies (author, year, title, country).
Read-only: never mutates the catalog.
"""
import json, os, re, argparse, sys

DEFAULT_CAT = r"C:\Users\Milos\AppData\Local\hermes\cache\web\universal_rag\UNIVERSAL_CATALOG.json"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--instrument", required=True,
                    help="regex for the instrument name, e.g. 'expanded nursing stress scale|enss'")
    ap.add_argument("--catalog", default=DEFAULT_CAT)
    ap.add_argument("--include-local", action="store_true",
                    help="also scan local: working/thesis docs (default: skip them)")
    args = ap.parse_args()

    if not os.path.exists(args.catalog):
        print(f"CATALOG NOT FOUND: {args.catalog}", file=sys.stderr); sys.exit(1)
    docs = json.loads(open(args.catalog, encoding="utf-8").read())["documents"]
    INSTR = args.instrument

    adm, cited = [], []
    for d in docs:
        doi = d.get("doi", "")
        if not args.include_local and doi.startswith("local:"):
            continue
        p = (d.get("files") or {}).get("extracted_text")
        if not p or not os.path.exists(p):
            continue
        t = open(p, encoding="utf-8", errors="ignore").read().lower()
        if not re.search(INSTR, t):
            continue
        used = re.search(
            r"(administered|used|collected|measured|assessed|employ|utili[sz]ed|completed).{0,40}(" + INSTR + r")", t
        ) or re.search(
            r"(" + INSTR + r").{0,40}(was (used|administered)|to measure|questionnaire|instrument)", t
        )
        (adm if used else cited).append(d)

    print(f"\nINSTRUMENT REGEX: {INSTR}")
    print(f"Records scanned (non-local): {sum(1 for d in docs if not d.get('doi','').startswith('local:'))}")
    print(f"\n=== ADMINISTERED (genuine users) : {len(adm)} ===")
    for d in adm:
        print(f"  {d.get('authors')} ({d.get('year')}) | {d.get('title')} | {d.get('country')}")
        print(f"     {d.get('doi')}")
    print(f"\n=== CITED-ONLY (exclude from 'studies that used it'): {len(cited)} ===")
    for d in cited:
        print(f"  {d.get('doi')} | {d.get('title','')[:50]}")


if __name__ == "__main__":
    main()
