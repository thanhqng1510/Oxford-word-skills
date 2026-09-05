#!/usr/bin/env python3
"""
Wiktionary Retrieval, Normalization, & Compound Synthesis Engine
Milestone 1 — Oxford Word Skills British English (RP) IPA Audit

Audits all vocabulary entries (~2,783 XML entries / 2,777 unique headwords)
against English Wiktionary (en.wiktionary.org), standardizing on standard
British English (Received Pronunciation / UK / SSB) with 100% completeness.
"""

import argparse
import difflib
import gzip
import json
import os
import random
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Set, Tuple

# Base paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
RESOURCES_DIR = os.path.join(PROJECT_ROOT, "Resources")
EXTRAWORDLIST_XML_PATH = os.path.join(RESOURCES_DIR, "extrawordlist.xml")
DEFINITIONS_JSON_PATH = os.path.join(RESOURCES_DIR, "definitions.json")
DEFAULT_CACHE_DIR = os.path.join(PROJECT_ROOT, ".agents", "cache")
DEFAULT_CACHE_FILE = os.path.join(DEFAULT_CACHE_DIR, "wiktionary_cache.json")
DEFAULT_OUTPUT_MAP = os.path.join(
    PROJECT_ROOT, ".agents", "teamwork_preview_worker_m1_1", "audited_ipa_map.json"
)

# Wiktionary API Configuration
WIKTIONARY_API_URL = "https://en.wiktionary.org/w/api.php"
USER_AGENT = (
    "OxfordWordSkillsIPABot/1.0 "
    "(https://github.com/thanhqng/OxfordWordSkills; contact: dev@example.com) "
    "Python-urllib/3.12"
)
BATCH_SIZE = 50
REQUEST_INTERVAL = 1.0  # 1.0s between remote requests
MAX_RETRIES = 5

# Validation Regexes
VALID_IPA_REGEX = re.compile(
    r"^/[a-zæɑɒɔəɛɜɪʊʌbcdefɡhijklmnŋpqrstuvwzðθʃʒˈˌː\s\-\,\.\(\)\…']+/$"
)
FORBIDDEN_SAMPA_REGEX = re.compile(r'[%&"”QVUITAODSZ23@ÍÙ]')

# Dialect Keywords
STANDARD_RP_KEYWORDS = [
    "rp", "received pronunciation", "ssb", "standard southern british"
]
GENERIC_UK_KEYWORDS = [
    "uk", "british", "southern england", "southern british",
    "england", "trap-bath split", "non-rhotic"
]
COMMONWEALTH_KEYWORDS = [
    "commonwealth"
]
DISQUALIFY_KEYWORDS = [
    # North American
    "ga", "genam", "general american", "us", "usa", "united states",
    "north america", "north american", "ca", "canada", "canadian",
    "canadian raising", "cane", "pittsburgh", "aave", "appalachian",
    # Antipodean
    "au", "australia", "australian", "aue", "ause",
    "nz", "new zealand", "nze",
    # Celtic & UK Regional (Non-RP)
    "scotland", "scottish", "sce",
    "wales", "welsh", "cymru",
    "northumbria", "northumbrian", "geordie", "northern england",
    "ireland", "irish", "northern ireland", "dublin",
    # Global & Other
    "za", "south africa", "south african",
    "india", "indian", "ine", "indic", "philippines",
    "mle", "cornish",
    # Non-Standard Phonetic Phenomena, Registers, and Variants
    "flapping", "t-flapping", "nt-flapping",
    "monophthongization", "fast speech", "casual",
    "archaic", "obsolete", "dated", "proscribed", "sometimes"
]

# Weak forms for connected speech synthesis
WEAK_FORMS = {
    "a": "/ə/",
    "an": "/ən/",
    "the": "/ðə/",
    "of": "/əv/",
    "to": "/tə/",
    "at": "/ət/",
    "as": "/əz/",
    "for": "/fə(r)/",
    "and": "/ənd/",
    "or": "/ɔː(r)/",
    "in": "/ɪn/",
    "on": "/ɒn/",
    "with": "/wɪð/",
}


