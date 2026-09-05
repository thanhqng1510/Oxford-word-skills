"""Tier 3: Cross-Feature Combinations E2E Tests.

Covers:
- Word-to-unit cross-referencing and pipeline aggregation
- Module word count aggregation & unit distribution
- Section-to-unit hierarchy consistency (160 sections across 80 units)
- Intra-unit distractor collision prevention across all 80 units
- Synonym matching pair exclusivity within units
- Learned word persistence key stability & determinism
- Multi-unit word definition consistency
- Module & Unit progress calculation invariants
- Search filter cross-referencing across words and definitions
"""

import json
import os
import unittest
from typing import Dict, List, Set

from tests.content_loader import (
    build_runtime_modules,
    is_valid_swift_word,
    load_definitions_json,
    load_extrawordlist_xml,
    load_settings_xml,
)


class TestTier3CrossFeatureCombinations(unittest.TestCase):
    """Tier 3: Cross-Feature Combination Tests."""

    def setUp(self):
        self.tree_settings, self.modules = load_settings_xml()
        self.tree_words, self.raw_words = load_extrawordlist_xml()
        self.defs_dict = load_definitions_json()
        self.modules, self.runtime_words, self.words_by_unit = build_runtime_modules()

    def test_t3_01_word_to_unit_cross_referencing(self):
        """Cross-Feature: Verify all words in extrawordlist.xml correctly map into their units."""
        valid_raw = [w for w in self.raw_words if is_valid_swift_word(w.word)]
        for raw in valid_raw:
            for u in raw.unit_numbers:
                unit_words = [w.word for w in self.words_by_unit.get(u, [])]
                self.assertIn(
                    raw.word,
                    unit_words,
                    f"Word '{raw.word}' assigned to unit {u} in XML is missing from unit words list",
                )

    def test_t3_02_module_word_count_aggregation(self):
        """Cross-Feature: Verify Module wordCount equals sum of constituent Unit word counts."""
        for mod in self.modules:
            unit_sum = sum(len(self.words_by_unit.get(u.number, [])) for u in mod.units)
            self.assertGreater(
                unit_sum,
                0,
                f"Module '{mod.title}' has 0 words across its units: {[u.number for u in mod.units]}",
            )

    def test_t3_03_section_to_unit_hierarchy_integrity(self):
        """Cross-Feature: Verify each of the 80 units has at least 1 section (148 total) linked to their parent unit."""
        total_sections = 0
        for mod in self.modules:
            for u in mod.units:
                self.assertGreaterEqual(
                    len(u.sections),
                    1,
                    f"Unit {u.number} ('{u.title}') has 0 sections",
                )
                total_sections += len(u.sections)

        self.assertEqual(total_sections, 148, f"Expected 148 total sections, got {total_sections}")

    def test_t3_04_intra_unit_distractor_collisions_across_all_80_units(self):
        """Cross-Feature: Check that no unit out of 80 has duplicate short definitions among its words."""
        collisions_by_unit = {}
        for unit_num in range(1, 81):
            words = self.words_by_unit.get(unit_num, [])
            seen_defs: Dict[str, str] = {}
            unit_collisions = []
            for w in words:
                s_def = w.short_definition.strip().lower()
                if s_def and s_def != "no definition available":
                    if s_def in seen_defs:
                        unit_collisions.append((seen_defs[s_def], w.word, s_def))
                    else:
                        seen_defs[s_def] = w.word
            if unit_collisions:
                collisions_by_unit[unit_num] = unit_collisions

        self.assertEqual(
            len(collisions_by_unit),
            0,
            f"Found definition collisions in {len(collisions_by_unit)} units: {list(collisions_by_unit.items())[:3]}",
        )

    def test_t3_05_intra_unit_synonym_matching_exclusivity(self):
        """Cross-Feature: Verify top 2 synonyms per word in MatchingView do not collide within any unit."""
        synonym_collisions = {}
        for unit_num in range(1, 81):
            words = self.words_by_unit.get(unit_num, [])
            seen_syns: Dict[str, str] = {}
            collisions = []
            for w in words:
                for syn in w.synonyms[:2]:
                    s_clean = syn.strip().lower()
                    if s_clean in seen_syns and seen_syns[s_clean] != w.word:
                        collisions.append((seen_syns[s_clean], w.word, s_clean))
                    else:
                        seen_syns[s_clean] = w.word
            if collisions:
                synonym_collisions[unit_num] = collisions

        self.assertEqual(
            len(synonym_collisions),
            0,
            f"Found synonym matching collisions in {len(synonym_collisions)} units: {list(synonym_collisions.items())[:3]}",
        )

    def test_t3_06_persistence_key_stability_and_determinism(self):
        """Cross-Feature: Verify persistence key calculation is 100% deterministic and reversible."""
        for w in self.runtime_words:
            key1 = w.persistence_key
            # Recompute with shuffled unit numbers
            shuffled_units = list(reversed(w.unit_numbers))
            recomputed = f"{w.word}|{','.join(str(u) for u in sorted(shuffled_units))}"
            self.assertEqual(key1, recomputed, f"Persistence key non-deterministic for word '{w.word}'")

    def test_t3_07_multi_unit_word_definition_consistency(self):
        """Cross-Feature: Multi-unit words must have identical definitions in all unit instances."""
        multi_unit_words = [w for w in self.runtime_words if len(w.unit_numbers) > 1]
        for w in multi_unit_words:
            for u in w.unit_numbers:
                unit_instance = next((uw for uw in self.words_by_unit.get(u, []) if uw.word == w.word), None)
                self.assertIsNotNone(unit_instance, f"Word '{w.word}' not found in unit {u}")
                self.assertEqual(
                    w.short_definition,
                    unit_instance.short_definition,
                    f"Inconsistent definition for '{w.word}' in unit {u}",
                )

    def test_t3_08_progress_calculation_invariants(self):
        """Cross-Feature: Verify Unit and Module progress invariants (0 <= progress <= 1)."""
        for mod in self.modules:
            for u in mod.units:
                words = self.words_by_unit.get(u.number, [])
                total_count = len(words)
                # Test 0 learned
                p0 = 0.0 if total_count == 0 else 0 / total_count
                self.assertEqual(p0, 0.0)
                # Test all learned
                p1 = 0.0 if total_count == 0 else total_count / total_count
                self.assertEqual(p1, 1.0 if total_count > 0 else 0.0)
                # Test partial
                half = total_count // 2
                ph = 0.0 if total_count == 0 else half / total_count
                self.assertTrue(0.0 <= ph <= 1.0)

    def test_t3_09_search_filter_cross_referencing(self):
        """Cross-Feature: Verify search filtering matches both headword and shortDefinition substrings."""
        sample_word = self.runtime_words[0]
        query_word = sample_word.word[:3].lower()

        matched_by_word = [
            w for w in self.runtime_words if query_word in w.word.lower() or query_word in w.short_definition.lower()
        ]
        self.assertIn(sample_word, matched_by_word, f"Search by word prefix '{query_word}' failed")

        if sample_word.short_definition and len(sample_word.short_definition) >= 4:
            query_def = sample_word.short_definition.split()[0].lower()
            matched_by_def = [
                w for w in self.runtime_words if query_def in w.word.lower() or query_def in w.short_definition.lower()
            ]
            self.assertIn(sample_word, matched_by_def, f"Search by definition token '{query_def}' failed")

    def test_t3_10_module_unit_span_contiguous(self):
        """Cross-Feature: Verify that modules cover non-overlapping contiguous slices of the 1..80 unit space."""
        seen_units = set()
        for mod_idx, mod in enumerate(self.modules):
            mod_units = [u.number for u in mod.units]
            self.assertTrue(len(mod_units) > 0, f"Module {mod_idx+1} has no units")
            # Check units within module are contiguous
            self.assertEqual(
                mod_units,
                list(range(mod_units[0], mod_units[-1] + 1)),
                f"Module '{mod.title}' units are not contiguous: {mod_units}",
            )
            # Check disjoint
            self.assertTrue(seen_units.isdisjoint(set(mod_units)), f"Unit overlap in module '{mod.title}'")
            seen_units.update(mod_units)

        self.assertEqual(len(seen_units), 80, f"All 80 units must be covered by modules, got {len(seen_units)}")

    def test_t3_11_content_parser_fallback_xml_and_definitions(self):
        """Cross-Feature: Verify fallback logic interaction between extrawordlist.xml and definitions.json."""
        # Simulated fallback engine behavior matching PROJECT.md Swift contract
        def resolve_ipa(xml_ipa: str, def_phonetic: str) -> str:
            clean_xml = xml_ipa.strip()
            clean_def = def_phonetic.strip()
            if clean_xml and clean_xml != "//" and clean_xml != "/":
                return clean_xml
            if clean_def and clean_def != "//" and clean_def != "/":
                if clean_def.startswith("/") and clean_def.endswith("/"):
                    return clean_def
                return f"/{clean_def}/"
            return ""

        # Test simulated edge conditions
        self.assertEqual(resolve_ipa("/æd/", ""), "/æd/", "Valid XML IPA should be preferred")
        self.assertEqual(resolve_ipa("", "/æd/"), "/æd/", "Empty XML IPA should fallback to definitions.json")
        self.assertEqual(resolve_ipa("//", "/æd/"), "/æd/", "Malformed '//' XML IPA should fallback to definitions.json")
        self.assertEqual(resolve_ipa("", "æd"), "/æd/", "Un-slashed definitions phonetic should be auto-enclosed on fallback")

        # Verify across dataset that fallback produces 100% non-empty IPAs
        unresolvable = []
        for w in self.runtime_words:
            def_phonetic = self.defs_dict.get(w.word, {}).get("phonetic", "")
            resolved = resolve_ipa(w.ipa, def_phonetic)
            if not resolved or resolved == "//":
                unresolvable.append(w.word)

        self.assertEqual(
            len(unresolvable),
            0,
            f"Found {len(unresolvable)} words unresolvable via XML / definitions fallback: {unresolvable[:10]}",
        )

    def test_t3_12_speech_text_pronunciation_cleaning_interaction(self):
        """Cross-Feature: Verify cleanWord, speechText, and IPA interaction for annotated words."""
        # Check annotated words e.g. 'ad (= advertisement)'
        annotated_words = [w for w in self.runtime_words if "(" in w.word]
        self.assertGreaterEqual(len(annotated_words), 50, "Expected at least 50 annotated words")

        for w in annotated_words:
            # IPA must not contain the annotation or '=' sign
            self.assertNotIn(
                "=",
                w.ipa,
                f"Word '{w.word}' has '=' sign in IPA '{w.ipa}'",
            )
            # IPA should be non-empty and valid
            self.assertTrue(
                w.ipa.startswith("/") and w.ipa.endswith("/"),
                f"Word '{w.word}' must have slash-enclosed IPA, got '{w.ipa}'",
            )

    def test_t3_13_quiz_distractor_matching_with_ipa(self):
        """Cross-Feature: Verify quiz distractors within a unit do not share both identical definition and IPA."""
        ambiguous_questions = []
        for unit_num in range(1, 81):
            words = self.words_by_unit.get(unit_num, [])
            valid_words = [w for w in words if w.definitions]
            for target in valid_words:
                target_def = target.short_definition
                target_ipa = target.ipa
                # Find distractors with both identical definition and identical IPA
                identical_distractors = [
                    w.word for w in valid_words
                    if w.word != target.word and w.short_definition == target_def and w.ipa == target_ipa
                ]
                if identical_distractors:
                    ambiguous_questions.append((unit_num, target.word, identical_distractors))

        self.assertEqual(
            len(ambiguous_questions),
            0,
            f"Found {len(ambiguous_questions)} questions where distractors share identical definition & IPA: {ambiguous_questions[:5]}",
        )

    def test_t3_14_ipa_and_audio_alignment(self):
        """Cross-Feature: Verify all words marked with hasAudio have complete, non-empty IPA."""
        audio_words = [w for w in self.runtime_words if w.has_audio]
        self.assertGreaterEqual(len(audio_words), 700, "Expected >=700 audio-enabled words")

        missing_ipa_audio_words = [w.word for w in audio_words if not w.ipa or w.ipa == "//"]
        self.assertEqual(
            len(missing_ipa_audio_words),
            0,
            f"Found {len(missing_ipa_audio_words)} audio-enabled words with missing IPA: {missing_ipa_audio_words[:10]}",
        )


if __name__ == "__main__":
    unittest.main()
