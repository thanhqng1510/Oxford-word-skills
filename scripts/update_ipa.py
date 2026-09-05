#!/usr/bin/env python3
"""
update_ipa.py — Fetch and apply IPA updates for new or missing words using wiktionary_ipa library.

Use this when new vocabulary is added to extrawordlist.xml or definitions.json
and you need to fetch their verified British RP IPA from Wiktionary live.

Usage:
    python3 scripts/update_ipa.py                      # fetch + apply all missing
    python3 scripts/update_ipa.py --dry-run            # report only, no writes
    python3 scripts/update_ipa.py --word "ameliorate"  # single word
"""

import argparse
import json
import os
import sys
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional

from ipa_storage import (
    DEFINITIONS_JSON,
    EXTRAWORDLIST_XML,
    ensure_wiktionary_ipa,
    save_vocabulary_fixes,
)

wipa = ensure_wiktionary_ipa()


def find_missing_words() -> List[str]:
    """Finds words in definitions.json or extrawordlist.xml that lack valid slash-enclosed IPA."""
    missing = set()

    if os.path.isfile(DEFINITIONS_JSON):
        with open(DEFINITIONS_JSON, "r", encoding="utf-8") as f:
            defs = json.load(f)
        for w, entry in defs.items():
            p = entry.get("phonetic", "").strip()
            if not p or not (p.startswith("/") and p.endswith("/")):
                missing.add(w)

    if os.path.isfile(EXTRAWORDLIST_XML):
        tree = ET.parse(EXTRAWORDLIST_XML)
        for elem in tree.findall(".//word"):
            w = elem.attrib.get("str", "").strip()
            ipa_elem = elem.find("ipa")
            p = ipa_elem.text.strip() if (ipa_elem is not None and ipa_elem.text) else ""
            if not p or not (p.startswith("/") and p.endswith("/")):
                missing.add(w)

    return sorted(list(missing))


def main():
    parser = argparse.ArgumentParser(description="Fetch and apply British RP IPA updates from Wiktionary.")
    parser.add_argument("--word", help="Single word to look up and apply")
    parser.add_argument("--dry-run", action="store_true", help="Report only, do not write files")
    args = parser.parse_args()

    words_to_update = [args.word] if args.word else find_missing_words()

    if not words_to_update:
        print("✓ All vocabulary entries already have valid IPA pronunciations.")
        sys.exit(0)

    print(f"Fetching IPA for {len(words_to_update)} words live from Wiktionary (batched)...")
    results = wipa.batch_lookup(words_to_update)

    fixes_to_apply: Dict[str, str] = {}
    for w in words_to_update:
        ipa = results.get(w)
        if ipa:
            print(f"  {w:30s} -> {ipa}")
            fixes_to_apply[w] = ipa
        else:
            print(f"  {w:30s} -> [NOT FOUND on Wiktionary]")

    if args.dry_run:
        print(f"\n[DRY-RUN] Would update {len(fixes_to_apply)} words.")
    elif fixes_to_apply:
        defs_count, xml_count = save_vocabulary_fixes(fixes_to_apply)
        print(f"\n✓ Updated {defs_count} in definitions.json, {xml_count} in extrawordlist.xml")

        print("\nValidating changes with check_ipa...")
        from check_ipa import Report, audit_definitions_json, audit_extrawordlist_xml, print_report
        report = Report()
        audit_definitions_json(report)
        audit_extrawordlist_xml(report)
        print_report(report, verbose=False)
        if not report.ok:
            sys.exit(1)


if __name__ == "__main__":
    main()