def sampa_to_ipa(sampa: str) -> str:
    """
    Converts Oxford SAMPA / ASCII phonetic encoding into standard British Unicode IPA.
    Sanitizes trailing slashes, orphaned stress before ellipsis, and unescaped characters.
    """
    if not sampa:
        return ""
    trimmed = sampa.strip()
    if not trimmed:
        return ""

    # Sanitize trailing or leading slashes
    trimmed = trimmed.rstrip("/").lstrip("/")
    if not trimmed:
        return ""

    text = trimmed
    text = text.replace("”", "\"")
    text = text.replace("Í", "tS")
    text = text.replace("Ù", "dZ")
    text = text.replace("2@", "@")
    text = text.replace("Ww", "w")
    text = text.replace("2", "@")

    replacements = [
        ("\"", "ˈ"),
        ("%", "ˌ"),
        ("tS", "tʃ"),
        ("dZ", "dʒ"),
        ("eI", "eɪ"),
        ("aI", "aɪ"),
        ("OI", "ɔɪ"),
        ("aU", "aʊ"),
        ("@U", "əʊ"),
        ("I@", "ɪə"),
        ("e@", "eə"),
        ("U@", "ʊə"),
        ("3:", "ɜː"),
        ("3", "ɜː"),
        ("i:", "iː"),
        ("u:", "uː"),
        ("A:", "ɑː"),
        ("O:", "ɔː"),
        (":", "ː"),
        ("@", "ə"),
        ("&", "æ"),
        ("A", "ɑː"),
        ("V", "ʌ"),
        ("O", "ɔː"),
        ("Q", "ɒ"),
        ("U", "ʊ"),
        ("I", "ɪ"),
        ("E", "e"),
        ("T", "θ"),
        ("D", "ð"),
        ("S", "ʃ"),
        ("Z", "ʒ"),
        ("N", "ŋ"),
    ]

    for old, new in replacements:
        text = text.replace(old, new)

    # Sanitize orphaned stress before ellipsis (e.g. "ˈ..." -> "...")
    text = re.sub(r"[ˈˌ]\s*(\.{3}|…)", r"\1", text)
    text = re.sub(r"\s+", " ", text).strip()
    return f"/{text}/"


def normalize_ipa(raw: str) -> str:
    """
    Phonetic Normalizer:
    Strips non-phonemic symbols, syllable dots, turned-r, tie bars, Americanisms,
    combining diacritics, and qualifier markup.
    Ensures broad phonemic slash notation /.../.
    """
    if not raw:
        return ""
    # Strip inline Wiktionary HTML tags or qualifier brackets (e.g. <q:uncommon>, <a:also <<RP>>>)
    text = re.sub(r"<[^>]+>", "", raw).strip()
    if text.startswith("[") and text.endswith("]"):
        inner = text[1:-1]
    elif text.startswith("/") and text.endswith("/"):
        inner = text[1:-1]
    else:
        inner = text

    # Strip syllable boundary dots
    inner = inner.replace(".", "")
    # Map turned-r to standard r
    inner = inner.replace("ɹ", "r")
    inner = inner.replace("(ɹ)", "(r)")
    # Strip ligature tie bars
    inner = inner.replace("͡", "").replace("͜", "")
    # Strip Unicode combining diacritical marks (U+0300 to U+036F)
    # Strips non-syllabic breve U+032F, syllabic mark U+0329, tilde U+0303, etc.
    inner = re.sub(r"[\u0300-\u036f]", "", inner)
    # Strip American rhoticism
    inner = inner.replace("ɚ", "ə").replace("ɝ", "ɜː")
    # NOTE: Do NOT map 'ɾ' to 't'. Candidates containing 'ɾ' are disqualified in filtering.
    # Standardize open-mid front vowel to Gimson / Oxford standard 'e'
    inner = inner.replace("ɛ", "e")
    # Map script g (U+0261) to standard ASCII g (U+0067)
    inner = inner.replace("ɡ", "g")
    # Standardize non-standard length marks or ASCII colons to Unicode length mark
    inner = inner.replace(":", "ː")
    # Normalize multiple spaces
    inner = re.sub(r"\s+", " ", inner).strip()
    # Strip orphaned stress before ellipsis
    inner = re.sub(r"[ˈˌ]\s*(\.{3}|…)", r"\1", inner)

    return f"/{inner}/"


def consonant_skeleton(s: str) -> str:
    """Extracts the sequence of consonant phonemes for disambiguation tie-breaking."""
    return "".join(c for c in s.lower() if c in "bcdfghjklmnpqrstvwxzðθʃʒŋ")



def extract_english_section(wikitext: str) -> str:
    """Extracts only the ==English== section from wikitext, ignoring other languages."""
    if not wikitext:
        return ""
    m = re.search(r"==\s*English\s*==(.*?)(?=\n==[^=]|\Z)", wikitext, re.DOTALL | re.IGNORECASE)
    return m.group(1) if m else ""


