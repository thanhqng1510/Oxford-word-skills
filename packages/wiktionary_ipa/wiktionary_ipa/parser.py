"""
parser.py — Wikitext section extraction, IPA template parsing, and dialect priority scoring.
"""

import re
from typing import Dict, List, NamedTuple, Optional, Tuple
from .dialects import (
    DISQUALIFY_KEYWORDS,
    FORBIDDEN_SAMPA_REGEX,
    GENERIC_UK_KEYWORDS,
    STANDARD_RP_KEYWORDS,
    VALID_IPA_REGEX,
)
from .normalizer import normalize_ipa


class IPACandidate(NamedTuple):
    """Represents a scored IPA pronunciation candidate."""
    ipa: str
    score: int

UNIT_MEASUREMENTS: Dict[str, str] = {
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


def clean_lookup_title(headword: str) -> str:
    """Extracts canonical dictionary lookup title from curriculum headwords."""
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


def extract_english_section(wikitext: str) -> str:
    """Extracts only the ==English== section from wikitext."""
    if not wikitext:
        return ""
    m = re.search(r"==\s*English\s*==(.*?)(?=\n==[^=]|\Z)", wikitext, re.DOTALL | re.IGNORECASE)
    return m.group(1) if m else ""


def parse_wiktionary_rp_candidates(wikitext: str, headword: str = "") -> List[IPACandidate]:
    """
    Parses candidate pronunciations from English wikitext, scored by British RP preference:
      +100: Explicit Received Pronunciation (RP / SSB)
      +90:  General British / UK
      +10:  Neutral (unspecified dialect in English section)
      -100: Disqualified dialects (US, Canada, Australia, Scotland, Northern English, etc.)
    """
    eng_text = extract_english_section(wikitext)
    if not eng_text:
        return []

    candidates: List[IPACandidate] = []
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
                candidates.append(IPACandidate(ipa=norm, score=score))

    return candidates


def select_best_ipa(candidates: List[IPACandidate], word: str = "") -> Optional[str]:
    """Selects the top British RP IPA transcription from candidates, handling homographs."""
    valid = [c for c in candidates if c.score >= 10]
    if not valid:
        return None
    valid.sort(key=lambda c: c.score, reverse=True)
    best_ipas = [c.ipa for c in valid]

    # Handle homographs: "record N" vs "record V"
    if word.endswith(" N") and any(p.startswith("/ˈ") for p in best_ipas):
        return next(p for p in best_ipas if p.startswith("/ˈ"))
    if word.endswith(" V") and any(not p.startswith("/ˈ") and "ˈ" in p for p in best_ipas):
        return next(p for p in best_ipas if not p.startswith("/ˈ") and "ˈ" in p)

    return best_ipas[0]
