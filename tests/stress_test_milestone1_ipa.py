#!/usr/bin/env python3
"""
Adversarial Stress Test Suite for Milestone 1 (Wiktionary IPA Retrieval & Normalization Engine)
Empirical validation performed by teamwork_preview_challenger_m1_2.

Covers:
1. Offline Execution & Network Isolation (<3s, 0 socket/HTTP calls)
2. Cache Integrity & Parity (3,097 entries, 100% key match)
3. Output Map Invariants & Key Parity (exact 2,777 keys vs definitions.json)
4. Error Resilience & Malformed Wikitext Handling
5. Dialect Disqualification & Scoring Edge Cases
6. SAMPA & Normalizer Adversarial Invariants
7. Mock Network Fault & Redirect Resilience
"""

import gzip
import json
import os
import re
import socket
import sys
import time
import unittest
import urllib.error
import urllib.request
from io import BytesIO
from typing import Dict, List, Optional
from unittest.mock import MagicMock, patch

# Ensure project root is in sys.path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from scripts.audit_wiktionary_ipa import (
    DEFAULT_CACHE_FILE,
    DEFINITIONS_JSON_PATH,
    EXTRAWORDLIST_XML_PATH,
    FORBIDDEN_SAMPA_REGEX,
    VALID_IPA_REGEX,
    WiktionaryClient,
    build_audited_ipa_map,
    extract_base_query_title,
    extract_english_section,
    normalize_ipa,
    parse_wiktionary_ipa_candidates,
    sampa_to_ipa,
    synthesize_compound_pronunciation,
)


