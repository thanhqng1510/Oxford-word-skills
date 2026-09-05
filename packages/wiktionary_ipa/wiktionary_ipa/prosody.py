"""
prosody.py — English prosodic stress synthesis for compounds, phrases, and idioms.
"""

import re
from typing import Dict, List, Optional, Tuple
from .normalizer import is_valid_ipa, normalize_ipa

WEAK_FORMS: Dict[str, str] = {
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

PHRASAL_PARTICLES = {
    "up", "down", "in", "out", "on", "off", "away", "back",
    "over", "round", "around", "through", "across"
}


def synthesize_compound_ipa(
    phrase: str,
    word_ipa_map: Dict[str, str],
    fallback_ipa: Optional[str] = None
) -> str:
    """
    Synthesizes prosodic stress for multi-word phrases from constituent words:
    - Grammatical weak forms applied to function words.
    - Phrasal verbs: primary stress on particle, secondary on verb.
    - Compound nouns: nuclear stress on first element, secondary on second.
    """
    clean_p = re.sub(r"\(.*?\)", "", phrase).strip()
    clean_p = re.sub(r"\.{3}|…", "", clean_p).strip()
    words = clean_p.split()

    if len(words) < 2:
        return fallback_ipa or ""

    tokens: List[Tuple[str, str, bool]] = []
    for i, w in enumerate(words):
        w_clean = re.sub(r"[^\w\-]", "", w).lower()
        if not w_clean:
            continue
        if w_clean in WEAK_FORMS and i < len(words) - 1:
            tokens.append((w_clean, WEAK_FORMS[w_clean].strip("/"), True))
        elif w_clean in word_ipa_map:
            tokens.append((w_clean, word_ipa_map[w_clean].strip("/"), False))
        else:
            return fallback_ipa or ""

    is_phrasal_verb = (len(words) == 2 and words[1].lower() in PHRASAL_PARTICLES)
    syllables: List[str] = []

    if is_phrasal_verb:
        verb_ipa = tokens[0][1].replace("ˈ", "ˌ")
        if not verb_ipa.startswith("ˌ"):
            verb_ipa = "ˌ" + verb_ipa
        particle_ipa = tokens[1][1]
        if not particle_ipa.startswith("ˈ"):
            particle_ipa = "ˈ" + particle_ipa
        syllables = [verb_ipa, particle_ipa]
    else:
        # Nuclear stress on first element for compounds
        for i, (w_clean, base_ipa, is_weak) in enumerate(tokens):
            if is_weak:
                syllables.append(base_ipa)
            elif i == 0:
                syllables.append(base_ipa)
            else:
                syllables.append(base_ipa.replace("ˈ", "ˌ"))

    synthesized = normalize_ipa(f"/{' '.join(syllables)}/")
    if is_valid_ipa(synthesized):
        return synthesized
    return fallback_ipa or synthesized
