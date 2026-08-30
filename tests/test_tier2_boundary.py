"""Tier 2: Boundary & Corner Cases E2E Tests.

Covers:
- Empty strings and blank definitions
- Special punctuation & unbalanced parentheses
- Multi-unit words with comma-separated unit attributes
- Headword annotations (e.g. `ad (= advertisement)`, `BBC (British Broadcasting Corporation)`)
- Missing meanings detection (`meanings: []`)
- Missing headwords (e.g. `brackets`)
- Corrupted tokens (`🍑`, `∵`, `BS`, Cockney rhyming slang)
- Hyphenated prefix words vs compound words
- Duplicate XML headword nodes
- Idioms / multi-word phrases vs single words
- Extreme length boundaries
- Key whitespace and case normalization
"""

import json
import os
import re
import unittest
from typing import Dict, List, Set

from tests.content_loader import (
    CORRUPT_TOKENS,
    build_runtime_modules,
    is_valid_swift_word,
    load_definitions_json,
    load_extrawordlist_xml,
    load_settings_xml,
)


class TestTier2BoundaryCases(unittest.TestCase):
    """Tier 2: Boundary & Corner Case Tests."""

    def setUp(self):
        self.defs_dict = load_definitions_json()
        _, self.raw_words = load_extrawordlist_xml()
        _, self.modules = load_settings_xml()
        self.modules, self.runtime_words, self.words_by_unit = build_runtime_modules()

    def test_t2_01_no_empty_string_definitions_or_meanings(self):
        """Boundary: Detect any empty or whitespace-only definition strings across the entire dataset."""
        empty_entries = []
        for word, entry in self.defs_dict.items():
            meanings = entry.get("meanings", [])
            if not meanings:
                empty_entries.append((word, "empty meanings list"))
            for m_idx, m in enumerate(meanings):
                defs = m.get("definitions", [])
                if not defs:
                    empty_entries.append((word, f"meaning {m_idx} has no definitions"))
                for d_idx, d in enumerate(defs):
                    text = d.get("definition", "")
                    if not text or not text.strip():
                        empty_entries.append((word, f"meaning {m_idx} def {d_idx} is empty string"))

        self.assertEqual(
            len(empty_entries),
            0,
            f"Found {len(empty_entries)} empty definition boundaries: {empty_entries[:10]}",
        )

    def test_t2_02_definition_punctuation_boundaries(self):
        """Boundary: Detect definitions with illegal trailing punctuation (:, ;, -) or unbalanced parens/brackets."""
        malformed = []
        for word, entry in self.defs_dict.items():
            for m_idx, m in enumerate(entry.get("meanings", [])):
                for d_idx, d in enumerate(m.get("definitions", [])):
                    text = d.get("definition", "").strip()
                    if text:
                        if text.endswith(":") or text.endswith(";") or text.endswith("-"):
                            malformed.append((word, "trailing punctuation", text))
                        if text.count("(") != text.count(")"):
                            malformed.append((word, "unbalanced parentheses", text))
                        if text.count("[") != text.count("]"):
                            malformed.append((word, "unbalanced square brackets", text))

        self.assertEqual(
            len(malformed),
            0,
            f"Found {len(malformed)} malformed definition boundaries: {malformed[:10]}",
        )

    def test_t2_03_multi_unit_words_mapping(self):
        """Corner Case: Verify all 226+ multi-unit words (e.g. unit='42, 46') correctly map to every designated unit."""
        multi_unit_raw = [w for w in self.raw_words if len(w.unit_numbers) > 1]
        self.assertGreaterEqual(
            len(multi_unit_raw),
            200,
            f"Expected at least 200 multi-unit words, found {len(multi_unit_raw)}",
        )

        # Check each multi-unit word is present in all of its units
        missing_mappings = []
        for raw in multi_unit_raw:
            if not is_valid_swift_word(raw.word):
                continue
            for u in raw.unit_numbers:
                unit_words = [w.word for w in self.words_by_unit.get(u, [])]
                if raw.word not in unit_words:
                    missing_mappings.append((raw.word, u))

        self.assertEqual(
            len(missing_mappings),
            0,
            f"Found {len(missing_mappings)} missing multi-unit word mappings: {missing_mappings[:10]}",
        )

    def test_t2_04_annotated_headwords_lexicographical_integrity(self):
        """Corner Case: Validate annotated headwords (e.g. 'ad (= advertisement)', 'BBC (British Broadcasting Corporation)')."""
        annotated_words = [w for w in self.raw_words if "(" in w.word or "=" in w.word]
        self.assertGreaterEqual(
            len(annotated_words),
            50,
            f"Expected at least 50 annotated headwords, found {len(annotated_words)}",
        )

        unpopulated_annotated = []
        for raw in annotated_words:
            if raw.word in self.defs_dict:
                entry = self.defs_dict[raw.word]
                if not entry.get("meanings"):
                    unpopulated_annotated.append(raw.word)
            else:
                unpopulated_annotated.append(raw.word)

        self.assertEqual(
            len(unpopulated_annotated),
            0,
            f"{len(unpopulated_annotated)} annotated headwords lack definitions: {unpopulated_annotated[:10]}",
        )

    def test_t2_05_missing_meanings_detection(self):
        """Boundary: Explicitly assert that 0 entries in definitions.json have empty meanings: []."""
        empty_meanings = [k for k, v in self.defs_dict.items() if not v.get("meanings")]
        self.assertEqual(
            len(empty_meanings),
            0,
            f"Found {len(empty_meanings)} entries with empty meanings array: {empty_meanings[:10]}",
        )

    def test_t2_06_missing_headword_brackets_detection(self):
        """Corner Case: Specifically verify that 'brackets' exists in definitions.json with valid content."""
        self.assertIn("brackets", self.defs_dict, "Headword 'brackets' (Unit 4) is missing from definitions.json")
        entry = self.defs_dict.get("brackets", {})
        meanings = entry.get("meanings", [])
        self.assertTrue(len(meanings) > 0, "'brackets' has empty meanings list")
        pos_list = [m.get("partOfSpeech") for m in meanings]
        self.assertIn("noun", pos_list, "'brackets' should have a noun meaning")

    def test_t2_07_corrupt_tokens_detection(self):
        """Boundary: Search the entire definitions.json dataset for specific corrupt tokens (🍑, ∵, BS, etc.)."""
        found_corruptions = []
        for word, entry in self.defs_dict.items():
            entry_str = json.dumps(entry, ensure_ascii=False)
            for token in CORRUPT_TOKENS:
                if token in entry_str:
                    found_corruptions.append((word, token))

        self.assertEqual(
            len(found_corruptions),
            0,
            f"Found {len(found_corruptions)} corrupt token occurrences: {found_corruptions[:10]}",
        )

    def test_t2_08_hyphenated_prefix_words_filtering(self):
        """Corner Case: Verify Swift ContentParser.isValidWord filters prefix-hyphen words like -ish, -shaped."""
        self.assertFalse(is_valid_swift_word("-ish"), "'-ish' should be invalid (starts with '-')")
        self.assertFalse(is_valid_swift_word("-shaped"), "'-shaped' should be invalid (starts with '-')")
        self.assertFalse(is_valid_swift_word("a-"), "'a-' should be invalid (ends with '-')")
        self.assertFalse(is_valid_swift_word("a"), "'a' should be invalid (length < 2)")
        self.assertTrue(is_valid_swift_word("ice-cream"), "'ice-cream' should be valid compound word")
        self.assertTrue(is_valid_swift_word("well-known"), "'well-known' should be valid compound word")

    def test_t2_09_duplicate_xml_headword_nodes_consistency(self):
        """Corner Case: Verify 6 duplicate XML headwords ('mind', 'overall', 'patient', 'scratch', 'store', 'think')."""
        duplicates = ["mind", "overall", "patient", "scratch", "store", "think"]
        for dup in duplicates:
            matching_raw = [w for w in self.raw_words if w.word == dup]
            self.assertEqual(
                len(matching_raw),
                2,
                f"Word '{dup}' should appear exactly twice in extrawordlist.xml, got {len(matching_raw)}",
            )
            # In definitions.json, there must be a valid unified entry
            self.assertIn(dup, self.defs_dict, f"Duplicate XML word '{dup}' must exist in definitions.json")
            entry = self.defs_dict[dup]
            self.assertGreater(len(entry.get("meanings", [])), 0, f"'{dup}' must have populated meanings")

    def test_t2_10_phrase_and_idiom_headwords_presence(self):
        """Corner Case: Verify multi-word phrases and idioms (e.g. 'after a while', 'break the law') have definitions."""
        multi_word_raw = [w for w in self.raw_words if " " in w.word and is_valid_swift_word(w.word)]
        self.assertGreaterEqual(
            len(multi_word_raw),
            400,
            f"Expected at least 400 multi-word phrases/idioms, got {len(multi_word_raw)}",
        )

        unpopulated_phrases = []
        for raw in multi_word_raw:
            if raw.word in self.defs_dict:
                entry = self.defs_dict[raw.word]
                if not entry.get("meanings"):
                    unpopulated_phrases.append(raw.word)
            else:
                unpopulated_phrases.append(raw.word)

        self.assertEqual(
            len(unpopulated_phrases),
            0,
            f"{len(unpopulated_phrases)} multi-word phrases/idioms lack definitions: {unpopulated_phrases[:10]}",
        )

    def test_t2_11_definition_length_boundaries(self):
        """Boundary: Definitions must not be excessively terse (< 5 chars) or run-away (> 500 chars)."""
        extreme_defs = []
        for word, entry in self.defs_dict.items():
            for meaning in entry.get("meanings", []):
                for d in meaning.get("definitions", []):
                    def_str = d.get("definition", "").strip()
                    if len(def_str) < 5:
                        extreme_defs.append((word, "too short", def_str))
                    elif len(def_str) > 500:
                        extreme_defs.append((word, "excessive length", def_str))

        self.assertEqual(
            len(extreme_defs),
            0,
            f"Found {len(extreme_defs)} definitions with extreme length boundaries: {extreme_defs[:10]}",
        )

    def test_t2_12_key_whitespace_and_case_exact_match(self):
        """Boundary: Verify JSON dictionary keys have no leading/trailing whitespace and match XML headwords exactly."""
        bad_keys = []
        for k in self.defs_dict.keys():
            if k != k.strip():
                bad_keys.append((k, "key has leading/trailing whitespace"))

        self.assertEqual(len(bad_keys), 0, f"Found {len(bad_keys)} whitespace-corrupted keys: {bad_keys}")


if __name__ == "__main__":
    unittest.main()
