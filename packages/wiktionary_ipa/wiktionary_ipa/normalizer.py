"""
normalizer.py — Normalizes raw Wiktionary phonetic transcriptions to standard British RP
and provides phonetic equivalence comparison.
"""

import re
from typing import Optional
from .dialects import FORBIDDEN_SAMPA_REGEX, VALID_IPA_REGEX


def normalize_ipa(raw: str) -> str:
    """
    Normalizes a phonetic string to clean British Received Pronunciation broad slash notation:
    - Strips syllable dots (.), turned-r (ɹ -> r), and ligature tie bars (͡, ͜).
    - Strips Unicode combining diacritical marks (U+0300 to U+036F).
    - Maps American rhoticism (ɚ -> ə, ɝ -> ɜː) and alveolar tap (ɾ -> t).
    - Normalizes open-mid vowel (ɛ -> e) and script g (ɡ -> g).
    - Standardizes ASCII colons (:) to Unicode length mark (ː).
    - Strips orphaned stress marks before ellipsis (ˈ... -> ...).
    """
    if not raw:
        return ""
    text = re.sub(r"<[^>]+>", "", raw).strip()
    if text.startswith("[") and text.endswith("]"):
        inner = text[1:-1]
    elif text.startswith("/") and text.endswith("/"):
        inner = text[1:-1]
    else:
        inner = text

    inner = inner.replace(".", "")
    inner = inner.replace("ɹ", "r")
    inner = inner.replace("(ɹ)", "(r)")
    inner = inner.replace("͡", "").replace("͜", "")
    inner = re.sub(r"[\u0300-\u036f]", "", inner)
    inner = inner.replace("ɚ", "ə").replace("ɝ", "ɜː")
    inner = inner.replace("ɾ", "t")
    inner = inner.replace("ɛ", "e")
    inner = inner.replace("ɡ", "g")
    inner = inner.replace(":", "ː")
    inner = re.sub(r"\s+", " ", inner).strip()
    inner = re.sub(r"[ˈˌ]\s*(\.{3}|…)", r"\1", inner)

    return f"/{inner}/"


def is_valid_ipa(ipa: str) -> bool:
    """Checks whether an IPA string strictly satisfies British RP character format."""
    if not ipa or not (ipa.startswith("/") and ipa.endswith("/")):
        return False
    if len(ipa) <= 2:
        return False
    if FORBIDDEN_SAMPA_REGEX.search(ipa):
        return False
    return bool(VALID_IPA_REGEX.match(ipa))


def simplify_phonetics(s: str) -> str:
    """
    Simplifies phonetic transcription for dialect and variant equivalence checking:
    ignores stress marks, optional yod, linking rhoticity, syllabic consonants, and optional suffixes.
    """
    s = s.strip("/").lower()
    s = re.sub(r"\([sz]\)", "", s)
    s = re.sub(r"[ˈˌ\s\(\)]", "", s)
    s = s.replace("(r)", "").replace("r", "")
    s = s.replace("ː", "")
    s = s.replace("(j)", "").replace("j", "")
    s = s.replace("ʃən", "ʃn")
    s = s.replace("fəl", "fl")
    s = s.replace("bəl", "bl")
    s = s.replace("təl", "tl")
    s = s.replace("dəl", "dl")
    s = s.replace("məl", "ml")
    s = s.replace("səl", "sl")
    s = s.replace("zəl", "zl")
    s = s.replace("vəl", "vl")
    s = s.replace("eə", "e")
    return s


def phonetically_equivalent(ipa1: str, ipa2: str) -> bool:
    """Checks whether two transcriptions represent equivalent standard British RP variants."""
    if not ipa1 or not ipa2:
        return False
    if ipa1 == ipa2:
        return True
    return simplify_phonetics(ipa1) == simplify_phonetics(ipa2)
