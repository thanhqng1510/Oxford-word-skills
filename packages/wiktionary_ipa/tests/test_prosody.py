"""
Tests for prosody.py in wiktionary_ipa library.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from wiktionary_ipa.prosody import synthesize_compound_ipa


class TestProsody(unittest.TestCase):
    def test_phrasal_verb_stress(self):
        word_map = {"break": "/breɪk/", "out": "/aʊt/"}
        res = synthesize_compound_ipa("break out", word_map)
        self.assertEqual(res, "/ˌbreɪk ˈaʊt/")

    def test_compound_noun_stress(self):
        word_map = {"science": "/ˈsaɪəns/", "fiction": "/ˈfɪkʃən/"}
        res = synthesize_compound_ipa("science fiction", word_map)
        self.assertEqual(res, "/ˈsaɪəns ˌfɪkʃən/")

    def test_weak_forms_handling(self):
        word_map = {"time": "/taɪm/"}
        res = synthesize_compound_ipa("from time to time", word_map, fallback_ipa="/frəm ˌtaɪm tə ˈtaɪm/")
        self.assertEqual(res, "/frəm ˌtaɪm tə ˈtaɪm/")


if __name__ == "__main__":
    unittest.main()
