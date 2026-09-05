#!/usr/bin/env python3
"""
verify_ipa_live.py — Automated Live Web IPA Verification Tool for Oxford Word Skills.

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
import gzip
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Set, Tuple

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
RESOURCES_DIR = os.path.join(PROJECT_ROOT, "Resources")
DEFINITIONS_JSON = os.path.join(RESOURCES_DIR, "definitions.json")
EXTRAWORDLIST_XML = os.path.join(RESOURCES_DIR, "extrawordlist.xml")

WIKTIONARY_API = "https://en.wiktionary.org/w/api.php"
USER_AGENT = (
    "OxfordWordSkillsLiveBot/1.0 "
    "(https://github.com/thanhqng1510/Oxford-word-skills; contact: dev@example.com) "
    "Python-urllib/3.12"
)
BATCH_SIZE = 50
RATE_LIMIT_DELAY = 0.35  # seconds between batch requests
MAX_RETRIES = 5

VALID_IPA_REGEX = re.compile(
    r"^/[a-zæɑɒɔəɛɜɪʊʌbcdefɡhijklmnŋpqrstuvwzðθʃʒˈˌːɹ\s\-\,\.\(\)\…\u2019\']+/$"
)
FORBIDDEN_SAMPA_REGEX = re.compile(r'[%&"”QVUITAODSZ23@ÍÙ]')

# ── Dialect Filtering ──────────────────────────────────────────────────────────

STANDARD_RP_KEYWORDS = ["rp", "received pronunciation", "ssb", "standard southern british"]
GENERIC_UK_KEYWORDS = ["uk", "british", "southern england", "southern british", "england", "non-rhotic"]
DISQUALIFY_KEYWORDS = [
    "ga", "genam", "general american", "us", "usa", "united states",
    "ca", "canada", "canadian", "au", "australia", "australian", "nz", "new zealand",
    "scotland", "scottish", "scots", "wales", "welsh", "ireland", "irish",
    "northumbria", "geordie", "aave", "flapping", "t-flapping", "archaic", "obsolete",
    "triphthong smoothing", "smoothing", "dialectal", "south asia", "indian", "pakistan",
    "mle", "dated", "rare"
]


def normalize_ipa(raw: str) -> str:
    """Normalizes phonetic transcription to clean British RP slash notation."""
    if not raw:
        return ""
    text = re.sub(r"<[^>]+>", "", raw).strip()
    if text.startswith("[") and text.endswith("]"):
        inner = text[1:-1]
    elif text.startswith("/") and text.endswith("/"):
        inner = text[1:-1]
    else:
        inner = text

    # Remove syllable dots and stress-tied characters
    inner = inner.replace(".", "")
    inner = inner.replace("ɹ", "r")
    inner = inner.replace("(ɹ)", "(r)")
    inner = inner.replace("͡", "").replace("͜", "")
    inner = re.sub(r"[\u0300-\u036f]", "", inner)  # strip combining diacritics
    inner = inner.replace("ɚ", "ə").replace("ɝ", "ɜː")
    inner = inner.replace("ɾ", "t")
    inner = inner.replace("ɛ", "e")
    inner = inner.replace("ɡ", "g")
    inner = inner.replace(":", "ː")
    inner = re.sub(r"\s+", " ", inner).strip()
    inner = re.sub(r"[ˈˌ]\s*(\.{3}|…)", r"\1", inner)

    return f"/{inner}/"


def extract_english_section(wikitext: str) -> str:
    if not wikitext:
        return ""
    m = re.search(r"==\s*English\s*==(.*?)(?=\n==[^=]|\Z)", wikitext, re.DOTALL | re.IGNORECASE)
    return m.group(1) if m else ""


def parse_wiktionary_rp_candidates(wikitext: str, headword: str = "") -> List[Tuple[str, int]]:
    """Extracts candidate British RP IPAs scored by dialect match."""
    eng_text = extract_english_section(wikitext)
    if not eng_text:
        return []

    candidates: List[Tuple[str, int]] = []
    lines = eng_text.splitlines()
    bullet_stack: Dict[int, str] = {}

    for line in lines:
        line_clean = line.strip()
        if not line_clean:
            continue

        b_match = re.match(r"^(\*+)", line_clean)
        level = len(b_match.group(1)) if b_match else 0

        accent_m = re.search(r"\{\{(?:a|accent)\|(?:en\|)?([^}]+)\}\}", line_clean, re.IGNORECASE)
        if accent_m:
            bullet_stack = {k: v for k, v in bullet_stack.items() if k < level}
            bullet_stack[level] = accent_m.group(1).lower()
        elif level > 0:
            bullet_stack = {k: v for k, v in bullet_stack.items() if k <= level}
        else:
            bullet_stack = {}

        current_bullet_accent = " ".join(bullet_stack.values())

        for ipa_m in re.finditer(r"\{\{IPA\|en\|([^}]+)\}\}", line_clean):
            args = ipa_m.group(1).split("|")
            transcriptions = []
            local_accents = []

            for arg in args:
                arg = arg.strip()
                if not arg:
                    continue
                if "=" in arg:
                    k, v = arg.split("=", 1)
                    k = k.strip().lower()
                    v = v.strip().lower()
                    if re.match(r"^(a|aa|q|qq)\d*$", k) or k in ("qual", "qualifier"):
                        local_accents.append(v)
                elif arg.startswith("/") or arg.startswith("["):
                    transcriptions.append(arg)

            local_accents_str = " ".join(local_accents).lower()
            all_accents_str = f"{local_accents_str} {current_bullet_accent}".strip().lower()

            has_rp = any(re.search(r"\b" + re.escape(k) + r"\b", all_accents_str) for k in STANDARD_RP_KEYWORDS)
            has_uk = any(re.search(r"\b" + re.escape(k) + r"\b", all_accents_str) for k in GENERIC_UK_KEYWORDS)
            has_disqualify = any(re.search(r"\b" + re.escape(k) + r"\b", all_accents_str) for k in DISQUALIFY_KEYWORDS)

            score = 10
            if has_rp and not has_disqualify:
                score = 100
            elif has_uk and not has_disqualify:
                score = 90
            elif (has_rp or has_uk) and has_disqualify:
                score = -100
            elif has_disqualify:
                score = -100

            for trans in transcriptions:
                norm = normalize_ipa(trans)
                if not norm or not VALID_IPA_REGEX.match(norm) or FORBIDDEN_SAMPA_REGEX.search(norm):
                    continue
                candidates.append((norm, score))

    return candidates


def fetch_live_wiktionary_pages(titles: List[str], verbose: bool = False) -> Dict[str, Optional[str]]:
    """Fetches wikitext directly from live Wiktionary in batches over HTTPS."""
    unique_titles = sorted(list(set(titles)))
    batches = [unique_titles[i:i + BATCH_SIZE] for i in range(0, len(unique_titles), BATCH_SIZE)]
    pages_result: Dict[str, Optional[str]] = {}

    if verbose:
        print(f"Querying Wiktionary live for {len(unique_titles)} titles in {len(batches)} batches...")

    for idx, batch in enumerate(batches):
        params = {
            "action": "query",
            "titles": "|".join(batch),
            "prop": "revisions",
            "rvslots": "main",
            "rvprop": "content",
            "format": "json",
            "formatversion": "2",
            "redirects": "1",
        }
        url = f"{WIKTIONARY_API}?{urllib.parse.urlencode(params)}"
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": USER_AGENT,
                "Accept-Encoding": "gzip",
            },
        )

        for attempt in range(MAX_RETRIES):
            try:
                with urllib.request.urlopen(req, timeout=20) as resp:
                    raw_data = resp.read()
                    if resp.headers.get("Content-Encoding") == "gzip" or raw_data.startswith(b"\x1f\x8b"):
                        raw_data = gzip.decompress(raw_data)
                    data = json.loads(raw_data.decode("utf-8", errors="replace"))

                    query_data = data.get("query", {})
                    norm_map = {}
                    for n in query_data.get("normalized", []):
                        norm_map[n.get("to")] = n.get("from")
                    for r in query_data.get("redirects", []):
                        to_t = r.get("to")
                        from_t = r.get("from")
                        norm_map[to_t] = norm_map.get(from_t, from_t)

                    for p in query_data.get("pages", []):
                        title = p.get("title", "")
                        orig_title = norm_map.get(title, title)
                        if p.get("missing"):
                            pages_result[orig_title] = None
                            pages_result[title] = None
                        else:
                            revs = p.get("revisions", [])
                            content = revs[0].get("slots", {}).get("main", {}).get("content", "") if revs else ""
                            pages_result[orig_title] = content
                            pages_result[title] = content

                    for t in batch:
                        if t not in pages_result:
                            pages_result[t] = None

                    break
            except urllib.error.HTTPError as e:
                if e.code in (429, 503):
                    delay = (attempt + 1) * 2
                    time.sleep(delay)
                else:
                    break
            except Exception:
                time.sleep(1)

        time.sleep(RATE_LIMIT_DELAY)
        if verbose and ((idx + 1) % 10 == 0 or idx == len(batches) - 1):
            print(f"  Live query progress: batch {idx + 1}/{len(batches)} completed")

    return pages_result


UNIT_MEASUREMENTS = {
    "cl (centilitre(s))": "centilitre",
    "cm (centimetre(s))": "centimetre",
    "ct (cent(s))": "cent",
    "c (cent(s))": "cent",
    "gm (gram(s))": "gram",
    "g (gram(s))": "gram",
    "kg (kilo(s)/kilogram(s))": "kilogram",
    "kph (kilometres per hour)": "kph",
    "km (kilometre(s))": "kilometre",
    "l (litre)": "litre",
    "ml (millilitre(s))": "millilitre",
    "mm (millimetre(s))": "millimetre",
    "mph (miles per hour)": "mph",
    "p (pence)": "pence",
    "t (tonne)": "tonne",
}


def clean_query_title(headword: str) -> str:
    """Extracts canonical lookup word from curriculum headword."""
    w = headword.strip()
    if w in UNIT_MEASUREMENTS:
        return UNIT_MEASUREMENTS[w]
    m = re.match(r"^([A-Z0-9]+)\s*\(.+\)$", w)
    if m:
        return m.group(1).strip()
    if "(s)" in w:
        return w.replace("(s)", "").strip()
    if "(" in w:
        base = w.split("(")[0].strip()
        if base:
            return base
    if w.endswith(" N") or w.endswith(" V"):
        return w[:-2].strip()
    w = re.sub(r"\.{3}|…", "", w).strip()
    return w


def phonetically_equivalent(ipa1: str, ipa2: str) -> bool:
    """Checks if two IPAs are equivalent variants of standard British RP."""
    if ipa1 == ipa2:
        return True

    def simplify(s: str) -> str:
        s = s.strip("/").lower()
        # Remove optional suffix notation like (s) or (z)
        s = re.sub(r"\([sz]\)", "", s)
        # Remove stresses, syllable breaks, spaces, parens, optional markers
        s = re.sub(r"[ˈˌ\s\(\)]", "", s)
        # Rhoticity and length marks
        s = s.replace("(r)", "").replace("r", "")
        s = s.replace("ː", "")
        # Optional yod
        s = s.replace("(j)", "").replace("j", "")
        # Syllabic consonants vs schwa + consonant
        s = s.replace("ʃən", "ʃn")
        s = s.replace("fəl", "fl")
        s = s.replace("bəl", "bl")
        s = s.replace("təl", "tl")
        s = s.replace("dəl", "dl")
        s = s.replace("məl", "ml")
        s = s.replace("səl", "sl")
        s = s.replace("zəl", "zl")
        s = s.replace("vəl", "vl")
        # Square diphthong variants (eə vs ɛː)
        s = s.replace("eə", "e")
        return s

    return simplify(ipa1) == simplify(ipa2)


def run_live_verification(
    words: Optional[List[str]] = None,
    fix: bool = False,
    verbose: bool = False,
    quiet: bool = False,
) -> Dict[str, any]:
    """Executes live verification against en.wiktionary.org and returns audit results."""
    with open(DEFINITIONS_JSON, "r", encoding="utf-8") as f:
        defs_dict = json.load(f)

    target_words = words if words else sorted(list(defs_dict.keys()))
    if not quiet:
        print(f"Starting live web verification for {len(target_words)} words against en.wiktionary.org...")

    # Build query titles
    query_titles = [clean_query_title(w) for w in target_words]
    pages_map = fetch_live_wiktionary_pages(query_titles, verbose=(verbose and not quiet))

    exact_matches = []
    equivalent_matches = []
    discrepancies = []
    not_on_wiktionary = []

    fixes_to_apply: Dict[str, str] = {}

    for word in target_words:
        current_ipa = defs_dict[word].get("phonetic", "")
        title = clean_query_title(word)
        wikitext = pages_map.get(title)

        if not wikitext:
            not_on_wiktionary.append((word, current_ipa))
            continue

        candidates = parse_wiktionary_rp_candidates(wikitext, headword=word)
        valid_candidates = [c for c in candidates if c[1] >= 10]

        if not valid_candidates:
            not_on_wiktionary.append((word, current_ipa))
            continue

        # Sort by score descending
        valid_candidates.sort(key=lambda c: c[1], reverse=True)
        web_rp_ipas = [c[0] for c in valid_candidates]
        best_web_ipa = web_rp_ipas[0]

        # Handle homographs: "record N" vs "record V"
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
        # Apply to definitions.json
        for w, ipa in fixes_to_apply.items():
            if w in defs_dict:
                defs_dict[w]["phonetic"] = ipa
        with open(DEFINITIONS_JSON, "w", encoding="utf-8") as f:
            json.dump(defs_dict, f, ensure_ascii=False, indent=2)
            f.write("\n")

        # Apply to extrawordlist.xml
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

    # Exit code: 0 if no unhandled discrepancies, 1 if discrepancies exist without --fix
    if results["discrepancies"] and not args.fix:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
