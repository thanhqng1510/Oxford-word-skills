# scripts/ — IPA Maintenance Toolkit

This directory provides tools to keep Oxford Word Skills vocabulary
pronunciations accurate, complete, and up to date.

---

## Quick reference

| Script | What it does | When to run |
|---|---|---|
| `verify_ipa_live.py` | Automated live web audit against Wiktionary (no cache) | **Verification / Automation** — checks all words live on the web in ~45s |
| `check_ipa.py` | Fast local audit of all IPA entries (< 1s, no network) | **Pre-commit / CI** — instant syntax & invariant check |
| `update_ipa.py` | Fetches IPA from Wiktionary for new/missing words | When vocabulary is added |
| `audit_wiktionary_ipa.py` | Full re-audit of all ~2,800 words against Wiktionary | Periodic (quarterly) re-verification |

---

## `verify_ipa_live.py` — Automated Live Web Auditor (no cache, ~45 seconds)

Directly queries `en.wiktionary.org` live via MediaWiki batch API (50 titles/request) and compares every curriculum entry against live British English (RP) pronunciations on the web. Zero LLM tokens required.

```bash
# Full live web audit across all 2,777 vocabulary entries
python3 scripts/verify_ipa_live.py

# Check a single word live against Wiktionary
python3 scripts/verify_ipa_live.py --word "abbreviation"
python3 scripts/verify_ipa_live.py --word "backward(s)"

# Verbose output showing exact comparisons
python3 scripts/verify_ipa_live.py --verbose

# Machine-readable JSON output for CI automation
python3 scripts/verify_ipa_live.py --json

# Automatically fix discrepancies using live Wiktionary data
python3 scripts/verify_ipa_live.py --fix
```

**What it verifies live against the web:**
- Fetches wikitext directly over HTTPS with rate limiting and gzip compression
- Dialect scoring filters out non-RP varieties (General American, Canadian, Australian, Scots, Northern English, Irish)
- Detects phonemic drift, homograph stress mismatches, and diphthong corruptions
- Evaluates phonetic equivalence (optional yod `(j)`, linking `(r)`, syllabic consonants `ʃn` vs `ʃən`, optional `(s)/(z)`)


---

## `check_ipa.py` — Fast local validator (< 1 second, no network)

```bash
# Summary report
python3 scripts/check_ipa.py

# Verbose — see every problem
python3 scripts/check_ipa.py --verbose

# Machine-readable JSON (for CI)
python3 scripts/check_ipa.py --json

# List every word and its IPA as TSV
python3 scripts/check_ipa.py --words | sort | less
```

**What it checks (both `definitions.json` and `extrawordlist.xml`):**
- Missing or empty IPA entries
- Not enclosed in `/…/`
- Lingering raw SAMPA characters (`%`, `&`, `"`, `Q`, `V`, etc.)
- Non-RP phonemes (`ɚ`, `ɝ`, `ɾ` — rhotic/tap, American English)
- Invalid IPA character set

Exit codes: `0` = all good, `1` = issues found.

---

## `update_ipa.py` — Delta updater (network required)

Use this whenever you **add new words** to the curriculum.

```bash
# Fetch and apply IPA for all missing/empty entries
python3 scripts/update_ipa.py

# Preview what would change without writing
python3 scripts/update_ipa.py --dry-run

# Update a specific word
python3 scripts/update_ipa.py --word "ameliorate"

# Force re-fetch from Wiktionary (ignore cache)
python3 scripts/update_ipa.py --force --word "nuance"
```

The script:
1. Finds all words with missing/invalid IPA in `definitions.json`
2. Checks the **local Wiktionary cache** first (`scripts/cache/wiktionary_cache.json`)
3. Only hits the network for genuinely new words (rate-limited: 1 req/s)
4. Extracts British English (Received Pronunciation) IPA
5. Writes updates to both `definitions.json` and `extrawordlist.xml`
6. Saves the updated cache for future runs

---

## `audit_wiktionary_ipa.py` — Full re-audit (periodic, network required)

This is the heavy tool used for the original Wiktionary audit (all ~2,800 words).
Run it when you want a complete ground-truth refresh, e.g. after significant
Wiktionary pronunciation updates.

```bash
# Full audit (uses cache, only fetches uncached entries)
python3 scripts/audit_wiktionary_ipa.py

# Re-fetch everything from Wiktionary (very slow — ~1h for full corpus)
python3 scripts/audit_wiktionary_ipa.py --force-refetch

# After audit, apply to data stores
python3 /tmp/harmonize_ipa.py      # (recreate from transcript if needed)
```

The audit map output (`audited_ipa_map.json`) is committed in the `.agents/`
working directory. Apply it using the harmonization approach in the PR.

---

## `cache/wiktionary_cache.json`

A local cache of ~3,000 Wiktionary page wikitexts (42 MB). It prevents
redundant network requests and makes subsequent runs instant for cached words.

- **Keep this committed** — it is the source of truth for IPA lookups.
- It is updated automatically by `update_ipa.py` and `audit_wiktionary_ipa.py`.
- Entry format: `{ "word": { "wikitext": "...", "ts": <unix_timestamp> } }`

---

## Workflow for adding new vocabulary

1. Add words to `Resources/extrawordlist.xml` and `Resources/definitions.json`.
2. Run `python3 scripts/update_ipa.py` to fetch and apply IPA for new entries.
3. Run `python3 scripts/check_ipa.py` to verify — should show 0 issues.
4. Run `python3 tests/run_all_tests.py` to confirm all 99 tests still pass.
5. Commit everything including the updated `scripts/cache/wiktionary_cache.json`.

---

## Integration with the test suite

`python3 tests/run_all_tests.py` (and `./run_e2e_tests.sh`) include IPA checks:

| Test | What it validates |
|---|---|
| `test_f9_07_runtime_words_ipa_completeness_and_format` | 100% non-empty, slash-enclosed IPA |
| `test_f9_08_runtime_words_ipa_no_lingering_sampa` | Zero SAMPA residue in runtime words |
| `test_t2_13_ipa_character_set_whitelist` | Only valid IPA characters |
| `test_t2_14_reject_bracketed_allophones` | No unresolved `[…]` allophones |
| `test_t2_15_reject_raw_sampa_tokens` | No raw SAMPA in output |
| `test_t2_16_reject_ascii_colons` | No unconverted `:` length marks |
| `test_t2_17_reject_americanisms` | No `ɚ`/`ɝ`/`ɾ` (US-specific phonemes) |
| `test_t4_09_full_curriculum_ipa_audit_all_80_units` | Full 80-unit sweep |
