"""
wiktionary_ipa — Fast, automated British English (RP) IPA extractor and verifier
querying en.wiktionary.org live.
"""

from typing import Dict, List, Optional
from .client import WiktionaryClient
from .dialects import VALID_IPA_REGEX, FORBIDDEN_SAMPA_REGEX
from .normalizer import is_valid_ipa, normalize_ipa, phonetically_equivalent, simplify_phonetics
from .parser import IPACandidate, clean_lookup_title, parse_wiktionary_rp_candidates, select_best_ipa
from .prosody import synthesize_compound_ipa

__version__ = "1.0.0"
__all__ = [
    "WiktionaryClient",
    "IPACandidate",
    "lookup",
    "batch_lookup",
    "verify_word",
    "normalize_ipa",
    "phonetically_equivalent",
    "is_valid_ipa",
    "simplify_phonetics",
    "select_best_ipa",
    "synthesize_compound_ipa",
    "clean_lookup_title",
]


def lookup(word: str, client: Optional[WiktionaryClient] = None) -> Optional[str]:
    """
    Looks up a word live on en.wiktionary.org and returns its top British English (RP) IPA.
    Falls back to compound synthesis for multi-word phrases if not indexed directly.
    Returns None if not found or no valid RP transcription exists.
    """
    c = client or WiktionaryClient()
    title = clean_lookup_title(word)
    wikitext = c.fetch_page(title)
    if wikitext:
        candidates = parse_wiktionary_rp_candidates(wikitext, headword=word)
        best = select_best_ipa(candidates, word=word)
        if best:
            return best

    # Fallback to constituent compound synthesis if multi-word phrase
    clean_words = word.strip().split()
    if len(clean_words) >= 2:
        sub_ipas = batch_lookup(clean_words, client=c)
        if all(sub_ipas.get(w) for w in clean_words):
            return synthesize_compound_ipa(word, {w: sub_ipas[w] for w in clean_words})

    return None


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
        results[word] = select_best_ipa(candidates, word=word)

    # Fallback synthesis for unresolved multi-word phrases
    unresolved = [w for w in words if results[w] is None and len(w.strip().split()) >= 2]
    if unresolved:
        needed_subwords = list({sw for w in unresolved for sw in w.strip().split() if not results.get(sw)})
        if needed_subwords:
            sub_results = batch_lookup(needed_subwords, client=c)
            for sw, ipa in sub_results.items():
                if ipa:
                    results[sw] = ipa

        for w in unresolved:
            sw_list = w.strip().split()
            if all(results.get(sw) for sw in sw_list):
                results[w] = synthesize_compound_ipa(w, {sw: results[sw] for sw in sw_list})

    return results


def verify_word(word: str, expected_ipa: str, client: Optional[WiktionaryClient] = None) -> Dict[str, any]:
    """
    Verifies an expected IPA against live British RP pronunciations on Wiktionary:
    returns {"status": "MATCH" | "EQUIVALENT" | "DISCREPANCY" | "NOT_FOUND", ...}.
    """
    c = client or WiktionaryClient()
    title = clean_lookup_title(word)
    wikitext = c.fetch_page(title)

    candidates: List[IPACandidate] = []
    if wikitext:
        candidates = parse_wiktionary_rp_candidates(wikitext, headword=word)

    best_web = select_best_ipa(candidates, word=word)
    if not best_web:
        # Fallback compound synthesis
        clean_words = word.strip().split()
        if len(clean_words) >= 2:
            sub_ipas = batch_lookup(clean_words, client=c)
            if all(sub_ipas.get(w) for w in clean_words):
                best_web = synthesize_compound_ipa(word, {w: sub_ipas[w] for w in clean_words})

    if not best_web:
        return {"word": word, "status": "NOT_FOUND", "expected_ipa": expected_ipa, "web_ipa": None}

    web_ipas = [c.ipa for c in candidates if c.score >= 10] or [best_web]

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
            "all_web_ipas": web_ipas[:3],
        }
