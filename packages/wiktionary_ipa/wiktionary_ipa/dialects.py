"""
dialects.py — Dialect keywords, priority scoring, and phonological invariants for British RP.
"""

import re

# Broad phonemic British RP IPA character whitelist
VALID_IPA_REGEX = re.compile(
    r"^/[a-zæɑɒɔəɛɜɪʊʌbcdefɡhijklmnŋpqrstuvwzðθʃʒˈˌːɹ\s\-\,\.\(\)\…\u2019\']+/$"
)
FORBIDDEN_SAMPA_REGEX = re.compile(r'[%&"”QVUITAODSZ23@ÍÙ]')

STANDARD_RP_KEYWORDS = [
    "rp",
    "received pronunciation",
    "ssb",
    "standard southern british",
]

GENERIC_UK_KEYWORDS = [
    "uk",
    "british",
    "southern england",
    "southern british",
    "england",
    "non-rhotic",
]

DISQUALIFY_KEYWORDS = [
    "ga",
    "genam",
    "general american",
    "us",
    "usa",
    "united states",
    "ca",
    "canada",
    "canadian",
    "au",
    "australia",
    "australian",
    "nz",
    "new zealand",
    "scotland",
    "scottish",
    "scots",
    "wales",
    "welsh",
    "ireland",
    "irish",
    "northumbria",
    "geordie",
    "aave",
    "flapping",
    "t-flapping",
    "archaic",
    "obsolete",
    "triphthong smoothing",
    "smoothing",
    "dialectal",
    "south asia",
    "indian",
    "pakistan",
    "mle",
    "dated",
    "rare",
]
