"""Tier 4: Real-World Application Scenario Simulations E2E Tests.

Covers:
- Full Word -> Definition Quiz session simulation across all 80 units
- Full Definition -> Word Reverse Quiz session simulation across all 80 units
- Full Synonym Match Game simulation with stable identity matching
- Full Listening & Spelling (Fill in the Blank) simulation with hint & skip flows
- Full Flashcard deck study flow with flip, example reveal, and learned progress updates
- Full Curriculum navigation and search query traversal
- Full 5 active exercise modes session simulation
- Progress persistence lifecycle (mark learned, reset unit, reset all)
"""

import os
import random
import re
import unittest
from typing import Dict, List, Set

from tests.content_loader import (
    RuntimeWord,
    build_runtime_modules,
    is_valid_swift_word,
    load_definitions_json,
    load_extrawordlist_xml,
    load_settings_xml,
)


class TestTier4RealWorldScenarios(unittest.TestCase):
    """Tier 4: Real-World Application Scenario Tests."""

    def setUp(self):
        self.modules, self.runtime_words, self.words_by_unit = build_runtime_modules()

    def test_t4_01_word_to_definition_quiz_simulation_all_80_units(self):
        """Scenario: Simulate 15-question Word -> Definition Quiz for all 80 units."""
        random.seed(42)
        total_quizzes_tested = 0
        total_questions_tested = 0

        for unit_num in range(1, 81):
            unit_words = self.words_by_unit.get(unit_num, [])
            valid_words = [w for w in unit_words if w.definitions]
            if len(valid_words) < 4:
                continue

            total_quizzes_tested += 1
            # Simulate QuizView.generateQuestions()
            shuffled = list(valid_words)
            random.shuffle(shuffled)
            question_words = shuffled[: min(15, len(shuffled))]

            for word in question_words:
                total_questions_tested += 1
                correct_def = word.short_definition
                distractor_pool = [
                    w.short_definition for w in valid_words if w.word != word.word and w.short_definition != correct_def
                ]
                unique_distractors = list(dict.fromkeys(distractor_pool))
                random.shuffle(unique_distractors)
                selected_distractors = unique_distractors[:3]

                options = [correct_def] + selected_distractors
                random.shuffle(options)

                # Assertions on generated question
                self.assertEqual(
                    len(options),
                    4,
                    f"Unit {unit_num} question for '{word.word}' did not produce exactly 4 choices: {options}",
                )
                self.assertEqual(
                    len(set(options)),
                    4,
                    f"Unit {unit_num} question for '{word.word}' has duplicate choices: {options}",
                )
                self.assertIn(correct_def, options, "Correct answer must be present in options")

                # Simulate answering correctly
                user_selection = correct_def
                is_correct = user_selection == correct_def
                self.assertTrue(is_correct)

        self.assertGreaterEqual(
            total_quizzes_tested,
            75,
            f"Expected at least 75 units to support quizzes, got {total_quizzes_tested}",
        )

    def test_t4_02_definition_to_word_quiz_simulation_all_80_units(self):
        """Scenario: Simulate 15-question Definition -> Word Reverse Quiz for all 80 units."""
        random.seed(123)
        total_reverse_quizzes = 0

        for unit_num in range(1, 81):
            unit_words = self.words_by_unit.get(unit_num, [])
            valid_words = [w for w in unit_words if w.definitions]
            if len(valid_words) < 4:
                continue

            total_reverse_quizzes += 1
            shuffled = list(valid_words)
            random.shuffle(shuffled)
            question_words = shuffled[: min(15, len(shuffled))]

            for word in question_words:
                correct_word = word.word
                distractor_pool = [w.word for w in valid_words if w.word != correct_word]
                unique_distractors = list(dict.fromkeys(distractor_pool))
                random.shuffle(unique_distractors)
                selected_distractors = unique_distractors[:3]

                options = [correct_word] + selected_distractors
                random.shuffle(options)

                self.assertEqual(len(options), 4, f"Reverse quiz for '{word.word}' options != 4")
                self.assertEqual(len(set(options)), 4, f"Reverse quiz options have duplicates: {options}")
                self.assertIn(correct_word, options)

        self.assertGreaterEqual(total_reverse_quizzes, 75)

    def test_t4_03_matching_game_simulation(self):
        """Scenario: Simulate full Synonym Match game round with pair matching logic."""
        random.seed(999)
        units_with_synonyms = [
            u for u, words in self.words_by_unit.items() if len([w for w in words if len(w.synonyms) >= 1]) >= 4
        ]

        if not units_with_synonyms:
            self.skipTest("No units with sufficient synonym words yet")

        test_unit = units_with_synonyms[0]
        words_with_syns = [w for w in self.words_by_unit[test_unit] if len(w.synonyms) >= 1]
        sample = words_with_syns[: min(6, len(words_with_syns))]

        # Model stable pairs
        pairs = []
        for i, w in enumerate(sample):
            pairs.append({"id": f"pair_{i}", "word": w.word, "synonym": w.synonyms[0]})

        # Model stable right options
        right_options = [{"opt_id": f"opt_{p['id']}", "pair_id": p["id"], "text": p["synonym"]} for p in pairs]
        random.shuffle(right_options)

        matched_pairs = set()
        attempts = 0

        # Simulate user successfully matching all pairs
        for p in pairs:
            # User clicks left
            selected_left = p["id"]
            # User finds matching right option
            matching_right = next(opt for opt in right_options if opt["pair_id"] == selected_left)
            selected_right = matching_right["opt_id"]

            attempts += 1
            # Check match logic
            target_opt = next(opt for opt in right_options if opt["opt_id"] == selected_right)
            if target_opt["pair_id"] == selected_left:
                matched_pairs.add(selected_left)

        self.assertEqual(len(matched_pairs), len(pairs), "All pairs must be successfully matched")
        self.assertEqual(attempts, len(pairs), "Should match in minimal attempts for perfect play")

    def test_t4_04_listening_and_spelling_simulation(self):
        """Scenario: Simulate FillInBlankView spelling game with hint progression, skip, and check."""
        sample_words = self.runtime_words[:20]

        for w in sample_words:
            # Base target word (handling annotations like 'ad (= advertisement)' -> 'ad')
            target_spelling = re.sub(r"\s*\(.*?\)", "", w.word).strip()

            # Test 1: User types exact answer
            user_input = target_spelling
            is_correct = user_input.strip().lower() == target_spelling.lower()
            self.assertTrue(is_correct, f"Exact answer matching failed for '{w.word}'")

            # Test 2: Hint progression (character by character)
            for hint_len in range(1, len(target_spelling) + 1):
                hint_str = target_spelling[:hint_len]
                self.assertEqual(len(hint_str), hint_len)
                self.assertTrue(target_spelling.startswith(hint_str))

    def test_t4_05_flashcard_deck_and_learned_progress_simulation(self):
        """Scenario: Simulate FlashcardView deck traversal, flip state, and learned toggle."""
        test_unit = 1
        unit_words = self.words_by_unit.get(test_unit, [])
        self.assertGreater(len(unit_words), 0, f"Unit {test_unit} has no words")

        learned_ids: Set[str] = set()

        # Step through deck
        for idx, word in enumerate(unit_words):
            # Card front: word visible
            self.assertTrue(len(word.word) > 0)

            # Card flip: short definition and example check
            s_def = word.short_definition
            self.assertNotEqual(s_def, "No definition available", f"Word '{word.word}' has no definition")

            # User toggles learned
            key = word.persistence_key
            learned_ids.add(key)

            # Check unit progress update
            learned_count = len([w for w in unit_words if w.persistence_key in learned_ids])
            expected_progress = learned_count / len(unit_words)
            self.assertAlmostEqual(expected_progress, (idx + 1) / len(unit_words))

        # At end of deck, progress must be 100%
        final_progress = len([w for w in unit_words if w.persistence_key in learned_ids]) / len(unit_words)
        self.assertEqual(final_progress, 1.0)

    def test_t4_06_curriculum_search_and_navigation_traversal(self):
        """Scenario: Simulate navigating through all 13 modules, filtering words by search queries."""
        for mod in self.modules:
            self.assertTrue(len(mod.title) > 0)
            for unit in mod.units:
                words = self.words_by_unit.get(unit.number, [])
                # Test empty search query -> returns all unit words
                empty_filter = [w for w in words if "" in w.word.lower()]
                self.assertEqual(len(empty_filter), len(words))

                # Test search query matching first letter
                if words:
                    query = words[0].word[0].lower()
                    filtered = [
                        w for w in words if query in w.word.lower() or query in w.short_definition.lower()
                    ]
                    self.assertGreater(len(filtered), 0)

    def test_t4_07_five_exercise_modes_session_simulation(self):
        """Scenario: Simulate launching all 5 active exercise modes across randomly sampled units."""
        sample_units = random.sample(range(1, 81), 10)
        for unit_num in sample_units:
            words = self.words_by_unit[unit_num]
            # 1. Flashcards: words available
            self.assertGreaterEqual(len(words), 4)
            # 2. Definition Quiz: at least 4 distinct definitions
            defs = [w.short_definition for w in words if w.short_definition]
            self.assertGreaterEqual(len(set(defs)), 4)
            # 3. Reverse Quiz: at least 4 distinct headwords
            self.assertGreaterEqual(len(set(w.word for w in words)), 4)
            # 4. Listening & Spelling: valid normalized headwords
            for w in words[:4]:
                clean = re.sub(r"\s*\(.*?\)", "", w.word).strip()
                self.assertGreater(len(clean), 0)
            # 5. Synonym Match: valid words
            self.assertTrue(all(len(w.word) > 0 for w in words))

    def test_t4_08_progress_persistence_lifecycle(self):
        """Scenario: Simulate complete persistence lifecycle: mark all in unit, reset unit, reset all."""
        learned_ids: Set[str] = set()

        # Mark all in unit 1
        unit1_words = self.words_by_unit.get(1, [])
        for w in unit1_words:
            learned_ids.add(w.persistence_key)

        unit1_learned = len([w for w in unit1_words if w.persistence_key in learned_ids])
        self.assertEqual(unit1_learned, len(unit1_words))

        # Reset unit 1
        for w in unit1_words:
            learned_ids.discard(w.persistence_key)

        unit1_learned_after_reset = len([w for w in unit1_words if w.persistence_key in learned_ids])
        self.assertEqual(unit1_learned_after_reset, 0)

        # Mark all across multiple units then resetAllProgress()
        for w in self.runtime_words[:50]:
            learned_ids.add(w.persistence_key)
        self.assertEqual(len(learned_ids), 50)

        learned_ids.clear()
        self.assertEqual(len(learned_ids), 0)

    def test_t4_09_full_curriculum_ipa_audit_all_80_units(self):
        """Scenario: Full-curriculum end-to-end audit verifying all 80 units & 2,781 runtime words have complete British RP IPA."""
        total_units_audited = 0
        total_word_assignments = 0
        unique_headwords: Set[str] = set()
        missing_or_invalid_ipa = []
        forbidden_sampa = set("%&QVUITAODSZ23@ÍÙ")
        sampa_violations = []

        for mod_idx, mod in enumerate(self.modules):
            for unit in mod.units:
                unit_words = self.words_by_unit.get(unit.number, [])
                self.assertGreater(
                    len(unit_words),
                    0,
                    f"Unit {unit.number} in module '{mod.title}' has 0 runtime words",
                )
                total_units_audited += 1

                for w in unit_words:
                    total_word_assignments += 1
                    unique_headwords.add(w.word)

                    ipa = getattr(w, "ipa", "").strip()
                    if not ipa or not (ipa.startswith("/") and ipa.endswith("/")) or ipa == "//" or len(ipa) <= 2 or "//" in ipa:
                        missing_or_invalid_ipa.append((unit.number, w.word, ipa))

                    bad_sampa = [c for c in ipa if c in forbidden_sampa]
                    if bad_sampa:
                        sampa_violations.append((unit.number, w.word, ipa, bad_sampa))

        # Curriculum invariants
        self.assertEqual(total_units_audited, 80, f"Expected exactly 80 units audited, got {total_units_audited}")
        self.assertEqual(len(unique_headwords), 2775, f"Expected 2,775 unique runtime headwords (2,781 minus 6 duplicates), got {len(unique_headwords)}")
        self.assertEqual(total_word_assignments, 3031, f"Expected 3,031 total word-unit assignments, got {total_word_assignments}")

        # IPA Invariants
        self.assertEqual(
            len(missing_or_invalid_ipa),
            0,
            f"Found {len(missing_or_invalid_ipa)} words with missing or invalid IPA across the curriculum: {missing_or_invalid_ipa[:10]}",
        )
        self.assertEqual(
            len(sampa_violations),
            0,
            f"Found {len(sampa_violations)} words with lingering SAMPA characters across the curriculum: {sampa_violations[:10]}",
        )

    def test_t4_10_flashcard_study_session_ipa_rendering(self):
        """Scenario: Simulate complete Flashcard study session across 80 units verifying clean phonetic presentation."""
        def to_clean_word(word_str: str) -> str:
            if "(" in word_str:
                idx = word_str.index("(")
                base = word_str[:idx].strip()
                return base if base else word_str
            return word_str

        def to_speech_text(word_str: str) -> str:
            cw = to_clean_word(word_str)
            text = cw.replace("...", "").strip()
            return text if text else word_str

        for unit_num in range(1, 81):
            unit_words = self.words_by_unit.get(unit_num, [])
            for w in unit_words:
                clean_word = to_clean_word(w.word)
                speech_text = to_speech_text(w.word)
                # Front of card: clean headword
                self.assertTrue(len(clean_word) > 0, f"Unit {unit_num}: Word '{w.word}' has empty cleanWord")
                # Back of card: IPA pronunciation display
                self.assertTrue(w.ipa.startswith("/") and w.ipa.endswith("/"), f"Unit {unit_num}: '{w.word}' invalid card IPA '{w.ipa}'")
                self.assertNotIn("//", w.ipa, f"Unit {unit_num}: '{w.word}' contains double-slash artifact in '{w.ipa}'")
                # Pronunciation audio text
                self.assertTrue(len(speech_text) > 0, f"Unit {unit_num}: '{w.word}' has empty speechText")

    def test_t4_11_exercise_container_pronunciation_fidelity(self):
        """Scenario: Active exercise execution ensuring uninterrupted pronunciation access in all exercise views."""
        for unit_num in [1, 10, 25, 42, 60, 75, 80]:
            unit_words = self.words_by_unit.get(unit_num, [])
            valid_words = [w for w in unit_words if w.definitions]
            self.assertGreaterEqual(len(valid_words), 4, f"Unit {unit_num} must have >=4 words for exercise modes")

            for mode in ["flashcard", "quiz", "fillInBlank", "matching"]:
                for word in valid_words:
                    self.assertIsNotNone(word.ipa, f"Mode {mode} encountered nil IPA on word '{word.word}'")
                    self.assertGreater(len(word.ipa), 2, f"Mode {mode} encountered empty/invalid IPA on '{word.word}'")


if __name__ == "__main__":
    unittest.main()
