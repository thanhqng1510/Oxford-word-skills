"""
wiktionary_ipa — Fast, automated British English (RP) IPA extractor and verifier
querying en.wiktionary.org live.
"""

from typing import Dict, List, Optional
from .client import WiktionaryClient
from .dialects import VALID_IPA_REGEX, FORBIDDEN_SAMPA_REGEX
from .normalizer import is_valid_ipa, normalize_ipa, phonetically_equivalent, simplify_phonetics
from .parser import clean_lookup_title, parse_wiktionary_rp_candidates
from .prosody import synthesize_compound_ipa

__version__ = "1.0.0"
__all__ = [
    "WiktionaryClient",
    "lookup",
    "batch_lookup",
    "verify_word",
    "normalize_ipa",
    "phonetically_equivalent",
    "is_valid_ipa",
    "simplify_phonetics",
    "synthesize_compound_ipa",
    "clean_lookup_title",
]


def lookup(word: str, client: Optional[WiktionaryClient] = None) -> Optional[str]:
    """
    Looks up a word live on en.wiktionary.org and returns its top British English (RP) IPA.
    Returns None if not found or no valid RP transcription exists.
    """
    c = client or WiktionaryClient()
    title = clean_lookup_title(word)
    wikitext = c.fetch_page(title)
    if not wikitext:
        return None

    candidates = parse_wiktionary_rp_candidates(wikitext, headword=word)
    valid = [cand for cand in candidates if cand[1] >= 10]
    if not valid:
        return None

    valid.sort(key=lambda x: x[1], reverse=True)
    best_ipas = [x[0] for x in valid]

    # Handle homographs
    if word.endswith(" N") and any(p.startswith("/ˈ") for p in best_ipas):
        return next(p for p in best_ipas if p.startswith("/ˈ"))
    if word.endswith(" V") and any(not p.startswith("/ˈ") and "ˈ" in p for p in best_ipas):
        return next(p for p in best_ipas if not p.startswith("/ˈ") and "ˈ" in p)

    return best_ipas[0]


def batch_lookup(words: List[str], client: Optional[WiktionaryClient] = None) -> Dict[str, Optional[str]]:
    """
    Looks up a batch of words concurrently over live Wiktionary API.
    Returns mapping of {word: ipa_or_None}.
    """
    c = client or WiktionaryClient()
    titles = [clean_lookup_title(w) for w in words]
    pages = c.fetch_all(titles)

    results: Dict[str, Optional[str]] = {}
    for word in words:
        title = clean_lookup_title(word)
        wikitext = pages.get(title)
        if not wikitext:
            results[word] = None
            continue

        candidates = parse_wiktionary_rp_candidates(wikitext, headword=word)
        valid = [cand for cand in candidates if cand[1] >= 10]
        if not valid:
            results[word] = None
            continue

        valid.sort(key=lambda x: x[1], reverse=True)
        best_ipas = [x[0] for x in valid]

        if word.endswith(" N") and any(p.startswith("/ˈ") for p in best_ipas):
            results[word] = next(p for p in best_ipas if p.startswith("/ˈ"))
        elif word.endswith(" V") and any(not p.startswith("/ˈ") and "ˈ" in p for p in best_ipas):
            results[word] = next(p for p in best_ipas if not p.startswith("/ˈ") and "ˈ" in p)
        else:
            results[word] = best_ipas[0]

    return results


def verify_word(word: str, expected_ipa: str, client: Optional[WiktionaryClient] = None) -> Dict[str, any]:
    """
    Verifies an expected IPA against live British RP pronunciations on Wiktionary:
    returns {"status": "MATCH" | "EQUIVALENT" | "DISCREPANCY" | "NOT_FOUND", ...}.
    """
    c = client or WiktionaryClient()
    title = clean_lookup_title(word)
    wikitext = c.fetch_page(title)
    if not wikitext:
        return {"word": word, "status": "NOT_FOUND", "expected_ipa": expected_ipa, "web_ipa": None}

    candidates = parse_wiktionary_rp_candidates(wikitext, headword=word)
    valid = [cand for cand in candidates if cand[1] >= 10]
    if not valid:
        return {"word": word, "status": "NOT_FOUND", "expected_ipa": expected_ipa, "web_ipa": None}

    valid.sort(key=lambda x: x[1], reverse=True)
    web_ipas = [x[0] for x in valid]
    best_web = web_ipas[0]

    if word.endswith(" N") and any(p.startswith("/ˈ") for p in web_ipas):
        best_web = next(p for p in web_ipas if p.startswith("/ˈ"))
    elif word.endswith(" V") and any(not p.startswith("/ˈ") and "ˈ" in p for p in web_ipas):
        best_web = next(p for p in web_ipas if not p.startswith("/ˈ") and "ˈ" in p)

    if expected_ipa == best_web or expected_ipa in web_ipas:
        return {"word": word, "status": "MATCH", "expected_ipa": expected_ipa, "web_ipa": best_web}
    elif any(phonetically_equivalent(expected_ipa, p) for p in web_ipas):
        return {"word": word, "status": "EQUIVALENT", "expected_ipa": expected_ipa, "web_ipa": best_web}
    else:
        return {
            "word": word,
            "status": "DISCREPANCY",
            "expected_ipa": expected_ipa,
            "web_ipa": best_web,
            "all_web_ipas": web_ipas[:3]
        }
