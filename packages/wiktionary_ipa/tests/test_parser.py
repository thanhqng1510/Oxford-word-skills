"""
Tests for parser.py in wiktionary_ipa library.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from wiktionary_ipa.parser import (
    clean_lookup_title,
    extract_english_section,
    parse_wiktionary_rp_candidates,
)


class TestParser(unittest.TestCase):
    def test_clean_lookup_title_abbreviations(self):
        self.assertEqual(clean_lookup_title("BBC (British Broadcasting Corporation)"), "BBC")
        self.assertEqual(clean_lookup_title("CV (curriculum vitae)"), "CV")

    def test_clean_lookup_title_units(self):
        self.assertEqual(clean_lookup_title("l (litre)"), "litre")
        self.assertEqual(clean_lookup_title("cm (centimetre(s))"), "centimetre")
        self.assertEqual(clean_lookup_title("kg (kilo(s)/kilogram(s))"), "kilogram")

    def test_clean_lookup_title_pos_tags(self):
        self.assertEqual(clean_lookup_title("record N"), "record")
        self.assertEqual(clean_lookup_title("contrast V"), "contrast")

    def test_clean_lookup_title_ellipses(self):
        self.assertEqual(clean_lookup_title("how about ...?"), "how about ?")

    def test_extract_english_section(self):
        wikitext = "==French==\n...fr...\n==English==\n===Pronunciation===\n* {{IPA|en|/test/|a=RP}}\n==German==\n...de..."
        eng = extract_english_section(wikitext)
        self.assertIn("===Pronunciation===", eng)
        self.assertNotIn("French", eng)
        self.assertNotIn("German", eng)

    def test_dialect_scoring_rp_over_ga(self):
        wikitext = """
==English==
===Pronunciation===
* {{a|UK}} {{IPA|en|/ˈkɑː/}}
* {{a|US}} {{IPA|en|/ˈkɑɹ/}}
"""
        cands = parse_wiktionary_rp_candidates(wikitext, "car")
        self.assertGreater(len(cands), 0)
        cands.sort(key=lambda x: x[1], reverse=True)
        self.assertEqual(cands[0][0], "/ˈkɑː/")
        self.assertGreater(cands[0][1], 0)


if __name__ == "__main__":
    unittest.main()
