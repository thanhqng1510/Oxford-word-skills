"""
Tests for normalizer.py in wiktionary_ipa library.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from wiktionary_ipa.normalizer import (
    is_valid_ipa,
    normalize_ipa,
    phonetically_equivalent,
    simplify_phonetics,
)


class TestNormalizer(unittest.TestCase):
    def test_strip_square_brackets(self):
        self.assertEqual(normalize_ipa("[test]"), "/test/")

    def test_strip_syllable_dots(self):
        self.assertEqual(normalize_ipa("/b.æ.θ/"), "/bæθ/")

    def test_turned_r_mapping(self):
        self.assertEqual(normalize_ipa("/ɹed/"), "/red/")
        self.assertEqual(normalize_ipa("/fɑː(ɹ)/"), "/fɑː(r)/")

    def test_american_tap_mapping(self):
        self.assertEqual(normalize_ipa("[ˈbeɾə]"), "/ˈbetə/")

    def test_rhotic_vowels_mapping(self):
        self.assertEqual(normalize_ipa("/bɝd/"), "/bɜːd/")
        self.assertEqual(normalize_ipa("/əkˈsɛləˌɹeɪtɚ/"), "/əkˈseləˌreɪtə/")

    def test_open_mid_vowel_mapping(self):
        self.assertEqual(normalize_ipa("/bɛd/"), "/bed/")

    def test_script_g_mapping(self):
        self.assertEqual(normalize_ipa("/ɡʊd/"), "/gʊd/")

    def test_ascii_colon_standardization(self):
        self.assertEqual(normalize_ipa("/bi:t/"), "/biːt/")

    def test_valid_ipa_check(self):
        self.assertTrue(is_valid_ipa("/ˈæpəl/"))
        self.assertFalse(is_valid_ipa("apple"))
        self.assertFalse(is_valid_ipa("//"))
        self.assertFalse(is_valid_ipa("/%sampa/"))
        self.assertFalse(is_valid_ipa("/tS/"))

    def test_phonetic_equivalence(self):
        self.assertTrue(phonetically_equivalent("/ˈbækwəd(z)/", "/ˈbækwə(r)d/"))
        self.assertTrue(phonetically_equivalent("/əˈdɪʃn/", "/əˈdɪʃən/"))
        self.assertTrue(phonetically_equivalent("/səkˈsesfl/", "/səkˈsesfəl/"))
        self.assertTrue(phonetically_equivalent("/ˌtiː ˈviː/", "/ˌtiːˈviː/"))
        self.assertFalse(phonetically_equivalent("/kæt/", "/dɒg/"))


if __name__ == "__main__":
    unittest.main()