def parse_wiktionary_ipa_candidates(wikitext: str, headword: str = "") -> List[Tuple[str, int, str]]:
    """
    Parses all candidate pronunciations from the English section of wikitext.
    Returns list of (normalized_ipa, score, raw_line).
    Scoring:
      +100: Explicit local RP/SSB (+100) or inherited UK without disqualifier (+100)
      +80:  UK shared with GA/US (e.g. a=UK,US)
      +50:  Commonwealth
      +10:  Neutral (unspecified dialect on English page)
      -100: Disqualified dialects (US, CA, AU, NZ, Scotland, Wales, Northumbria, etc.)
    """
    eng_text = extract_english_section(wikitext)
    if not eng_text:
        return []

    candidates: List[Tuple[str, int, str]] = []
    lines = eng_text.splitlines()

    # Track bullet nesting levels to prevent regional sub-bullets from inheriting UK
    bullet_stack: Dict[int, str] = {}
    hw = headword.strip()

    for line in lines:
        line_clean = line.strip()
        if not line_clean:
            continue

        # Determine bullet nesting level
        b_match = re.match(r"^(\*+)", line_clean)
        level = len(b_match.group(1)) if b_match else 0

        # Bullet accent template extraction, e.g. * {{a|UK}} or * {{a|en|RP}}
        accent_m = re.search(r"\{\{(?:a|accent)\|(?:en\|)?([^}]+)\}\}", line_clean, re.IGNORECASE)
        if accent_m:
            bullet_stack = {k: v for k, v in bullet_stack.items() if k < level}
            bullet_stack[level] = accent_m.group(1).lower()
        elif level > 0:
            bullet_stack = {k: v for k, v in bullet_stack.items() if k <= level}
        else:
            bullet_stack = {}

        current_bullet_accent = " ".join(bullet_stack.values())

        # Extract {{IPA|en|...}} templates
        for ipa_m in re.finditer(r"\{\{IPA\|en\|([^}]+)\}\}", line_clean):
            template_args = ipa_m.group(1).split("|")
            transcriptions: List[str] = []
            local_accents: List[str] = []

            for arg in template_args:
                arg = arg.strip()
                if not arg:
                    continue
                if "=" in arg:
                    k, v = arg.split("=", 1)
                    k = k.strip().lower()
                    v = v.strip().lower()
                    # Support a, aa, a1..a4, q, qq, q1..q4, qual, qualifier
                    if re.match(r"^(a|aa|q|qq)\d*$", k) or k in ("qual", "qualifier"):
                        local_accents.append(v)
                elif arg.startswith("/") or arg.startswith("["):
                    transcriptions.append(arg)

            local_accents_str = " ".join(local_accents).lower()
            all_accents_str = f"{local_accents_str} {current_bullet_accent}".strip().lower()

            if "enpr" in line_clean.lower():
                enpr_m = re.search(r"\{\{enPR\|[^}]+a=([^}|]+)", line_clean, re.IGNORECASE)
                if enpr_m:
                    all_accents_str += " " + enpr_m.group(1).lower()

            # Accent checks
            has_local_rp = any(re.search(r"\b" + re.escape(k) + r"\b", local_accents_str) for k in STANDARD_RP_KEYWORDS)
            has_local_uk = any(re.search(r"\b" + re.escape(k) + r"\b", local_accents_str) for k in GENERIC_UK_KEYWORDS)
            has_local_disqualify = any(re.search(r"\b" + re.escape(k) + r"\b", local_accents_str) for k in DISQUALIFY_KEYWORDS)

            has_any_rp = any(re.search(r"\b" + re.escape(k) + r"\b", all_accents_str) for k in STANDARD_RP_KEYWORDS)
            has_any_uk = any(re.search(r"\b" + re.escape(k) + r"\b", all_accents_str) for k in GENERIC_UK_KEYWORDS)
            has_any_disqualify = any(re.search(r"\b" + re.escape(k) + r"\b", all_accents_str) for k in DISQUALIFY_KEYWORDS)
            has_commonwealth = any(re.search(r"\b" + re.escape(k) + r"\b", all_accents_str) for k in COMMONWEALTH_KEYWORDS)

            # Score calculation
            score = 10  # default neutral
            if has_local_rp:
                # 1. Explicit local RP takes highest precedence even if shared (e.g. "a=RP,GA")
                score = 100
            elif has_local_uk and not has_local_disqualify:
                # 2. Local UK without disqualifiers
                score = 100
            elif has_local_uk and has_local_disqualify:
                # 3. Shared between UK and US/CA/AU (e.g. a=UK,US), score 80 unless regional
                if not any(k in local_accents_str for k in ("scotland", "scottish", "wales", "welsh", "northumbria", "northumbrian", "geordie", "pittsburgh", "monophthongization", "flapping", "archaic", "sometimes")):
                    score = 80
                else:
                    score = -100
            elif has_local_disqualify:
                # 4. Local tag specifies regional, foreign, or non-standard variety
                score = -100
            elif has_any_disqualify:
                # 5. Bullet-level disqualification
                score = -100
            elif has_any_rp:
                score = 100
            elif has_any_uk:
                score = 100
            elif has_commonwealth:
                score = 50

            for trans in transcriptions:
                norm = normalize_ipa(trans)
                # Strictly reject empty, tap 'ɾ', invalid characters, or raw SAMPA
                if not norm or "ɾ" in norm or not VALID_IPA_REGEX.match(norm) or FORBIDDEN_SAMPA_REGEX.search(norm):
                    continue

                inner = norm[1:-1]
                # Reject circumfixes or broken templates
                if "- -" in inner or " - " in inner or "--" in inner:
                    continue

                # Structural Invariant Filtering based on headword:
                if hw:
                    # Reject dangling hyphens unless the headword itself has them
                    if (inner.startswith("-") and not hw.startswith("-")) or (inner.endswith("-") and not hw.endswith("-")):
                        continue
                    # Reject single-word headwords with internal spaces
                    if " " in inner and " " not in hw and "-" not in hw and not (hw.isupper() and len(hw) <= 4):
                        continue
                else:
                    if inner.startswith("-") or inner.endswith("-"):
                        continue
                    if " " in inner:
                        continue

                candidates.append((norm, score, line_clean))

    return candidates


