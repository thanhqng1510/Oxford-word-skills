# wiktionary-ipa

A fast, lightweight, standalone Python library to extract, normalize, and verify **British English (Received Pronunciation / RP)** International Phonetic Alphabet (IPA) transcriptions directly from [en.wiktionary.org](https://en.wiktionary.org).

Zero external dependencies — standard library only.

---

## Installation

```bash
pip install -e packages/wiktionary_ipa
```

Or copy the `wiktionary_ipa/` folder directly into your Python project.

---

## Quick Python API

```python
import wiktionary_ipa as wipa

# 1. Single Word Lookup (Live Web)
ipa = wipa.lookup("abbreviation")
print(ipa)  # /əˌbriːviˈeɪʃən/

# 2. Batch Lookup (Batched MediaWiki API, 50 titles/request)
results = wipa.batch_lookup(["apple", "banana", "record N", "record V"])
# {
#   "apple": "/ˈæp.əl/",
#   "banana": "/bəˈnɑː.nə/",
#   "record N": "/ˈrekɔːd/",
#   "record V": "/rɪˈkɔːd/"
# }

# 3. Verify Word Against Live Web
res = wipa.verify_word("backward(s)", "/ˈbækwəd(z)/")
print(res["status"])  # 'EQUIVALENT' (matches live /bækwə(r)d/)

# 4. Phonetic Equivalence Check
wipa.phonetically_equivalent("/ˈbækwəd(z)/", "/ˈbækwə(r)d/")  # True
wipa.phonetically_equivalent("/əˈdɪʃn/", "/əˈdɪʃən/")         # True

# 5. Normalizer
wipa.normalize_ipa("[ˈbeɾə]")  # '/ˈbetə/'
```

---

## CLI Usage

```bash
# Lookup single word
python3 -m wiktionary_ipa.cli "abbreviation"
# abbreviation: /əˌbriːviˈeɪʃən/

# Batch lookup
python3 -m wiktionary_ipa.cli apple banana cucumber

# Verify expected pronunciation against live Wiktionary
python3 -m wiktionary_ipa.cli --verify "sea bass" "/ˈsiː bæs/"
# Word: sea bass
# Status: MATCH
# Expected: /ˈsiː bæs/
# Live Web: /ˈsiː bæs/

# JSON output for CI automation
python3 -m wiktionary_ipa.cli --verify "backward(s)" "/ˈbækwəd(z)/" --json
```

---

## Features

- **Live MediaWiki Action API Client**: Batches up to 50 titles per query with gzip compression and rate-limiting.
- **Dialect Priority Scoring**: Prioritizes Received Pronunciation (`RP`, `SSB`) and British English while strictly disqualifying rhotic/American variants (`GA`, `US`, flaps, Canadian raising, Australian, Scottish).
- **Homograph Disambiguation**: Resolves noun initial stress vs verb second-syllable stress for words like `record`, `contrast`, `produce`.
- **Phonetic Equivalence**: Intelligently handles optional yods `(j)`, syllabic consonants (`ʃn` vs `ʃən`), linking `(r)`, and optional plural/adverbial markers `(s)/(z)`.
- **Compound Prosody**: Applies English nuclear stress and phrasal verb particle stress rules.
