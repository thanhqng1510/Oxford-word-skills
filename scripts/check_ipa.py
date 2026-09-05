#!/usr/bin/env python3
"""
check_ipa.py — Fast local IPA audit tool for Oxford Word Skills.

Validates all IPA entries in both data stores WITHOUT hitting the network.
Runs in < 1 second. Use this for routine CI checks and pre-commit validation.

Usage:
    python3 scripts/check_ipa.py              # summary report
    python3 scripts/check_ipa.py --verbose    # list every problem
    python3 scripts/check_ipa.py --json       # machine-readable JSON report
    python3 scripts/check_ipa.py --words      # list all words with their IPA
"""
import argparse
import json
import os
import re
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import List, Optional

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
RESOURCES_DIR = os.path.join(PROJECT_ROOT, "Resources")
DEFINITIONS_JSON = os.path.join(RESOURCES_DIR, "definitions.json")
EXTRAWORDLIST_XML = os.path.join(RESOURCES_DIR, "extrawordlist.xml")

# Add packages/wiktionary_ipa to sys.path
sys.path.insert(0, os.path.join(PROJECT_ROOT, "packages", "wiktionary_ipa"))
from wiktionary_ipa.dialects import FORBIDDEN_SAMPA_REGEX as SAMPA_TOKENS, VALID_IPA_REGEX as VALID_IPA_CHARS

# American-English-specific phonemes that should not appear in RP
# (ɚ = rhotic schwa, ɝ = rhotic mid-central, ɾ = tap/flap)
NON_RP_TOKENS = re.compile(r"[ɚɝɾ]")

# Detect obviously unconverted CDATA SAMPA (a legacy artefact)
RAW_SAMPA_ENTRY = re.compile(r'[%"&][a-z]')


@dataclass
class Issue:
    word: str
    source: str  # "defs" or "xml"
    kind: str    # "missing", "bad_format", "sampa", "non_rp"
    value: str


@dataclass
class Report:
    total_defs: int = 0
    total_xml: int = 0
    issues: List[Issue] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return len(self.issues) == 0

    def by_kind(self, kind: str) -> List[Issue]:
        return [i for i in self.issues if i.kind == kind]


# ── Audit Functions ───────────────────────────────────────────────────────────

def audit_definitions_json(report: Report):
    with open(DEFINITIONS_JSON, encoding="utf-8") as f:
        defs = json.load(f)
    report.total_defs = len(defs)
    for word, entry in defs.items():
        ipa = entry.get("phonetic", "")
        if not ipa:
            report.issues.append(Issue(word, "defs", "missing", ipa))
        elif not ipa.startswith("/") or not ipa.endswith("/"):
            report.issues.append(Issue(word, "defs", "bad_format", ipa))
        elif SAMPA_TOKENS.search(ipa):
            report.issues.append(Issue(word, "defs", "sampa", ipa))
        elif NON_RP_TOKENS.search(ipa):
            report.issues.append(Issue(word, "defs", "non_rp", ipa))
        elif not VALID_IPA_CHARS.match(ipa):
            report.issues.append(Issue(word, "defs", "bad_format", ipa))


def audit_extrawordlist_xml(report: Report):
    tree = ET.parse(EXTRAWORDLIST_XML)
    root = tree.getroot()
    for elem in root.findall(".//word"):
        word = elem.attrib.get("str", "").strip()
        ipa_elem = elem.find("ipa")
        ipa = (ipa_elem.text or "").strip() if ipa_elem is not None else ""
        report.total_xml += 1
        if not ipa:
            report.issues.append(Issue(word, "xml", "missing", ipa))
        elif not ipa.startswith("/") or not ipa.endswith("/"):
            # Check if it looks like unconverted SAMPA
            if RAW_SAMPA_ENTRY.search(ipa) or SAMPA_TOKENS.search(ipa):
                report.issues.append(Issue(word, "xml", "sampa", ipa))
            else:
                report.issues.append(Issue(word, "xml", "bad_format", ipa))
        elif SAMPA_TOKENS.search(ipa):
            report.issues.append(Issue(word, "xml", "sampa", ipa))
        elif NON_RP_TOKENS.search(ipa):
            report.issues.append(Issue(word, "xml", "non_rp", ipa))


# ── Output Helpers ────────────────────────────────────────────────────────────

GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BOLD = "\033[1m"
RESET = "\033[0m"

KIND_LABEL = {
    "missing": "MISSING",
    "bad_format": "BAD FORMAT",
    "sampa": "SAMPA RESIDUE",
    "non_rp": "NON-RP PHONEME",
}


def print_report(report: Report, verbose: bool):
    total = report.total_defs + report.total_xml
    print(f"\n{BOLD}Oxford Word Skills — IPA Audit{RESET}")
    print(f"  definitions.json : {report.total_defs} entries")
    print(f"  extrawordlist.xml: {report.total_xml} entries")
    print(f"  Total            : {total} entries\n")

    if report.ok:
        print(f"{GREEN}{BOLD}  ✓ ALL {total} ENTRIES VALID — 0 issues found.{RESET}\n")
        return

    by_kind: dict[str, List[Issue]] = {}
    for i in report.issues:
        by_kind.setdefault(i.kind, []).append(i)

    print(f"{RED}{BOLD}  ✗ {len(report.issues)} ISSUE(S) FOUND:{RESET}")
    for kind, label in KIND_LABEL.items():
        items = by_kind.get(kind, [])
        if items:
            print(f"    {label}: {len(items)}")
    print()

    if verbose:
        for kind, label in KIND_LABEL.items():
            items = by_kind.get(kind, [])
            if not items:
                continue
            print(f"{YELLOW}{BOLD}  {label} ({len(items)}):{RESET}")
            for issue in items:
                print(f"    [{issue.source}] {issue.word!r:50s} → {issue.value!r}")
            print()


def list_all_words(report: Report):
    """Print a TSV of all words and their current IPA from definitions.json."""
    with open(DEFINITIONS_JSON, encoding="utf-8") as f:
        defs = json.load(f)
    for word, entry in sorted(defs.items()):
        ipa = entry.get("phonetic", "")
        status = "OK" if (ipa.startswith("/") and ipa.endswith("/") and not SAMPA_TOKENS.search(ipa)) else "ISSUE"
        print(f"{status}\t{word}\t{ipa}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Fast local IPA audit — no network required."
    )
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Print every problematic entry.")
    parser.add_argument("--json", action="store_true",
                        help="Output machine-readable JSON report.")
    parser.add_argument("--words", action="store_true",
                        help="List all words and their current IPA as TSV.")
    args = parser.parse_args()

    if args.words:
        list_all_words(Report())
        return

    report = Report()
    audit_definitions_json(report)
    audit_extrawordlist_xml(report)

    if args.json:
        out = {
            "ok": report.ok,
            "total_defs": report.total_defs,
            "total_xml": report.total_xml,
            "issue_count": len(report.issues),
            "issues": [
                {"word": i.word, "source": i.source, "kind": i.kind, "value": i.value}
                for i in report.issues
            ],
        }
        print(json.dumps(out, ensure_ascii=False, indent=2))
    else:
        print_report(report, verbose=args.verbose)

    sys.exit(0 if report.ok else 1)


if __name__ == "__main__":
    main()