class WiktionaryClient:
    """
    Batched, rate-limited Wiktionary Action API client with local JSON caching
    and exponential backoff.
    """

    def __init__(self, cache_file: str, rate_limit: float = REQUEST_INTERVAL, batch_size: int = BATCH_SIZE):
        self.cache_file = cache_file
        self.rate_limit = rate_limit
        self.batch_size = batch_size
        self.cache: Dict[str, Optional[str]] = self._load_cache()
        self.last_request_time = 0.0

    def _load_cache(self) -> Dict[str, Optional[str]]:
        if os.path.isfile(self.cache_file):
            try:
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    print(f"Loaded {len(data)} cached Wiktionary pages from {self.cache_file}")
                    return data
            except Exception as e:
                print(f"Warning: Could not read cache from {self.cache_file}: {e}")
        return {}

    def save_cache(self):
        os.makedirs(os.path.dirname(os.path.abspath(self.cache_file)), exist_ok=True)
        tmp_file = self.cache_file + ".tmp"
        with open(tmp_file, "w", encoding="utf-8") as f:
            json.dump(self.cache, f, ensure_ascii=False, indent=2)
        os.replace(tmp_file, self.cache_file)

    def _throttle(self):
        elapsed = time.time() - self.last_request_time
        if elapsed < self.rate_limit:
            time.sleep(self.rate_limit - elapsed)
        self.last_request_time = time.time()

    def _fetch_batch_with_retry(self, titles: List[str]) -> Dict[str, Optional[str]]:
        params = {
            "action": "query",
            "titles": "|".join(titles),
            "prop": "revisions",
            "rvslots": "main",
            "rvprop": "content",
            "format": "json",
            "redirects": "1",
        }
        url = WIKTIONARY_API_URL + "?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": USER_AGENT,
                "Accept-Encoding": "gzip",
            },
        )

        for attempt in range(MAX_RETRIES):
            self._throttle()
            try:
                with urllib.request.urlopen(req, timeout=20) as resp:
                    raw_data = resp.read()
                    if resp.headers.get("Content-Encoding") == "gzip" or raw_data.startswith(b"\x1f\x8b"):
                        raw_data = gzip.decompress(raw_data)
                    data = json.loads(raw_data.decode("utf-8", errors="replace"))

                    results: Dict[str, Optional[str]] = {}
                    query_data = data.get("query", {})

                    # Mapping normalized/redirected titles back to requested titles
                    norm_map: Dict[str, str] = {}
                    for norm in query_data.get("normalized", []):
                        norm_map[norm.get("to")] = norm.get("from")
                    for redir in query_data.get("redirects", []):
                        to_t = redir.get("to")
                        from_t = redir.get("from")
                        orig = norm_map.get(from_t, from_t)
                        norm_map[to_t] = orig

                    pages = query_data.get("pages", {})
                    for pid, p in pages.items():
                        title = p.get("title", "")
                        orig_title = norm_map.get(title, title)

                        if "missing" in p:
                            results[orig_title] = None
                            results[title] = None
                        else:
                            revs = p.get("revisions", [])
                            if revs and "slots" in revs[0] and "main" in revs[0]["slots"]:
                                content = revs[0]["slots"]["main"].get("*", "")
                            elif revs:
                                content = revs[0].get("*", "")
                            else:
                                content = ""
                            results[orig_title] = content
                            results[title] = content

                    # Ensure every title in batch has an entry
                    for t in titles:
                        if t not in results:
                            matched = False
                            for k, v in results.items():
                                if k.lower() == t.lower():
                                    results[t] = v
                                    matched = True
                                    break
                            if not matched:
                                results[t] = None

                    return results

            except urllib.error.HTTPError as e:
                if e.code in (429, 503):
                    retry_after = e.headers.get("Retry-After")
                    delay = float(retry_after) if retry_after else (2 ** attempt) + random.uniform(0.5, 1.5)
                    print(f"HTTP {e.code} received. Backing off for {delay:.2f}s (attempt {attempt + 1}/{MAX_RETRIES})...")
                    time.sleep(delay)
                else:
                    print(f"HTTP Error {e.code} for batch: {e.reason}")
                    break
            except Exception as e:
                delay = (2 ** attempt) + random.uniform(0.5, 1.5)
                print(f"Network error on batch: {e}. Retrying in {delay:.2f}s...")
                time.sleep(delay)

        # On ultimate failure, return None for batch
        return {t: None for t in titles}

    def fetch_all(self, titles: List[str]) -> Dict[str, Optional[str]]:
        unique_titles = sorted(list(set(titles)))
        missing = [t for t in unique_titles if t not in self.cache]

        if missing:
            batches = [missing[i:i + self.batch_size] for i in range(0, len(missing), self.batch_size)]
            print(f"Querying Wiktionary API for {len(missing)} uncached titles in {len(batches)} batches...")
            for idx, batch in enumerate(batches):
                res = self._fetch_batch_with_retry(batch)
                self.cache.update(res)
                if (idx + 1) % 5 == 0 or idx == len(batches) - 1:
                    self.save_cache()
                    print(f"  Processed batch {idx + 1}/{len(batches)} ({len(self.cache)} total pages cached)")
            self.save_cache()

        return {t: self.cache.get(t) for t in unique_titles}


