#!/usr/bin/env python3
"""
update_ipa.py — Fetch and apply IPA updates for new or missing words.

Use this when new vocabulary is added to extrawordlist.xml or
definitions.json and you need to enrich their IPA from Wiktionary.

It ONLY fetches words that are genuinely new (not in the local cache),
so re-running is fast and idempotent. It then applies updates to both
data stores and validates the result.

Usage:
    python3 scripts/update_ipa.py              # fetch + apply all missing
    python3 scripts/update_ipa.py --dry-run    # report only, no writes
    python3 scripts/update_ipa.py --word "ameliorate"   # single word
    python3 scripts/update_ipa.py --force      # re-fetch even if cached
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Set

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
RESOURCES_DIR = os.path.join(PROJECT_ROOT, "Resources")
DEFINITIONS_JSON = os.path.join(RESOURCES_DIR, "definitions.json")
EXTRAWORDLIST_XML = os.path.join(RESOURCES_DIR, "extrawordlist.xml")
AUDIT_MAP_PATH = os.path.join(PROJECT_ROOT, ".agents",
                              "teamwork_preview_worker_m1_1", "audited_ipa_map.json")
CACHE_PATH = os.path.join(SCRIPT_DIR, "cache", "wiktionary_cache.json")
AUDIT_SCRIPT = os.path.join(SCRIPT_DIR, "audit_wiktionary_ipa.py")

WIKTIONARY_API = "https://en.wiktionary.org/w/api.php"
USER_AGENT = (
    "OxfordWordSkillsIPABot/1.0 "
    "(https://github.com/thanhqng/OxfordWordSkills) Python-urllib/3.12"
)
REQUEST_INTERVAL = 1.0
MAX_RETRIES = 4

# ── Helpers (minimal RP extraction — delegates heavy logic to audit_wiktionary_ipa.py) ──

def _fetch_wikitext(title: str) -> Optional[str]:
    params = urllib.parse.urlencode({
        "action": "query",
        "titles": title,
        "prop": "revisions",
        "rvprop": "content",
        "format": "json",
        "formatversion": "2",
    })
    url = f"{WIKTIONARY_API}?{params}"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    for attempt in range(MAX_RETRIES):
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            pages = data.get("query", {}).get("pages", [])
            if pages and "revisions" in pages[0]:
                return pages[0]["revisions"][0]["content"]
            return None
        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                time.sleep(2 ** attempt)
            else:
                print(f"  Warning: failed to fetch {title!r}: {e}", file=sys.stderr)
                return None


_PRON_BLOCK_RE = re.compile(
    r"\{\{IPA\|en\|(.*?)\}\}", re.DOTALL
)
_IPA_RE = re.compile(r"/([^/]+)/")
_RP_HINTS = {"rp", "received pronunciation", "ssb", "standard southern british",
             "uk", "british", "southern england", "southern british", "non-rhotic"}
_DISQUALIFY = {"ga", "general american", "us", "usa", "au", "australia",
               "nz", "new zealand", "scotland", "scottish", "ireland", "irish",
               "rhotic", "t-flapping", "archaic", "obsolete", "dated"}


def _score_dialect(label: str) -> int:
    low = label.lower()
    if any(d in low for d in _DISQUALIFY):
        return -100
    if any(h in low for h in {"rp", "received pronunciation", "ssb"}):
        return 3
    if any(h in low for h in {"uk", "british"}):
        return 2
    return 1  # generic / no label


def _extract_rp_ipa(wikitext: str) -> Optional[str]:
    """Extract best British RP IPA from wikitext IPA templates."""
    # Import the heavier extraction logic from audit_wiktionary_ipa.py if available
    try:
        sys.path.insert(0, SCRIPT_DIR)
        import audit_wiktionary_ipa as _aud
        result = _aud.extract_rp_ipa_from_wikitext(wikitext)
        if result:
            return result
    except Exception:
        pass

    # Lightweight fallback: scan {{IPA|en|...}} templates
    best_ipa: Optional[str] = None
    best_score = -999
    for m in _PRON_BLOCK_RE.finditer(wikitext):
        content = m.group(1)
        # Collect labels (non-IPA parts)
        labels = [p for p in content.split("|") if not p.startswith("/")]
        label_str = " ".join(labels).lower()
        score = _score_dialect(label_str)
        if score < 0:
            continue
        # Extract IPA values
        for ipa_m in _IPA_RE.finditer(content):
            ipa_inner = ipa_m.group(1)
            # Remove combining diacritics (marks)
            ipa_inner = re.sub(r"[\u0300-\u036f]", "", ipa_inner)
            candidate = f"/{ipa_inner}/"
            if score > best_score:
                best_score = score
                best_ipa = candidate

    return best_ipa


def fetch_ipa(word: str, cache: Dict, force: bool) -> Optional[str]:
    """Return IPA for a word, using cache when available."""
    if not force and word in cache:
        cached = cache[word]
        wikitext = cached.get("wikitext", "") if isinstance(cached, dict) else cached
        if wikitext:
            return _extract_rp_ipa(wikitext)
        return None

    print(f"  Fetching: {word!r}")
    wikitext = _fetch_wikitext(word)
    time.sleep(REQUEST_INTERVAL)
    if wikitext:
        cache[word] = {"wikitext": wikitext, "ts": time.time()}
        return _extract_rp_ipa(wikitext)
    cache[word] = {"wikitext": "", "ts": time.time()}
    return None


# ── Word Discovery ────────────────────────────────────────────────────────────

def get_xml_words() -> Set[str]:
    tree = ET.parse(EXTRAWORDLIST_XML)
    return {e.attrib.get("str", "").strip() for e in tree.getroot().findall(".//word")}


def get_json_words() -> Set[str]:
    with open(DEFINITIONS_JSON, encoding="utf-8") as f:
        return set(json.load(f).keys())


def get_missing_words() -> List[str]:
    """Words with empty or invalid IPA in definitions.json."""
    with open(DEFINITIONS_JSON, encoding="utf-8") as f:
        defs = json.load(f)
    missing = []
    for word, entry in defs.items():
        p = entry.get("phonetic", "")
        if not p or not p.startswith("/") or not p.endswith("/"):
            missing.append(word)
    return sorted(missing)


# ── Apply Updates ─────────────────────────────────────────────────────────────

def apply_to_definitions_json(updates: Dict[str, str], dry_run: bool) -> int:
    with open(DEFINITIONS_JSON, encoding="utf-8") as f:
        defs = json.load(f)
    count = 0
    for word, ipa in updates.items():
        if word in defs and defs[word].get("phonetic") != ipa:
            defs[word]["phonetic"] = ipa
            count += 1
    if not dry_run and count:
        with open(DEFINITIONS_JSON, "w", encoding="utf-8") as f:
            json.dump(defs, f, ensure_ascii=False, indent=2)
            f.write("\n")
    return count


IPA_ELEM_RE = re.compile(
    r"(<ipa>)(?:<!\[CDATA\[.*?\]\]>|[^<]*)?(</ipa>)", re.DOTALL
)
WORD_ATTR_RE = re.compile(r'<word\b[^>]*\bstr\s*=\s*"([^"]*)"')


def apply_to_xml(updates: Dict[str, str], dry_run: bool) -> int:
    with open(EXTRAWORDLIST_XML, encoding="utf-8", newline="") as f:
        content = f.read()

    count = 0
    result_parts = []
    pos = 0
    word_start_re = re.compile(r"<word\b[^>]*>", re.DOTALL)

    for m in word_start_re.finditer(content):
        result_parts.append(content[pos:m.start()])
        pos = m.start()
        str_m = WORD_ATTR_RE.match(m.group(0))
        word_str = str_m.group(1) if str_m else None
        end_tag = content.find("</word>", m.end())
        if end_tag == -1:
            result_parts.append(content[pos:])
            pos = len(content)
            break
        end_tag += len("</word>")
        block = content[m.start():end_tag]

        if word_str and word_str in updates:
            new_ipa = updates[word_str]
            new_elem = f"<![CDATA[{new_ipa}]]>"

            def replace_ipa(mo, _new=new_elem, _word=word_str):
                nonlocal count
                count += 1
                return mo.group(1) + _new + mo.group(2)

            block, n = IPA_ELEM_RE.subn(replace_ipa, block)
            if n > 0:
                count = count  # already incremented in replace_ipa
            else:
                count -= 0  # no element found — skip

        result_parts.append(block)
        pos = end_tag

    result_parts.append(content[pos:])
    new_content = "".join(result_parts)

    if not dry_run and count:
        with open(EXTRAWORDLIST_XML, "w", encoding="utf-8", newline="") as f:
            f.write(new_content)
    return count


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Fetch and apply IPA updates for new/missing words."
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="Report what would change, do not write.")
    parser.add_argument("--word", metavar="WORD",
                        help="Update a single word only.")
    parser.add_argument("--force", action="store_true",
                        help="Re-fetch from Wiktionary even if cached.")
    args = parser.parse_args()

    # Load cache
    os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)
    if os.path.exists(CACHE_PATH):
        with open(CACHE_PATH, encoding="utf-8") as f:
            cache = json.load(f)
    else:
        cache = {}

    # Determine target words
    if args.word:
        targets = [args.word]
    else:
        targets = get_missing_words()
        # Also include XML words missing from definitions
        xml_only = get_xml_words() - get_json_words()
        targets = list(set(targets) | xml_only)
        targets.sort()

    if not targets:
        print("✓ No missing or invalid IPA entries found. Nothing to do.")
        return

    print(f"Fetching IPA for {len(targets)} word(s)…")
    updates: Dict[str, str] = {}

    for word in targets:
        ipa = fetch_ipa(word, cache, args.force)
        if ipa:
            updates[word] = ipa
            print(f"  {word!r:50s} → {ipa}")
        else:
            print(f"  {word!r:50s} → (not found on Wiktionary)")

    # Save cache
    if not args.dry_run:
        with open(CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)

    if not updates:
        print("\nNo updates to apply.")
        return

    mode = "[DRY RUN] " if args.dry_run else ""
    print(f"\n{mode}Applying {len(updates)} update(s)…")
    defs_n = apply_to_definitions_json(updates, args.dry_run)
    xml_n = apply_to_xml(updates, args.dry_run)
    print(f"  definitions.json updated: {defs_n}")
    print(f"  extrawordlist.xml updated: {xml_n}")

    if not args.dry_run:
        print("\nRunning quick validation…")
        os.system(f"python3 {os.path.join(SCRIPT_DIR, 'check_ipa.py')}")


if __name__ == "__main__":
    main()