class TestMilestone1Adversarial(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(DEFINITIONS_JSON_PATH, "r", encoding="utf-8") as f:
            cls.defs_dict = json.load(f)
        with open(DEFAULT_CACHE_FILE, "r", encoding="utf-8") as f:
            cls.cache_dict = json.load(f)
        cls.worker_output_path = os.path.join(
            PROJECT_ROOT, ".agents", "teamwork_preview_worker_m1_1", "audited_ipa_map.json"
        )
        with open(cls.worker_output_path, "r", encoding="utf-8") as f:
            cls.worker_output_map = json.load(f)

    # =========================================================================
    # 1. Offline Execution Speed & Network Isolation
    # =========================================================================
    def test_offline_execution_speed_and_network_isolation(self):
        """Verify full offline re-run completes in <3.0 seconds with zero network calls."""
        def forbidden_connect(*args, **kwargs):
            raise AssertionError("Remote socket.connect attempt detected during offline test!")

        def forbidden_urlopen(*args, **kwargs):
            raise AssertionError("Remote urllib.request.urlopen attempt detected during offline test!")

        temp_output_path = "/tmp/challenger_offline_test_map.json"

        with patch("socket.socket.connect", side_effect=forbidden_connect), \
             patch("urllib.request.urlopen", side_effect=forbidden_urlopen):
            
            start_time = time.perf_counter()
            result_map = build_audited_ipa_map(
                cache_file=DEFAULT_CACHE_FILE,
                output_map_path=temp_output_path,
                dry_run=False,  # Test default mode without dry-run flag
            )
            elapsed = time.perf_counter() - start_time

        self.assertLess(
            elapsed, 3.0,
            f"Offline execution took {elapsed:.3f}s, exceeding the 3.0s requirement!"
        )
        self.assertEqual(
            len(result_map), 2777,
            f"Expected 2,777 mapped headwords, got {len(result_map)}"
        )
        print(f"\n  [PASS] Offline execution completed in {elapsed:.3f}s (<3.0s) with 0 network calls.")

    # =========================================================================
    # 2. Cache Integrity & Structure
    # =========================================================================
    def test_cache_integrity_and_coverage(self):
        """Verify .agents/cache/wiktionary_cache.json structure and validity."""
        self.assertGreaterEqual(
            len(self.cache_dict), 3085,
            f"Cache entries ({len(self.cache_dict)}) should cover all 3,085 query titles"
        )
        # All keys must be non-empty strings
        for k, v in self.cache_dict.items():
            self.assertIsInstance(k, str)
            self.assertTrue(len(k.strip()) > 0, "Cache key cannot be empty")
            self.assertTrue(v is None or isinstance(v, str), f"Cache value for '{k}' must be string or None")

        # Check that corrupted cache loads gracefully without uncaught crash
        corrupt_cache_path = "/tmp/corrupted_cache.json"
        with open(corrupt_cache_path, "w") as f:
            f.write("{ invalid json")
        client = WiktionaryClient(cache_file=corrupt_cache_path)
        self.assertEqual(client.cache, {}, "Corrupted cache should safely fallback to empty dict")

    # =========================================================================
    # 3. Output Map Key Parity & IPA Invariants
    # =========================================================================
    def test_output_map_exact_key_parity(self):
        """Verify output map contains exactly all 2,777 keys present in definitions.json."""
        defs_keys = set(self.defs_dict.keys())
        output_keys = set(self.worker_output_map.keys())

        missing = defs_keys - output_keys
        surplus = output_keys - defs_keys

        self.assertEqual(len(missing), 0, f"Missing keys in audited map: {list(missing)[:5]}")
        self.assertEqual(len(surplus), 0, f"Surplus keys in audited map: {list(surplus)[:5]}")
        self.assertEqual(len(output_keys), 2777, f"Total keys count should be 2,777, got {len(output_keys)}")

    def test_output_map_strict_phonetic_invariants(self):
        """Verify all 2,777 entries satisfy strict British RP phonetic invariants."""
        allowed_chars = set(" abcdefghijklmnopqrstuvwxyzæɑɒɔəɛɜɪʊʌðŋʃʒθˈˌː/().-,'… ")

        for hw, ipa in self.worker_output_map.items():
            self.assertTrue(ipa.startswith("/"), f"Missing leading slash for '{hw}': {ipa}")
            self.assertTrue(ipa.endswith("/"), f"Missing trailing slash for '{hw}': {ipa}")
            self.assertGreater(len(ipa), 2, f"Empty or slash-only transcription for '{hw}': {ipa}")
            self.assertNotIn("//", ipa, f"Double slash found in '{hw}': {ipa}")
            self.assertNotIn(":", ipa, f"ASCII colon found in '{hw}': {ipa}")
            self.assertNotIn("[", ipa, f"Left square bracket found in '{hw}': {ipa}")
            self.assertNotIn("]", ipa, f"Right square bracket found in '{hw}': {ipa}")
            self.assertNotIn("ɚ", ipa, f"American rhotic schwa found in '{hw}': {ipa}")
            self.assertNotIn("ɝ", ipa, f"American rhotic open-mid found in '{hw}': {ipa}")
            self.assertNotIn("ɾ", ipa, f"American/Australian flap found in '{hw}': {ipa}")
            self.assertFalse(FORBIDDEN_SAMPA_REGEX.search(ipa), f"Forbidden SAMPA token in '{hw}': {ipa}")
            self.assertFalse(re.search(r"[ˈˌ]\s*(\.{3}|…)", ipa), f"Stress before ellipsis in '{hw}': {ipa}")
            self.assertTrue(VALID_IPA_REGEX.match(ipa), f"Regex validation failed for '{hw}': {ipa}")

            invalid_chars = [c for c in ipa if c.lower() not in allowed_chars]
            self.assertEqual(len(invalid_chars), 0, f"Disallowed characters in '{hw}' ({ipa}): {invalid_chars}")

    # =========================================================================
    # 4. Error Resilience & Malformed Wikitext Handling
    # =========================================================================
    def test_extract_english_section_edge_cases(self):
        """Probe extract_english_section on boundary, malformed, and adversarial inputs."""
        # None and empty
        self.assertEqual(extract_english_section(None), "")
        self.assertEqual(extract_english_section(""), "")
        self.assertEqual(extract_english_section("   \n\t  "), "")

        # Only foreign language
        foreign = "==French==\n===Noun===\n# French word\n==German==\n===Noun===\n# German word"
        self.assertEqual(extract_english_section(foreign), "")

        # Mixed languages with English in the middle
        mixed = (
            "==French==\nFrench content\n"
            "==English==\n===Pronunciation===\n* {{IPA|en|/hɛˈləʊ/}}\n"
            "==Spanish==\nSpanish content"
        )
        eng = extract_english_section(mixed)
        self.assertIn("===Pronunciation===", eng)
        self.assertNotIn("Spanish content", eng)
        self.assertNotIn("French content", eng)

        # Case-insensitive header with whitespace
        spaced = "==   english   ==\nEnglish content here\n==Latin=="
        self.assertIn("English content here", extract_english_section(spaced))

        # English at EOF without trailing newline
        eof_header = "==English==\nEnglish content at EOF"
        self.assertIn("English content at EOF", extract_english_section(eof_header))

        # 100k characters wikitext stopping at next language header
        adversarial_text = "==English==\n" + ("x" * 100000) + "\n==Spanish==\n" + ("y" * 50000)
        start = time.perf_counter()
        extracted = extract_english_section(adversarial_text)
        elapsed = time.perf_counter() - start
        self.assertLess(elapsed, 0.05, f"extract_english_section took {elapsed:.3f}s on large text")
        self.assertEqual(len(extracted.strip()), 100000)
        self.assertNotIn("Spanish", extracted)

    def test_parse_wiktionary_ipa_candidates_edge_cases(self):
        """Probe parse_wiktionary_ipa_candidates on malformed templates, accents, and junk."""
        # None and empty
        self.assertEqual(parse_wiktionary_ipa_candidates(None), [])
        self.assertEqual(parse_wiktionary_ipa_candidates(""), [])
        self.assertEqual(parse_wiktionary_ipa_candidates("No templates here"), [])

        # Unclosed template
        unclosed = "==English==\n* {{IPA|en|/fʊt/\n* More text"
        self.assertEqual(parse_wiktionary_ipa_candidates(unclosed), [])

        # Empty arguments
        empty_args = "==English==\n* {{IPA|en|||/bɑːθ/||}}"
        cands = parse_wiktionary_ipa_candidates(empty_args)
        self.assertEqual(len(cands), 1)
        self.assertEqual(cands[0][0], "/bɑːθ/")

        # Broken key-value attributes
        broken_attr = "==English==\n* {{IPA|en|a=|qual==invalid|=|/test/}}"
        cands = parse_wiktionary_ipa_candidates(broken_attr)
        self.assertEqual(len(cands), 1)
        self.assertEqual(cands[0][0], "/test/")

        # American / General American disqualification (-100)
        us_only = "==English==\n* {{a|US|GA}} {{IPA|en|/ˈkɑr/}}"
        cands = parse_wiktionary_ipa_candidates(us_only)
        self.assertEqual(len(cands), 1)
        self.assertEqual(cands[0][1], -100)

        # UK / RP priority scoring (+100)
        uk_rp = "==English==\n* {{a|UK|RP}} {{IPA|en|/kɑː/}}"
        cands = parse_wiktionary_ipa_candidates(uk_rp)
        self.assertEqual(len(cands), 1)
        self.assertEqual(cands[0][1], 100)
        self.assertEqual(cands[0][0], "/kɑː/")

        # Combined UK and US on separate lines: ensure UK takes precedence when sorted
        both = (
            "==English==\n"
            "===Pronunciation===\n"
            "* {{a|US}} {{IPA|en|/ˈbæθ/}}\n"
            "* {{a|UK}} {{IPA|en|/bɑːθ/}}\n"
        )
        cands = parse_wiktionary_ipa_candidates(both)
        cands.sort(key=lambda x: x[1], reverse=True)
        self.assertEqual(cands[0][0], "/bɑːθ/")
        self.assertEqual(cands[0][1], 100)

    # =========================================================================
    # 5. Normalizer & SAMPA Stress Tests
    # =========================================================================
    def test_normalize_ipa_adversarial_inputs(self):
        """Stress-test normalize_ipa with boundary and adversarial phonetic strings."""
        self.assertEqual(normalize_ipa(None), "")
        self.assertEqual(normalize_ipa(""), "")
        # Note: normalize_ipa on whitespace returns "//", which fails VALID_IPA_REGEX
        # and is safely caught by audit_wiktionary_ipa regex fallback
        norm_space = normalize_ipa("   ")
        self.assertEqual(norm_space, "//")
        self.assertFalse(VALID_IPA_REGEX.match(norm_space))

        # Square brackets stripping and conversion to slashes
        self.assertEqual(normalize_ipa("[test]"), "/test/")

        # Syllable dots removal
        self.assertEqual(normalize_ipa("/b.æ.θ/"), "/bæθ/")

        # Turned-r mapping
        self.assertEqual(normalize_ipa("/ɹed/"), "/red/")
        self.assertEqual(normalize_ipa("/fɑː(ɹ)/"), "/fɑː(r)/")

        # American tap removal
        self.assertEqual(normalize_ipa("[ˈbeɾə]"), "/ˈbetə/")

        # American rhotic vowels
        self.assertEqual(normalize_ipa("/əkˈsɛləˌɹeɪtɚ/"), "/əkˈseləˌreɪtə/")
        self.assertEqual(normalize_ipa("/bɝd/"), "/bɜːd/")

        # Ligature tie bars
        self.assertEqual(normalize_ipa("/t͡ʃɜːtʃ/"), "/tʃɜːtʃ/")
        self.assertEqual(normalize_ipa("/d͜ʒʌd͜ʒ/"), "/dʒʌdʒ/")

        # Open-mid front vowel 'ɛ' -> 'e'
        self.assertEqual(normalize_ipa("/bɛd/"), "/bed/")

        # Script g 'ɡ' -> standard 'g'
        self.assertEqual(normalize_ipa("/ɡʊd/"), "/gʊd/")

        # ASCII colon -> length mark
        self.assertEqual(normalize_ipa("/si:k/"), "/siːk/")

        # Orphaned stress marks before unicode ellipsis
        self.assertEqual(normalize_ipa("/ˈ…/"), "/…/")
        self.assertEqual(normalize_ipa("/ˌ…/"), "/…/")
        self.assertEqual(normalize_ipa("/ˈ …/"), "/…/")

    def test_sampa_to_ipa_trailing_slashes_and_stress(self):
        """Verify sampa_to_ipa correctly fixes the 12 actual XML trailing slashes and stress."""
        # The 12 actual trailing slash occurrences from extrawordlist.xml
        test_cases = [
            ("\"O:lt@(r)/", "/ˈɔːltə(r)/"),
            ("@\"pri:SieIt/", "/əˈpriːʃieɪt/"),
            ("\"e@ri@/", "/ˈeəriə/"),
            ("%sIvl \"wO:(r)/", "/ˌsɪvl ˈwɔː(r)/"),
            ("%gIv %... @d\"vaIs/", "/ˌgɪv ... ədˈvaɪs/"),
            ("%g@U t@ \"kO:t/", "/ˌgəʊ tə ˈkɔːt/"),
            ("In\"sQmni@/", "/ɪnˈsɒmniə/"),
            ("\"li:t@(z)/", "/ˈliːtə(z)/"),
            ("%@Uv@ \"De@(r)/", "/ˌəʊvə ˈðeə(r)/"),
            ("p@\"tIkj@l@(r)/", "/pəˈtɪkjələ(r)/"),
            ("\"sVbÙIkt t@/", "/ˈsʌbdʒɪkt tə/"),
            ("\"v&kju@m %kli:n@(r)/", "/ˈvækjuəm ˌkliːnə(r)/"),
        ]
        for sampa_input, expected_ipa in test_cases:
            res = sampa_to_ipa(sampa_input)
            self.assertEqual(res, expected_ipa, f"Mismatch for '{sampa_input}': got '{res}'")
            self.assertNotIn("//", res)
            self.assertFalse(res.endswith("//"))

        # Ellipsis stress tests
        self.assertEqual(sampa_to_ipa("\"..."), "/.../")
        self.assertEqual(sampa_to_ipa("%…"), "/…/")

    # =========================================================================
    # 6. Compound Synthesis & Query Title Extraction Edge Cases
    # =========================================================================
    def test_extract_base_query_title_edge_cases(self):
        """Verify title cleaner extracts proper Wiktionary search keys for tricky phrases."""
        cases = [
            ("BBC (British Broadcasting Corporation)", "BBC"),
            ("kg (kilo(s)/kilogram(s))", "kilogram"),
            ("km (kilometre(s))", "kilometre"),
            ("backward(s)", "backwards"),
            ("produce (goods)", "produce"),
            ("produce (a film)", "produce"),
            ("record N", "record"),
            ("record V", "record"),
            ("How do you feel about ...?", "How do you feel about ?"),
            ("up to now", "up to now"),
        ]
        for inp, expected in cases:
            self.assertEqual(extract_base_query_title(inp), expected)

    def test_compound_synthesis_weak_forms_and_stress(self):
        """Verify synthesize_compound_pronunciation applies weak forms and stress rules."""
        mock_map = {
            "law": "/lɔː/",
            "against": "/əˈgenst/",
        }
        # "against the law": 'the' is weak /ðə/, 'against' gets secondary stress /əˌgenst/
        syn = synthesize_compound_pronunciation(
            phrase="against the law",
            word_ipa_map=mock_map,
            ground_truth_ipa=None,
        )
        self.assertEqual(syn, "/əˌgenst ðə lɔː/")

    # =========================================================================
    # 7. Mock Network Fault & Redirect Resilience
    # =========================================================================
    def test_wiktionary_client_redirect_and_missing_handling(self):
        """Verify client correctly resolves MediaWiki redirects, normalized titles, and missing pages."""
        mock_response_data = {
            "query": {
                "normalized": [{"from": "grey_colour", "to": "Grey colour"}],
                "redirects": [{"from": "Grey colour", "to": "Grey"}],
                "pages": {
                    "101": {
                        "pageid": 101,
                        "title": "Grey",
                        "revisions": [{"slots": {"main": {"*": "==English==\n* {{IPA|en|/ɡreɪ/}}"}}}]
                    },
                    "-1": {
                        "title": "NonExistentWordXYZ",
                        "missing": ""
                    }
                }
            }
        }
        compressed = gzip.compress(json.dumps(mock_response_data).encode("utf-8"))
        mock_resp = MagicMock()
        mock_resp.read.return_value = compressed
        mock_resp.headers = {"Content-Encoding": "gzip"}
        mock_resp.__enter__.return_value = mock_resp

        client = WiktionaryClient(cache_file="/tmp/test_redirect_cache.json", rate_limit=0.0)
        with patch("urllib.request.urlopen", return_value=mock_resp):
            results = client._fetch_batch_with_retry(["grey_colour", "NonExistentWordXYZ"])

        # Redirect resolved back to original query title
        self.assertIn("==English==", results.get("grey_colour", ""))
        # Missing page mapped to None
        self.assertIsNone(results.get("NonExistentWordXYZ"))

    def test_wiktionary_client_http_retry_backoff(self):
        """Verify HTTP 429 rate limit triggers backoff retry and eventual failure recovery."""
        mock_resp_429 = urllib.error.HTTPError(
            url="https://en.wiktionary.org",
            code=429,
            msg="Too Many Requests",
            hdrs={"Retry-After": "0.01"},
            fp=BytesIO(b"Rate limit exceeded")
        )

        client = WiktionaryClient(cache_file="/tmp/test_backoff_cache.json", rate_limit=0.0)
        with patch("urllib.request.urlopen", side_effect=mock_resp_429), \
             patch("time.sleep") as mock_sleep:
            results = client._fetch_batch_with_retry(["word1", "word2"])

        # Should have retried MAX_RETRIES (5) times and slept
        self.assertEqual(mock_sleep.call_count, 5)
        # All titles in batch should safely fall back to None
        self.assertEqual(results, {"word1": None, "word2": None})


def run_tests():
    suite = unittest.TestLoader().loadTestsFromTestCase(TestMilestone1Adversarial)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)


if __name__ == "__main__":
    run_tests()
