#!/usr/bin/env python3
"""
verify_ipa_live.py — Automated Live Web IPA Verification Tool for Oxford Word Skills.
Powered by the dedicated `wiktionary_ipa` library.

Queries en.wiktionary.org live (via MediaWiki Action API in batches of 50)
and compares every vocabulary item in the app against live British English (RP)
pronunciations on the web. No local cache required.

Usage:
    python3 scripts/verify_ipa_live.py                  # Full live web audit
    python3 scripts/verify_ipa_live.py --word "abbreviation" # Single word live check
    python3 scripts/verify_ipa_live.py --fix            # Live audit & auto-fix discrepancies
    python3 scripts/verify_ipa_live.py --verbose        # Show detailed discrepancy analysis
    python3 scripts/verify_ipa_live.py --json           # Machine-readable JSON output for CI
"""

import argparse
import json
import os
import sys
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
LIB_DIR = os.path.join(PROJECT_ROOT, "packages", "wiktionary_ipa")
if LIB_DIR not in sys.path:
    sys.path.insert(0, LIB_DIR)

from wiktionary_ipa import (
    WiktionaryClient,
    clean_lookup_title,
    parse_wiktionary_rp_candidates,
    phonetically_equivalent,
)

RESOURCES_DIR = os.path.join(PROJECT_ROOT, "Resources")
DEFINITIONS_JSON = os.path.join(RESOURCES_DIR, "definitions.json")
EXTRAWORDLIST_XML = os.path.join(RESOURCES_DIR, "extrawordlist.xml")


def run_live_verification(
    words: Optional[List[str]] = None,
    fix: bool = False,
    verbose: bool = False,
    quiet: bool = False,
) -> Dict[str, any]:
    """Executes live verification against en.wiktionary.org using the wiktionary_ipa library."""
    with open(DEFINITIONS_JSON, "r", encoding="utf-8") as f:
        defs_dict = json.load(f)

    target_words = words if words else sorted(list(defs_dict.keys()))
    if not quiet:
        print(f"Starting live web verification for {len(target_words)} words against en.wiktionary.org...")

    client = WiktionaryClient()
    query_titles = [clean_lookup_title(w) for w in target_words]
    pages_map = client.fetch_all(query_titles, verbose=(verbose and not quiet))

    exact_matches = []
    equivalent_matches = []
    discrepancies = []
    not_on_wiktionary = []
    fixes_to_apply: Dict[str, str] = {}

    for word in target_words:
        current_ipa = defs_dict[word].get("phonetic", "")
        title = clean_lookup_title(word)
        wikitext = pages_map.get(title)

        if not wikitext:
            not_on_wiktionary.append((word, current_ipa))
            continue

        candidates = parse_wiktionary_rp_candidates(wikitext, headword=word)
        valid_candidates = [c for c in candidates if c[1] >= 10]

        if not valid_candidates:
            not_on_wiktionary.append((word, current_ipa))
            continue

        valid_candidates.sort(key=lambda c: c[1], reverse=True)
        web_rp_ipas = [c[0] for c in valid_candidates]
        best_web_ipa = web_rp_ipas[0]

        # Handle homographs
        if word.endswith(" N") and any(c.startswith("/ˈ") for c in web_rp_ipas):
            best_web_ipa = next(c for c in web_rp_ipas if c.startswith("/ˈ"))
        elif word.endswith(" V") and any(not c.startswith("/ˈ") and "ˈ" in c for c in web_rp_ipas):
            best_web_ipa = next(c for c in web_rp_ipas if not c.startswith("/ˈ") and "ˈ" in c)

        if current_ipa == best_web_ipa or current_ipa in web_rp_ipas:
            exact_matches.append((word, current_ipa))
        elif any(phonetically_equivalent(current_ipa, c) for c in web_rp_ipas):
            equivalent_matches.append((word, current_ipa, best_web_ipa))
        else:
            discrepancies.append({
                "word": word,
                "current_ipa": current_ipa,
                "web_ipa": best_web_ipa,
                "all_web_ipas": web_rp_ipas[:3]
            })
            if fix:
                fixes_to_apply[word] = best_web_ipa

    if not quiet:
        print("\n" + "=" * 60)
        print("LIVE WEB VERIFICATION RESULTS (en.wiktionary.org)")
        print("=" * 60)
        print(f"Total Words Checked    : {len(target_words)}")
        print(f"Exact Matches on Web   : {len(exact_matches)}")
        print(f"Phonetic Equivalents   : {len(equivalent_matches)}")
        print(f"Discrepancies on Web   : {len(discrepancies)}")
        print(f"Not Directly on Web    : {len(not_on_wiktionary)} (phrases/idioms/compounds)")
        print("=" * 60)

        if discrepancies and verbose:
            print("\nDiscrepancies found:")
            for d in discrepancies:
                print(f"  {d['word']:25s} | Current: {d['current_ipa']:20s} | Web Wiktionary: {d['web_ipa']:20s}")

    if fix and fixes_to_apply:
        if not quiet:
            print(f"\nApplying {len(fixes_to_apply)} live fixes to definitions.json and extrawordlist.xml...")
        for w, ipa in fixes_to_apply.items():
            if w in defs_dict:
                defs_dict[w]["phonetic"] = ipa
        with open(DEFINITIONS_JSON, "w", encoding="utf-8") as f:
            json.dump(defs_dict, f, ensure_ascii=False, indent=2)
            f.write("\n")

        tree = ET.parse(EXTRAWORDLIST_XML)
        root = tree.getroot()
        xml_fixes = 0
        for elem in root.findall(".//word"):
            w_str = elem.attrib.get("str", "").strip()
            if w_str in fixes_to_apply:
                ipa_elem = elem.find("ipa")
                if ipa_elem is not None:
                    ipa_elem.text = fixes_to_apply[w_str]
                    xml_fixes += 1
        xml_bytes = ET.tostring(root, encoding="unicode", xml_declaration=False)
        with open(EXTRAWORDLIST_XML, "w", encoding="utf-8") as f:
            f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
            f.write("<!-- Use this encoding for xml files with ipa -->\n")
            f.write(xml_bytes)
            f.write("\n")
        if not quiet:
            print(f"✓ Updated {len(fixes_to_apply)} in definitions.json, {xml_fixes} in extrawordlist.xml")

    return {
        "total": len(target_words),
        "exact_matches": len(exact_matches),
        "equivalent_matches": len(equivalent_matches),
        "discrepancies": discrepancies,
        "not_on_wiktionary": len(not_on_wiktionary),
    }


def main():
    parser = argparse.ArgumentParser(description="Verify IPA against live English Wiktionary web API.")
    parser.add_argument("--word", help="Verify a single word live")
    parser.add_argument("--fix", action="store_true", help="Apply live web fixes to data stores")
    parser.add_argument("--verbose", "-v", action="store_true", help="Detailed output")
    parser.add_argument("--json", action="store_true", help="JSON output")
    args = parser.parse_args()

    words = [args.word] if args.word else None
    results = run_live_verification(words=words, fix=args.fix, verbose=args.verbose, quiet=args.json)

    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))

    if results["discrepancies"] and not args.fix:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
