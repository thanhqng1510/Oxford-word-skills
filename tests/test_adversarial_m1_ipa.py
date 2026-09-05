#!/usr/bin/env python3
"""
Adversarial Test Harness for British English (Received Pronunciation) IPA Validation
Oxford Word Skills — Phonetic Integrity & Robustness

Empirically probes Resources/definitions.json across baseline invariants,
lexical edge cases, and adversarial phonetic integrity.
"""

import json
import os
import re
import unittest
from typing import Dict, List, Set, Tuple

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DEFINITIONS_PATH = os.path.join(PROJECT_ROOT, "Resources", "definitions.json")
EXTRAWORDLIST_PATH = os.path.join(PROJECT_ROOT, "Resources", "extrawordlist.xml")


class TestAdversarialM1IPAMap(unittest.TestCase):
    """Adversarial challenge test suite for audited IPA mapping."""

    @classmethod
    def setUpClass(cls):
        with open(DEFINITIONS_PATH, "r", encoding="utf-8") as f:
            cls.defs_dict = json.load(f)
        cls.audited_map = {hw: entry.get("phonetic", "") for hw, entry in cls.defs_dict.items()}
        cls.map_exists = True

    def setUp(self):
        self.assertTrue(
            self.map_exists,
            "Required definitions.json or audited IPA map missing",
        )

    # -------------------------------------------------------------------------
    # Tier A: Baseline Invariants (from Milestone 1 Contract & test_t2_13)
    # -------------------------------------------------------------------------

    def test_a01_completeness_and_key_parity(self):
        """Invariant: aud_map contains exactly 2,777 headwords with 100% parity to definitions.json."""
        self.assertEqual(
            len(self.audited_map),
            2777,
            f"Expected exactly 2,777 headwords, found {len(self.audited_map)}",
        )
        missing_keys = set(self.defs_dict.keys()) - set(self.audited_map.keys())
        self.assertEqual(
            len(missing_keys),
            0,
            f"Audited map missing {len(missing_keys)} headwords from definitions.json: {list(missing_keys)[:10]}",
        )
        extra_keys = set(self.audited_map.keys()) - set(self.defs_dict.keys())
        self.assertEqual(
            len(extra_keys),
            0,
            f"Audited map contains {len(extra_keys)} unindexed headwords: {list(extra_keys)[:10]}",
        )

    def test_a02_slash_enclosure_non_emptiness_and_length(self):
        """Invariant: All 2,777 headwords must be enclosed in /.../ and have length > 2."""
        malformed = []
        for hw, ipa in self.audited_map.items():
            if not (ipa.startswith("/") and ipa.endswith("/")):
                malformed.append((hw, ipa, "Missing slash enclosure"))
            elif len(ipa) <= 2:
                malformed.append((hw, ipa, "Empty or length <= 2"))
            elif ipa == "//":
                malformed.append((hw, ipa, "Empty slash pair //"))

        self.assertEqual(
            len(malformed),
            0,
            f"Found {len(malformed)} malformed enclosure/length entries: {malformed[:10]}",
        )

    def test_a03_forbidden_sampa_tokens(self):
        """Invariant: Zero raw legacy SAMPA tokens [%, &, Q, V, ”, Í, Ù, @, 2, 3, \"]."""
        forbidden_regex = re.compile(r'[%&"”QVUITAODSZ23@ÍÙ]')
        sampa_failures = []
        for hw, ipa in self.audited_map.items():
            if forbidden_regex.search(ipa):
                sampa_failures.append((hw, ipa))

        self.assertEqual(
            len(sampa_failures),
            0,
            f"Found {len(sampa_failures)} entries with forbidden SAMPA characters: {sampa_failures[:10]}",
        )

    def test_a04_no_ascii_colons(self):
        """Invariant: ASCII colon ':' is prohibited (must use Unicode length mark 'ː' U+02D0)."""
        colon_failures = [
            (hw, ipa) for hw, ipa in self.audited_map.items() if ":" in ipa
        ]
        self.assertEqual(
            len(colon_failures),
            0,
            f"Found {len(colon_failures)} entries with ASCII colon: {colon_failures[:10]}",
        )

    def test_a05_no_double_or_inner_slashes(self):
        """Invariant: No double slashes '//' or internal stray slashes."""
        slash_failures = []
        for hw, ipa in self.audited_map.items():
            if "//" in ipa:
                slash_failures.append((hw, ipa, "Contains double slash //"))
            elif "/" in ipa[1:-1]:
                slash_failures.append((hw, ipa, "Contains internal slash"))

        self.assertEqual(
            len(slash_failures),
            0,
            f"Found {len(slash_failures)} entries with slash errors: {slash_failures[:10]}",
        )

    def test_a06_no_americanisms(self):
        """Invariant: Zero General American symbols (rhotic schwa 'ɚ', 'ɝ', flap 'ɾ')."""
        american_chars = {"ɚ", "ɝ", "ɾ"}
        american_failures = [
            (hw, ipa)
            for hw, ipa in self.audited_map.items()
            if any(c in american_chars for c in ipa)
        ]
        self.assertEqual(
            len(american_failures),
            0,
            f"Found {len(american_failures)} entries with Americanisms: {american_failures[:10]}",
        )

    def test_a07_no_square_brackets(self):
        """Invariant: Zero narrow phonetic square brackets '[' or ']'."""
        bracket_failures = [
            (hw, ipa)
            for hw, ipa in self.audited_map.items()
            if "[" in ipa or "]" in ipa
        ]
        self.assertEqual(
            len(bracket_failures),
            0,
            f"Found {len(bracket_failures)} entries with square brackets: {bracket_failures[:10]}",
        )

    def test_a08_no_stress_marks_before_ellipsis(self):
        """Invariant: No orphaned primary or secondary stress marks preceding ellipsis (ˈ... or ˌ...)."""
        ellipsis_regex = re.compile(r"[ˈˌ]\s*(\.{3}|…)")
        ellipsis_failures = [
            (hw, ipa)
            for hw, ipa in self.audited_map.items()
            if ellipsis_regex.search(ipa)
        ]
        self.assertEqual(
            len(ellipsis_failures),
            0,
            f"Found {len(ellipsis_failures)} entries with stress before ellipsis: {ellipsis_failures[:10]}",
        )

    def test_a09_character_whitelist_compliance(self):
        """Invariant: Complete compliance with tests/test_tier2_boundary.py:test_t2_13 whitelist."""
        allowed_chars = set(
            " abcdefghijklmnopqrstuvwxyz"
            "æɑɒɔəɛɜɪʊʌ"
            "ðŋʃʒθ"
            "ˈˌː"
            "/().-,'… "
        )
        whitelist_failures = []
        for hw, ipa in self.audited_map.items():
            bad = [c for c in ipa if c.lower() not in allowed_chars]
            if bad:
                whitelist_failures.append((hw, ipa, bad))

        self.assertEqual(
            len(whitelist_failures),
            0,
            f"Found {len(whitelist_failures)} entries violating character whitelist: {whitelist_failures[:10]}",
        )

    # -------------------------------------------------------------------------
    # Tier B: Lexical & Morphological Edge Cases
    # -------------------------------------------------------------------------

    def test_b01_multi_word_phrases_and_idioms(self):
        """Edge Case: Multi-word phrases and idioms must contain prosodic stress and full word transcriptions."""
        phrase_samples = [
            ("Can you make it?", r"/.*meɪk.*ɪt/"),
            ("How do you feel about ...?", r"/.*fiːl.*əˌbaʊt/"),
            ("against the law", r"/.*lɔː/"),
            ("break the law", r"/.*lɔː/"),
            ("obey the law", r"/.*lɔː/"),
            ("cost a fortune", r"/.*fɔːtʃuːn/"),
            ("civil servant", r"/.*sɜːvənt/"),
            ("well known", r"/.*nəʊn/"),
        ]
        failures = []
        for phrase, pattern in phrase_samples:
            ipa = self.audited_map.get(phrase, "")
            if not ipa or not re.search(pattern, ipa):
                failures.append((phrase, ipa, f"Expected match for {pattern}"))

        self.assertEqual(
            len(failures),
            0,
            f"Multi-word phrase phonetic check failed for {len(failures)} entries: {failures}",
        )

    def test_b02_parenthetical_abbreviations_and_glosses(self):
        """Edge Case: Acronyms with expansions in parentheses must transcribe the acronym itself."""
        acronym_samples = [
            ("BBC (British Broadcasting Corporation)", "/ˌbiː ˌbiː ˈsiː/"),
            ("CV (curriculum vitae)", "/ˌsiː ˈviː/"),
            ("EU (European Union)", "/ˌiː ˈjuː/"),
            ("IT (information technology)", "/ˌaɪ ˈtiː/"),
            ("MP (Member of Parliament)", "/ˌem ˈpiː/"),
            ("PIN (personal identification number)", "/pɪn/"),
            ("TV (television)", "/ˌtiː ˈviː/"),
            ("UFO (unidentified flying object)", "/ˌjuː ˌef ˈəʊ/"),
            ("UN (United Nations)", "/ˌjuː ˈen/"),
        ]
        failures = []
        for term, expected in acronym_samples:
            actual = self.audited_map.get(term, "")
            if actual != expected:
                failures.append((term, actual, f"Expected {expected}"))

        self.assertEqual(
            len(failures),
            0,
            f"Parenthetical acronym transcription failed for {len(failures)} entries: {failures}",
        )

    def test_b03_homograph_syntactic_disambiguation(self):
        """Edge Case: Noun vs Verb homographs must have distinct initial vs second-syllable primary stress."""
        homograph_pairs = [
            ("record N", "record (= make a note)"),
            ("contrast N", "contrast V"),
            ("increase N", "increase V"),
            ("produce (goods)", "produce (a film)"),
        ]
        failures = []
        for noun_key, verb_key in homograph_pairs:
            noun_ipa = self.audited_map.get(noun_key, "")
            verb_ipa = self.audited_map.get(verb_key, "")
            # Noun should have initial stress (ˈ near start)
            noun_has_initial = noun_ipa.startswith("/ˈ")
            # Verb should have second-syllable stress (not start with /ˈ)
            verb_has_non_initial = not verb_ipa.startswith("/ˈ") and "ˈ" in verb_ipa

            if not (noun_has_initial and verb_has_non_initial):
                failures.append((noun_key, noun_ipa, verb_key, verb_ipa))

        self.assertEqual(
            len(failures),
            0,
            f"Homograph syntactic disambiguation failed for {len(failures)} pairs: {failures}",
        )

    def test_b04_hyphenated_compounds_and_prefixes(self):
        """Edge Case: Hyphenated words and affixes must not drop component stems."""
        hyphen_samples = [
            ("built-in flash", r"/.*bɪlt.*flæʃ/"),
            ("clean-shaven", r"/.*kliːn.*ʃeɪvn/"),
            ("face-to-face", r"/.*feɪs.*feɪs/"),
            ("hard-working", r"/.*hɑːd.*wɜːkɪŋ/"),
            ("semi-final", r"/.*semi.*faɪnl/"),
        ]
        failures = []
        for hw, pattern in hyphen_samples:
            ipa = self.audited_map.get(hw, "")
            if not ipa or not re.search(pattern, ipa):
                failures.append((hw, ipa, f"Expected match for {pattern}"))

        self.assertEqual(
            len(failures),
            0,
            f"Hyphenated compound checks failed for {len(failures)} entries: {failures}",
        )

    # -------------------------------------------------------------------------
    # Tier C: Adversarial Stress & Extraction Integrity Probes (Defect Hunters)
    # -------------------------------------------------------------------------

    def test_c01_adversarial_reject_fragment_hyphens(self):
        """Adversarial Defect Check: Reject truncated prefix/suffix fragments with leading/trailing hyphens.

        Known worker bug:
        - 'enthusiasm' -> '/en-/' (prefix fragment from Wiktionary '/ɛn-/')
        - 'hyphen' -> '/-fʌn/' (suffix fragment from Wiktionary '/-fʌn/')
        """
        fragment_failures = []
        for hw, ipa in self.audited_map.items():
            inner = ipa[1:-1]
            if inner.startswith("-") and not hw.startswith("-"):
                fragment_failures.append((hw, ipa, "Leading hyphen in non-affix headword"))
            elif inner.endswith("-") and not hw.endswith("-"):
                fragment_failures.append((hw, ipa, "Trailing hyphen in non-affix headword"))

        self.assertEqual(
            len(fragment_failures),
            0,
            f"CRITICAL DEFECT: Found {len(fragment_failures)} truncated fragment entries with dangling hyphens: {fragment_failures}",
        )

    def test_c02_adversarial_reject_broken_template_artifacts(self):
        """Adversarial Defect Check: Reject broken circumfix or template artifacts in single words.

        Known worker bug:
        - 'astonished' -> '/æ- -d/' (parsed from circumfix template '{{IPA|en|/æ- -d/|/əˈstɒn.ɪʃt/}}')
        """
        template_failures = []
        for hw, ipa in self.audited_map.items():
            inner = ipa[1:-1]
            if " " in inner and " " not in hw and "-" not in hw:
                # Allowed initialisms with spaces between letters (ATM, DVD)
                if not (hw.isupper() and len(hw) <= 4):
                    template_failures.append((hw, ipa, "Unexpected whitespace / broken template artifact"))
            if "- -" in inner or " - " in inner:
                template_failures.append((hw, ipa, "Circumfix hyphen artifact"))

        self.assertEqual(
            len(template_failures),
            0,
            f"CRITICAL DEFECT: Found {len(template_failures)} entries with broken template/circumfix artifacts: {template_failures}",
        )

    def test_c03_adversarial_reject_dialectal_monophthongization(self):
        """Adversarial Defect Check: Reject Pittsburgh / non-RP monophthongization (/aː/ for /aʊ/).

        Known worker bug:
        - 'blouse' -> '/ˈblaːz/' (Pittsburgh/ZA dialect picked because standard RP '/ˈblaʊ̯z/' contained U+032F)
        - 'crowd' -> '/ˈkraːd/' (Pittsburgh/ZA dialect)
        - 'found' -> '/ˈfaːnd/' (Pittsburgh/ZA dialect)
        - 'founder' -> '/ˈfaːndə/' (ZA dialect)
        - 'loud' -> '/ˈlaːd/' (Pittsburgh/ZA dialect)
        - 'proud' -> '/ˈpraːd/' (Pittsburgh/ZA dialect)
        """
        pittsburgh_words = ["blouse", "crowd", "found", "founder", "loud", "proud"]
        monophthong_failures = []
        for w in pittsburgh_words:
            ipa = self.audited_map.get(w, "")
            if "aː" in ipa:
                monophthong_failures.append((w, ipa, "Contains Pittsburgh/ZA monophthong /aː/ instead of standard RP /aʊ/"))

        self.assertEqual(
            len(monophthong_failures),
            0,
            f"CRITICAL DEFECT: Found {len(monophthong_failures)} entries with Pittsburgh/ZA monophthongization (/aː/): {monophthong_failures}",
        )

    def test_c04_adversarial_reject_regional_monophthongs_and_northumbrian(self):
        """Adversarial Defect Check: Reject regional monophthongs /eː/ and Northumbrian /aʊæː/.

        Known worker bug:
        - 'over' -> '/ˈaʊæː/' (Northumbrian dialect picked because standard RP '/ˈəʊ̯və/' had U+032F)
        - 'wake' -> '/ˈweːk/' (monophthongization picked because RP '/ˈweɪ̯k/' had U+032F)
        - 'tail' -> '/ˈteːl/' (monophthongization picked because RP '/ˈteɪ̯l/' had U+032F)
        """
        regional_checks = [
            ("over", "/ˈaʊæː/", "Northumbrian dialect"),
            ("wake", "/ˈweːk/", "Monophthongized dialect"),
            ("tail", "/ˈteːl/", "Monophthongized dialect"),
        ]
        failures = []
        for hw, forbidden_ipa, reason in regional_checks:
            actual = self.audited_map.get(hw, "")
            if actual == forbidden_ipa or "eː" in actual or "aʊæː" in actual:
                failures.append((hw, actual, f"{reason} (/eː/ or /aʊæː/)"))

        self.assertEqual(
            len(failures),
            0,
            f"CRITICAL DEFECT: Found {len(failures)} entries with regional monophthongs or Northumbrian forms: {failures}",
        )

    def test_c05_adversarial_reject_unhandled_dialect_abbreviations(self):
        """Adversarial Defect Check: Reject New Zealand English centralization in '-ish'.

        Known worker bug:
        - '-ish' -> '/əʃ/' (picked NZE because 'NZE' was missing from DISQUALIFY_KEYWORDS)
        Standard British English is '/ɪʃ/'.
        """
        ish_ipa = self.audited_map.get("-ish", "")
        self.assertNotEqual(
            ish_ipa,
            "/əʃ/",
            "CRITICAL DEFECT: '-ish' is transcribed as New Zealand English '/əʃ/' instead of British RP '/ɪʃ/'",
        )
        self.assertEqual(
            ish_ipa,
            "/ɪʃ/",
            f"Expected '-ish' to be British RP '/ɪʃ/', got {ish_ipa}",
        )

    def test_c06_adversarial_reject_archaic_and_corrupt_entries(self):
        """Adversarial Defect Check: Reject archaic noun forms and missing consonants.

        Known worker bug:
        - 'accused' -> '/əˈkjuzəd/' (archaic 3-syllable noun variant with non-standard short /u/ instead of '/əˈkjuːzd/')
        - 'obvious' -> '/ˈɒvɪəs/' (fast speech elision dropping /b/ instead of standard '/ˈɒbviəs/')
        """
        failures = []
        accused_ipa = self.audited_map.get("accused", "")
        if accused_ipa == "/əˈkjuzəd/" or accused_ipa.endswith("zəd/"):
            failures.append(("accused", accused_ipa, "Archaic 3-syllable variant with non-standard short /u/"))

        obvious_ipa = self.audited_map.get("obvious", "")
        if obvious_ipa == "/ˈɒvɪəs/" or "b" not in obvious_ipa:
            failures.append(("obvious", obvious_ipa, "Elided fast-speech form missing /b/"))

        self.assertEqual(
            len(failures),
            0,
            f"CRITICAL DEFECT: Found {len(failures)} archaic or consonant-elided entries: {failures}",
        )


if __name__ == "__main__":
    unittest.main()