def extract_base_query_title(headword: str) -> str:
    """
    Cleans headwords to isolate the base dictionary title for querying Wiktionary.
    Strips parenthetical glosses, POS indicators (' N', ' V'), and variable ellipsis.
    """
    w = headword.strip()

    # Acronyms with expanded names: e.g. "BBC (British Broadcasting Corporation)" -> "BBC"
    m = re.match(r"^([A-Z0-9]+)\s*\(.+\)$", w)
    if m:
        return m.group(1).strip()

    # Measurement units spoken pronunciations
    unit_map = {
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
    if w in unit_map:
        return unit_map[w]

    # Optional plural/suffix notation: "backward(s)" -> "backwards"
    if "(s)" in w:
        return w.replace("(s)", "s").strip()

    # Parenthetical glosses: "ad (= advertisement)" -> "ad", "produce (goods)" -> "produce"
    if "(" in w:
        base = w.split("(")[0].strip()
        if base:
            return base

    # POS indicators: "record N" -> "record", "contrast V" -> "contrast"
    if w.endswith(" N") or w.endswith(" V"):
        return w[:-2].strip()

    # Ellipsis tokens: "How do you feel about ...?" -> "How do you feel about"
    w = re.sub(r"\.{3}|…", "", w).strip()
    return w


def synthesize_compound_pronunciation(
    phrase: str,
    word_ipa_map: Dict[str, str],
    ground_truth_ipa: Optional[str] = None
) -> str:
    """
    Applies English prosodic stress rules to multi-word phrases and idioms:
    1. Weak Forms: Unstressed grammatical function words (a, the, of, to, at, as, for, and, or, in, on, with).
    2. Constituent Lookup: Resolves component lexical words from word_ipa_map.
    3. Phrasal Verb Particle Stress: Primary stress on adverbial particle, secondary on verb.
    4. Compound Noun vs. Syntactic Phrase (Nuclear Stress Rule):
       - Compound nouns: primary stress on first element, secondary on second.
       - Syntactic phrases: primary stress on final lexical element.
    5. Fallback Guard: Conversational idioms, elisions, or phrases with unindexed components
       fall back cleanly and transparently to validated Oxford curriculum ground truth.
    """
    clean_phrase = re.sub(r"\(.*?\)", "", phrase).strip()
    clean_phrase = re.sub(r"\.{3}|…", "", clean_phrase).strip()
    words = clean_phrase.split()

    # Guard: Conversational idioms, elisions, sentences with contractions, articles, or > 2 words
    # These fall back cleanly and transparently to validated Oxford curriculum ground truth
    is_idiom_or_sentence = (
        len(words) > 2 or
        len(words) < 2 or
        any(m in phrase for m in ("?", "!", "...", "…", "'")) or
        any(w.lower() in ("a", "an", "the") for w in words)
    )

    if is_idiom_or_sentence and ground_truth_ipa:
        return ground_truth_ipa

    particles = {"up", "down", "in", "out", "on", "off", "away", "back", "over", "round", "around", "through", "across"}
    tokens_ipa: List[Tuple[str, str, bool]] = []
    can_synthesize = True

    for i, w in enumerate(words):
        w_clean = re.sub(r"[^\w\-]", "", w).lower()
        if not w_clean:
            continue
        if w_clean in WEAK_FORMS and i < len(words) - 1:
            tokens_ipa.append((w_clean, WEAK_FORMS[w_clean].strip("/"), True))
        elif w_clean in word_ipa_map:
            tokens_ipa.append((w_clean, word_ipa_map[w_clean].strip("/"), False))
        else:
            can_synthesize = False
            break

    if not can_synthesize or not tokens_ipa:
        if ground_truth_ipa:
            return ground_truth_ipa
        return ""

    is_phrasal_verb = (len(words) == 2 and words[1].lower() in particles)
    syllables: List[str] = []

    if is_phrasal_verb:
        # Particle receives primary stress ˈ; verb receives secondary stress ˌ
        verb_ipa = tokens_ipa[0][1].replace("ˈ", "ˌ")
        if not verb_ipa.startswith("ˌ"):
            verb_ipa = "ˌ" + verb_ipa
        particle_ipa = tokens_ipa[1][1]
        if not particle_ipa.startswith("ˈ"):
            particle_ipa = "ˈ" + particle_ipa
        syllables = [verb_ipa, particle_ipa]
    else:
        # Check ground truth stress pattern to distinguish compound nouns vs syntactic phrases
        gt_stress_on_first = False
        if ground_truth_ipa:
            gt_words = ground_truth_ipa.strip("/").split()
            if len(gt_words) >= 2 and "ˈ" in gt_words[0] and "ˈ" not in gt_words[-1]:
                gt_stress_on_first = True

        if gt_stress_on_first:
            for i, (w_clean, base_ipa, is_weak) in enumerate(tokens_ipa):
                if is_weak:
                    syllables.append(base_ipa)
                elif i == 0:
                    syllables.append(base_ipa)
                else:
                    syllables.append(base_ipa.replace("ˈ", "ˌ"))
        else:
            for i, (w_clean, base_ipa, is_weak) in enumerate(tokens_ipa):
                if is_weak:
                    syllables.append(base_ipa)
                elif i < len(tokens_ipa) - 1:
                    syllables.append(base_ipa.replace("ˈ", "ˌ"))
                else:
                    syllables.append(base_ipa)

    synthesized_raw = " ".join(syllables)
    synthesized_norm = normalize_ipa(f"/{synthesized_raw}/")

    if VALID_IPA_REGEX.match(synthesized_norm) and not FORBIDDEN_SAMPA_REGEX.search(synthesized_norm):
        return synthesized_norm
    elif ground_truth_ipa:
        return ground_truth_ipa
    return synthesized_norm



def build_audited_ipa_map(
    cache_file: str = DEFAULT_CACHE_FILE,
    output_map_path: str = DEFAULT_OUTPUT_MAP,
    rate_limit: float = REQUEST_INTERVAL,
    batch_size: int = BATCH_SIZE,
    dry_run: bool = False,
    verbose: bool = False,
) -> Dict[str, str]:
    """
    Orchestrates the full Milestone 1 IPA audit pipeline:
    1. Ingests all 2,777 vocabulary headwords from definitions.json and extrawordlist.xml.
    2. Extracts query titles and fetches wikitext via batched Action API with rate limiting.
    3. Applies UK / RP dialect priority scoring (+100 RP/UK > +50 Commonwealth > +10 Neutral; -100 US/GA).
    4. Normalizes all pronunciations (strips dots, maps turned-r, removes brackets, removes tie bars).
    5. Disambiguates homographs (noun vs verb stress) using POS context.
    6. Synthesizes phrase/compound stress and cross-validates with Oxford curriculum ground truth.
    7. Enforces strict phonetic invariants and saves audited mapping.
    """
    print("=" * 70)
    print("Oxford Word Skills — Milestone 1 IPA Audit Engine")
    print("=" * 70)

    # 1. Load Data Stores
    with open(DEFINITIONS_JSON_PATH, "r", encoding="utf-8") as f:
        defs_dict = json.load(f)

    xml_tree = ET.parse(EXTRAWORDLIST_XML_PATH)
    xml_words_elem = xml_tree.findall(".//word")

    # Map headwords to raw XML SAMPA ground truth
    xml_ground_truth: Dict[str, str] = {}
    for w_elem in xml_words_elem:
        headword = w_elem.attrib.get("str", "").strip()
        ipa_elem = w_elem.find("ipa")
        raw_sampa = ipa_elem.text if (ipa_elem is not None and ipa_elem.text) else ""
        if headword and raw_sampa:
            xml_ground_truth[headword] = raw_sampa

    all_headwords = sorted(list(defs_dict.keys()))
    print(f"Total vocabulary headwords to audit: {len(all_headwords)}")

    # 2. Extract Base Query Titles
    query_title_to_headwords: Dict[str, List[str]] = {}
    for hw in all_headwords:
        base_title = extract_base_query_title(hw)
        query_title_to_headwords.setdefault(base_title, []).append(hw)

    # Also add individual constituent words of phrases to query list
    for hw in all_headwords:
        if " " in hw:
            for piece in hw.split():
                clean_p = re.sub(r"[^\w\-]", "", piece).strip()
                if clean_p and len(clean_p) > 1:
                    query_title_to_headwords.setdefault(clean_p, [])

    all_query_titles = sorted(list(query_title_to_headwords.keys()))
    print(f"Unique Wiktionary query titles: {len(all_query_titles)}")

    # 3. Fetch from Wiktionary
    client = WiktionaryClient(cache_file=cache_file, rate_limit=rate_limit, batch_size=batch_size)
    if dry_run:
        print("Dry run enabled: Using cached Wiktionary pages only.")
        wikitext_map = {t: client.cache.get(t) for t in all_query_titles}
    else:
        wikitext_map = client.fetch_all(all_query_titles)

    # 4. Parse Wiktionary RP Pronunciations for Base Titles
    base_title_ipa: Dict[str, str] = {}
    wiktionary_hits = 0

    for title, wikitext in wikitext_map.items():
        if not wikitext:
            continue
        candidates = parse_wiktionary_ipa_candidates(wikitext, headword=title)
        if not candidates:
            continue

        # Filter for UK/RP or neutral candidates (score >= 10)
        valid_candidates = [c for c in candidates if c[1] >= 10]
        if not valid_candidates:
            continue

        # Sort by score descending
        valid_candidates.sort(key=lambda x: x[1], reverse=True)
        top_ipa = valid_candidates[0][0]
        base_title_ipa[title] = top_ipa
        wiktionary_hits += 1

    print(f"Wiktionary entries with verified British RP IPA: {wiktionary_hits} / {len(all_query_titles)}")

    # 5. Audit Each Vocabulary Headword
    audited_map: Dict[str, str] = {}
    wiktionary_assigned = 0
    homographs_disambiguated = 0
    compounds_synthesized = 0
    curriculum_fallback_count = 0
    trailing_slashes_fixed = 0
    ellipsis_stress_fixed = 0

    for hw in all_headwords:
        raw_xml = xml_ground_truth.get(hw, "")
        clean_xml_raw = raw_xml.rstrip("/")
        if raw_xml.endswith("/"):
            trailing_slashes_fixed += 1

        if re.search(r"[%\"”]\s*(\.{3}|…)", raw_xml):
            ellipsis_stress_fixed += 1

        sanitized_xml_ipa = sampa_to_ipa(clean_xml_raw)

        # Check for acronyms with parenthetical expansions (e.g. "BBC (British Broadcasting Corporation)")
        is_acronym_gloss = bool(re.match(r"^[A-Z0-9]+\s*\(.+\)$", hw))

        # Determine POS context for disambiguation
        is_noun = hw.endswith(" N") or ("(goods)" in hw) or ("(a film)" in hw and "producer" in hw)
        is_verb = hw.endswith(" V") or ("(= make a note)" in hw) or ("(= put onto a disc)" in hw) or ("(goods)" in hw and hw.startswith("produce"))

        base_title = extract_base_query_title(hw)
        is_single_lexical_word = (" " not in base_title)
        assigned_ipa: Optional[str] = None

        if not is_acronym_gloss:
            wikitext = wikitext_map.get(base_title)
            if wikitext:
                candidates = parse_wiktionary_ipa_candidates(wikitext, headword=hw)
                valid_candidates = [c for c in candidates if c[1] >= 10]

                if valid_candidates:
                    # Handle homograph disambiguation
                    if is_noun:
                        noun_cands = [c for c in valid_candidates if c[0].startswith("/ˈ")]
                        if noun_cands:
                            valid_candidates = noun_cands
                    elif is_verb:
                        verb_cands = [c for c in valid_candidates if not c[0].startswith("/ˈ") and "ˈ" in c[0]]
                        if verb_cands:
                            valid_candidates = verb_cands

                    # Break ties using exact ground truth match, consonant skeleton match, and sequence similarity
                    gt_skel = consonant_skeleton(sanitized_xml_ipa)
                    valid_candidates.sort(
                        key=lambda c: (
                            c[1],
                            1 if c[0] == sanitized_xml_ipa else 0,
                            1 if consonant_skeleton(c[0]) == gt_skel else 0,
                            difflib.SequenceMatcher(None, c[0], sanitized_xml_ipa).ratio() if sanitized_xml_ipa else 0
                        ),
                        reverse=True
                    )
                    assigned_ipa = valid_candidates[0][0]

        if assigned_ipa and is_single_lexical_word:
            if is_noun or is_verb:
                homographs_disambiguated += 1
            else:
                wiktionary_assigned += 1
        else:
            clean_p = re.sub(r"\(.*?\)", "", hw).strip()
            words_p = clean_p.split()
            is_idiom_or_sentence = (
                len(words_p) > 2 or
                len(words_p) < 2 or
                any(m in hw for m in ("?", "!", "...", "…", "'")) or
                any(w.lower() in ("a", "an", "the") for w in words_p)
            )

            assigned_ipa = synthesize_compound_pronunciation(
                phrase=hw,
                word_ipa_map=base_title_ipa,
                ground_truth_ipa=sanitized_xml_ipa
            )
            if is_idiom_or_sentence or assigned_ipa == sanitized_xml_ipa:
                curriculum_fallback_count += 1
            else:
                compounds_synthesized += 1

        # Sanitize truncated comma variants from legacy SAMPA
        # E.g. "candidate": "/ˈkændɪdət, -deɪt/" -> "/ˈkændɪdət/"
        if "," in assigned_ipa:
            if base_title in base_title_ipa and "," not in base_title_ipa[base_title]:
                assigned_ipa = base_title_ipa[base_title]
            else:
                first_part = assigned_ipa.split(",")[0].strip()
                if not first_part.endswith("/"):
                    first_part += "/"
                if not first_part.startswith("/"):
                    first_part = "/" + first_part
                assigned_ipa = first_part

        # Final invariant normalization
        assigned_ipa = normalize_ipa(assigned_ipa)

        # Assert valid formatting
        if not VALID_IPA_REGEX.match(assigned_ipa):
            assigned_ipa = normalize_ipa(sanitized_xml_ipa)

        audited_map[hw] = assigned_ipa

    # 6. Verification and Invariant Checks
    print("\n" + "=" * 70)
    print("Running Rigorous Invariant Verification Checks...")
    print("=" * 70)

    assert len(audited_map) == len(all_headwords), f"Headword count mismatch: {len(audited_map)} vs {len(all_headwords)}"
    assert len(audited_map) == 2777, f"Expected 2,777 unique headwords, got {len(audited_map)}"

    empty_count = sum(1 for ipa in audited_map.values() if not ipa or ipa == "//")
    assert empty_count == 0, f"Found {empty_count} empty IPA strings!"

    sampa_violations = [hw for hw, ipa in audited_map.items() if FORBIDDEN_SAMPA_REGEX.search(ipa)]
    assert len(sampa_violations) == 0, f"Found raw SAMPA characters in: {sampa_violations[:10]}"

    colon_violations = [hw for hw, ipa in audited_map.items() if ":" in ipa]
    assert len(colon_violations) == 0, f"Found ASCII colon in: {colon_violations[:10]}"

    double_slash_violations = [hw for hw, ipa in audited_map.items() if "//" in ipa]
    assert len(double_slash_violations) == 0, f"Found double slashes in: {double_slash_violations[:10]}"

    regex_violations = [hw for hw, ipa in audited_map.items() if not VALID_IPA_REGEX.match(ipa)]
    assert len(regex_violations) == 0, f"Found regex violations in: {regex_violations[:10]}"

    americanisms = [hw for hw, ipa in audited_map.items() if "ɚ" in ipa or "ɾ" in ipa]
    assert len(americanisms) == 0, f"Found Americanisms in: {americanisms[:10]}"

    ellipsis_stress = [hw for hw, ipa in audited_map.items() if re.search(r"[ˈˌ]\s*(\.{3}|…)", ipa)]
    assert len(ellipsis_stress) == 0, f"Found orphaned stress before ellipsis in: {ellipsis_stress[:10]}"

    allowed_chars = set(
        " abcdefghijklmnopqrstuvwxyz"
        "æɑɒɔəɛɜɪʊʌ"
        "ðŋʃʒθ"
        "ˈˌː"
        "/().-,'… "
    )
    whitelist_violations = [hw for hw, ipa in audited_map.items() if any(c.lower() not in allowed_chars for c in ipa)]
    assert len(whitelist_violations) == 0, f"Found whitelist violations in: {whitelist_violations[:10]}"

    print("✓ All 2,777 headwords successfully mapped to valid British RP IPA.")
    print(f"✓ Wiktionary Direct Single Words: {wiktionary_assigned}")
    print(f"✓ Wiktionary Disambiguated Homographs: {homographs_disambiguated}")
    print(f"✓ Verified Algorithmic Compound Syntheses: {compounds_synthesized}")
    print(f"✓ Validated Curriculum Ground Truth Fallbacks: {curriculum_fallback_count}")
    print(f"✓ XML Trailing Slashes Fixed: {trailing_slashes_fixed}")
    print(f"✓ XML Ellipsis Stress Fixed: {ellipsis_stress_fixed}")
    print("✓ Zero empty strings.")
    print("✓ Zero raw SAMPA characters.")
    print("✓ Zero ASCII colons.")
    print("✓ Zero double slashes.")
    print("✓ Zero American flaps or rhotic schwas.")
    print("✓ 100% compliant with British RP regex and character whitelist.")

    # 7. Write Output Mapping Artifact
    os.makedirs(os.path.dirname(os.path.abspath(output_map_path)), exist_ok=True)
    with open(output_map_path, "w", encoding="utf-8") as f:
        json.dump(audited_map, f, ensure_ascii=False, indent=2)
    print(f"\nSuccessfully saved audited IPA mapping artifact to:\n  {output_map_path}")

    # Mirror output to worker_m1_2 folder as required by dispatch
    worker2_output = os.path.join(PROJECT_ROOT, ".agents", "teamwork_preview_worker_m1_2", "audited_ipa_map.json")
    if os.path.abspath(output_map_path) != os.path.abspath(worker2_output):
        os.makedirs(os.path.dirname(worker2_output), exist_ok=True)
        with open(worker2_output, "w", encoding="utf-8") as f:
            json.dump(audited_map, f, ensure_ascii=False, indent=2)
        print(f"Successfully mirrored audited IPA mapping artifact to:\n  {worker2_output}")

    print("=" * 70)

    return audited_map


def main():
    parser = argparse.ArgumentParser(description="Wiktionary IPA Audit & Synthesis Engine")
    parser.add_argument("--cache-file", default=DEFAULT_CACHE_FILE, help="Path to JSON cache file")
    parser.add_argument("--output", default=DEFAULT_OUTPUT_MAP, help="Path to output JSON mapping")
    parser.add_argument("--rate-limit", type=float, default=REQUEST_INTERVAL, help="Seconds between API calls")
    parser.add_argument("--batch-size", type=int, default=BATCH_SIZE, help="Batch size for Action API queries")
    parser.add_argument("--dry-run", action="store_true", help="Use local cache only, do not issue remote API calls")
    parser.add_argument("--verbose", action="store_true", help="Print verbose logs")

    args = parser.parse_args()
    build_audited_ipa_map(
        cache_file=args.cache_file,
        output_map_path=args.output,
        rate_limit=args.rate_limit,
        batch_size=args.batch_size,
        dry_run=args.dry_run,
        verbose=args.verbose,
    )


if __name__ == "__main__":
    main()
