#!/usr/bin/env python3
"""Adversarial Stress Test Suite for QuizView and MatchingView.

Executes 10,000 question generations in QuizView and extensive MatchingView simulations:
1. Strictly 4 unique choices per question (0 duplicates) across all 80 units and global mode.
2. Crash resilience on units with < 4 words (0, 1, 2, 3 words) and identical definition collisions.
3. Multi-round MatchingView game simulations (perfect play, random play, adversarial worst-case).
4. Edge-case word lists (0 synonyms, 1 synonym, duplicate synonyms, self-referential synonyms).
"""

import json
import os
import random
import re
import sys
import unittest
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

# Ensure project root is on sys.path
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from tests.content_loader import (
    RuntimeWord,
    WordDefinitionData,
    build_runtime_modules,
    is_valid_swift_word,
    load_definitions_json,
    load_extrawordlist_xml,
    load_settings_xml,
)


@dataclass
class QuizQuestionSim:
    word: RuntimeWord
    options: List[str]
    correct_answer: str
    correct_definition: str


class QuizViewSimulator:
    """Accurately mirrors Swift QuizView.generateQuestions() two-pass distractor algorithm."""

    def __init__(self, all_words: List[RuntimeWord], words_by_unit: Dict[int, List[RuntimeWord]]):
        self.all_words = all_words
        self.words_by_unit = words_by_unit

    def generate_questions(
        self, unit_number: Optional[int], quiz_mode: str, custom_source: Optional[List[RuntimeWord]] = None
    ) -> List[QuizQuestionSim]:
        if custom_source is not None:
            source_words = custom_source
        elif unit_number is not None:
            source_words = self.words_by_unit.get(unit_number, [])
        else:
            source_words = self.all_words

        valid_source_words = [
            w
            for w in source_words
            if w.definitions
            and w.short_definition != "No definition available"
            and w.short_definition.strip()
        ]

        if not valid_source_words:
            return []

        fallback_words = [
            w
            for w in self.all_words
            if w.definitions
            and w.short_definition != "No definition available"
            and w.short_definition.strip()
        ]

        shuffled = list(valid_source_words)
        random.shuffle(shuffled)
        question_words = shuffled[: min(15, len(shuffled))]

        questions = []
        for word in question_words:
            if quiz_mode == "wordToDefinition":
                correct_def = word.short_definition.strip()
                chosen_defs: List[str] = []
                seen_defs: Set[str] = {correct_def.lower()}

                # Pass 1: sample from current unit
                unit_candidates = [w for w in valid_source_words if w.word != word.word]
                random.shuffle(unit_candidates)
                for cand in unit_candidates:
                    d = cand.short_definition.strip()
                    d_key = d.lower()
                    if d and d_key not in seen_defs:
                        seen_defs.add(d_key)
                        chosen_defs.append(d)
                        if len(chosen_defs) == 3:
                            break

                # Pass 2: sample from global pool if unit has < 3 distinct distractors
                if len(chosen_defs) < 3:
                    global_candidates = [w for w in fallback_words if w.word != word.word]
                    random.shuffle(global_candidates)
                    for cand in global_candidates:
                        d = cand.short_definition.strip()
                        d_key = d.lower()
                        if d and d_key not in seen_defs:
                            seen_defs.add(d_key)
                            chosen_defs.append(d)
                            if len(chosen_defs) == 3:
                                break

                options = [correct_def] + chosen_defs
                random.shuffle(options)
                questions.append(
                    QuizQuestionSim(
                        word=word,
                        options=options,
                        correct_answer=correct_def,
                        correct_definition=correct_def,
                    )
                )

            elif quiz_mode == "definitionToWord":
                correct_word = word.word.strip()
                correct_def = word.short_definition.strip()
                chosen_words: List[str] = []
                seen_words: Set[str] = {correct_word.lower()}

                # Pass 1: sample from current unit
                unit_candidates = [w for w in valid_source_words if w.word != word.word]
                random.shuffle(unit_candidates)
                for cand in unit_candidates:
                    c_word = cand.word.strip()
                    w_key = c_word.lower()
                    if c_word and w_key not in seen_words:
                        seen_words.add(w_key)
                        chosen_words.append(c_word)
                        if len(chosen_words) == 3:
                            break

                # Pass 2: sample from global pool if unit has < 3 distinct distractors
                if len(chosen_words) < 3:
                    global_candidates = [w for w in fallback_words if w.word != word.word]
                    random.shuffle(global_candidates)
                    for cand in global_candidates:
                        c_word = cand.word.strip()
                        w_key = c_word.lower()
                        if c_word and w_key not in seen_words:
                            seen_words.add(w_key)
                            chosen_words.append(c_word)
                            if len(chosen_words) == 3:
                                break

                options = [correct_word] + chosen_words
                random.shuffle(options)
                questions.append(
                    QuizQuestionSim(
                        word=word,
                        options=options,
                        correct_answer=correct_word,
                        correct_definition=correct_def,
                    )
                )

        return questions


@dataclass
class MatchPairSim:
    id: str
    word: RuntimeWord
    synonym: str


@dataclass
class RightOptionSim:
    id: str
    pair_id: str
    synonym: str


class MatchingViewSimulator:
    """Accurately mirrors Swift MatchingView pair generation & match resolution state machine."""

    def __init__(self, all_words: List[RuntimeWord], words_by_unit: Dict[int, List[RuntimeWord]]):
        self.all_words = all_words
        self.words_by_unit = words_by_unit
        self.pairs: List[MatchPairSim] = []
        self.right_options: List[RightOptionSim] = []
        self.selected_left: Optional[str] = None
        self.selected_right: Optional[str] = None
        self.matched_pairs: Set[str] = set()
        self.attempts: int = 0
        self.is_finished: bool = False
        self.wrong_right_ids: Set[str] = set()
        self.wrong_left_ids: Set[str] = set()

    def generate_pairs(self, unit_number: Optional[int], custom_source: Optional[List[RuntimeWord]] = None):
        if custom_source is not None:
            source_words = custom_source
        elif unit_number is not None:
            source_words = self.words_by_unit.get(unit_number, [])
        else:
            source_words = self.all_words

        valid_words = [
            w
            for w in source_words
            if w.synonyms
            and any(
                s.strip() and s.strip().lower() != w.word.lower()
                for s in w.synonyms
            )
        ]

        shuffled = list(valid_words)
        random.shuffle(shuffled)
        selected_pairs: List[MatchPairSim] = []
        used_synonyms: Set[str] = set()

        for word in shuffled:
            available_synonyms = [
                s.strip()
                for s in word.synonyms
                if s.strip() and s.strip().lower() != word.word.lower() and s.strip().lower() not in used_synonyms
            ]

            if available_synonyms:
                chosen_syn = available_synonyms[0]
                pair_id = str(uuid.uuid4())
                selected_pairs.append(MatchPairSim(id=pair_id, word=word, synonym=chosen_syn))
                used_synonyms.add(chosen_syn.lower())

                if len(selected_pairs) == 6:
                    break

        if len(selected_pairs) < 2 and shuffled:
            selected_pairs = []
            for word in shuffled[:6]:
                for s in word.synonyms:
                    s_clean = s.strip()
                    if s_clean and s_clean.lower() != word.word.lower():
                        pair_id = str(uuid.uuid4())
                        selected_pairs.append(MatchPairSim(id=pair_id, word=word, synonym=s_clean))
                        break

        self.pairs = selected_pairs
        right_opts = [
            RightOptionSim(id=str(uuid.uuid4()), pair_id=p.id, synonym=p.synonym)
            for p in selected_pairs
        ]
        random.shuffle(right_opts)
        self.right_options = right_opts

        self.matched_pairs.clear()
        self.selected_left = None
        self.selected_right = None
        self.attempts = 0
        self.is_finished = False
        self.wrong_right_ids.clear()
        self.wrong_left_ids.clear()

    def select_left(self, pair_id: str):
        if pair_id in self.matched_pairs:
            return
        self.selected_left = None if self.selected_left == pair_id else pair_id
        self.check_match()

    def select_right(self, option: RightOptionSim):
        if option.pair_id in self.matched_pairs:
            return
        self.selected_right = None if self.selected_right == option.id else option.id
        self.check_match()

    def check_match(self):
        if not self.selected_left or not self.selected_right:
            return

        self.attempts += 1
        left_id = self.selected_left
        right_id = self.selected_right

        matched_option = next((opt for opt in self.right_options if opt.id == right_id), None)
        if not matched_option:
            self.selected_left = None
            self.selected_right = None
            return

        if matched_option.pair_id == left_id:
            self.matched_pairs.add(left_id)
            self.wrong_right_ids.discard(right_id)
            self.wrong_left_ids.discard(left_id)
        else:
            self.wrong_right_ids.add(right_id)
            self.wrong_left_ids.add(left_id)

        self.selected_left = None
        self.selected_right = None

        if len(self.matched_pairs) == len(self.pairs) and self.pairs:
            self.is_finished = True


class TestAdversarialQuizAndMatching(unittest.TestCase):
    """Full Empirical Adversarial Test Suite for QuizView and MatchingView."""

    @classmethod
    def setUpClass(cls):
        random.seed(42069)
        cls.modules, cls.runtime_words, cls.words_by_unit = build_runtime_modules()
        cls.quiz_sim = QuizViewSimulator(cls.runtime_words, cls.words_by_unit)
        cls.match_sim = MatchingViewSimulator(cls.runtime_words, cls.words_by_unit)

    def test_adv_01_quiz_view_10000_questions_simulation(self):
        """Adversarial: Execute 10,000 question generations across all 80 units & global pool.
        Verify:
        - Exactly 4 options per question.
        - Strictly 4 unique options (0 duplicates, case-insensitive check).
        - Correct answer present in options.
        - No blank/whitespace options.
        """
        total_questions = 0
        target = 10000
        unit_pool = [None] + list(range(1, 81))
        modes = ["wordToDefinition", "definitionToWord"]

        duplicate_violations = []
        non_four_violations = []
        missing_answer_violations = []
        blank_violations = []

        while total_questions < target:
            for u in unit_pool:
                for mode in modes:
                    questions = self.quiz_sim.generate_questions(u, mode)
                    for q in questions:
                        total_questions += 1

                        # Strict 4 options check
                        if len(q.options) != 4:
                            non_four_violations.append((u, mode, q.word.word, len(q.options)))

                        # Strict uniqueness check (case-sensitive and case-insensitive)
                        unique_set = set(q.options)
                        unique_ci = {opt.lower() for opt in q.options}
                        if len(unique_set) != 4 or len(unique_ci) != 4:
                            duplicate_violations.append((u, mode, q.word.word, q.options))

                        # Correct answer in options check
                        if q.correct_answer not in q.options:
                            missing_answer_violations.append((u, mode, q.word.word, q.correct_answer, q.options))

                        # Non-blank check
                        if any(not opt.strip() for opt in q.options):
                            blank_violations.append((u, mode, q.word.word, q.options))

                        if total_questions >= target:
                            break
                    if total_questions >= target:
                        break
                if total_questions >= target:
                    break

        self.assertGreaterEqual(total_questions, target)
        self.assertEqual(len(non_four_violations), 0, f"Non-4 options violations: {non_four_violations[:5]}")
        self.assertEqual(len(duplicate_violations), 0, f"Duplicate options violations: {duplicate_violations[:5]}")
        self.assertEqual(len(missing_answer_violations), 0, f"Missing correct answer: {missing_answer_violations[:5]}")
        self.assertEqual(len(blank_violations), 0, f"Blank options: {blank_violations[:5]}")

    def test_adv_02_quiz_synthetic_small_unit_edge_cases(self):
        """Adversarial: Test QuizView on synthetic small units (<4 words) and zero-word units."""
        # Case A: 0 words
        q_empty = self.quiz_sim.generate_questions(None, "wordToDefinition", custom_source=[])
        self.assertEqual(len(q_empty), 0, "Empty word list must yield empty questions without error")

        # Case B: 1 word
        w1 = RuntimeWord(
            word="solitary",
            ipa="/ˈsɒlətri/",
            unit_numbers=[901],
            has_audio=True,
            definitions=[WordDefinitionData(part_of_speech="adjective", definition="Done alone", example="A solitary walk.")],
        )
        q_w1_w2d = self.quiz_sim.generate_questions(None, "wordToDefinition", custom_source=[w1])
        q_w1_d2w = self.quiz_sim.generate_questions(None, "definitionToWord", custom_source=[w1])

        self.assertEqual(len(q_w1_w2d), 1)
        self.assertEqual(len(q_w1_w2d[0].options), 4)
        self.assertEqual(len(set(q_w1_w2d[0].options)), 4)
        self.assertIn("Done alone", q_w1_w2d[0].options)

        self.assertEqual(len(q_w1_d2w), 1)
        self.assertEqual(len(q_w1_d2w[0].options), 4)
        self.assertEqual(len(set(q_w1_d2w[0].options)), 4)
        self.assertIn("solitary", q_w1_d2w[0].options)

        # Case C: 2 words
        w2_list = [
            RuntimeWord(word="w_alpha", ipa="", unit_numbers=[902], has_audio=False, definitions=[WordDefinitionData("n", "Alpha def", "")]),
            RuntimeWord(word="w_beta", ipa="", unit_numbers=[902], has_audio=False, definitions=[WordDefinitionData("n", "Beta def", "")]),
        ]
        q_w2 = self.quiz_sim.generate_questions(None, "wordToDefinition", custom_source=w2_list)
        self.assertEqual(len(q_w2), 2)
        for q in q_w2:
            self.assertEqual(len(q.options), 4)
            self.assertEqual(len(set(q.options)), 4)

        # Case D: 3 words
        w3_list = [
            RuntimeWord(word="w_one", ipa="", unit_numbers=[903], has_audio=False, definitions=[WordDefinitionData("n", "Def 1", "")]),
            RuntimeWord(word="w_two", ipa="", unit_numbers=[903], has_audio=False, definitions=[WordDefinitionData("n", "Def 2", "")]),
            RuntimeWord(word="w_three", ipa="", unit_numbers=[903], has_audio=False, definitions=[WordDefinitionData("n", "Def 3", "")]),
        ]
        q_w3 = self.quiz_sim.generate_questions(None, "wordToDefinition", custom_source=w3_list)
        self.assertEqual(len(q_w3), 3)
        for q in q_w3:
            self.assertEqual(len(q.options), 4)
            self.assertEqual(len(set(q.options)), 4)

        # Case E: Identical definition collision words (4 words with same definition)
        col_list = [
            RuntimeWord(word="c1", ipa="", unit_numbers=[904], has_audio=False, definitions=[WordDefinitionData("n", "Same Definition", "")]),
            RuntimeWord(word="c2", ipa="", unit_numbers=[904], has_audio=False, definitions=[WordDefinitionData("n", "Same Definition", "")]),
            RuntimeWord(word="c3", ipa="", unit_numbers=[904], has_audio=False, definitions=[WordDefinitionData("n", "Same Definition", "")]),
            RuntimeWord(word="c4", ipa="", unit_numbers=[904], has_audio=False, definitions=[WordDefinitionData("n", "Same Definition", "")]),
        ]
        q_col = self.quiz_sim.generate_questions(None, "wordToDefinition", custom_source=col_list)
        self.assertEqual(len(q_col), 4)
        for q in q_col:
            self.assertEqual(len(q.options), 4)
            self.assertEqual(len(set(q.options)), 4, f"Collision words produced duplicate options: {q.options}")

    def test_adv_03_matching_view_multiround_perfect_play(self):
        """Adversarial: Execute 1,600 multi-round Matching games across curriculum with perfect play."""
        total_rounds = 0
        completed_rounds = 0

        for unit_num in range(1, 81):
            for _ in range(20):  # 20 rounds per unit = 1,600 rounds
                self.match_sim.generate_pairs(unit_num)
                if not self.match_sim.pairs:
                    continue

                total_rounds += 1
                pairs_count = len(self.match_sim.pairs)
                self.assertEqual(pairs_count, len(self.match_sim.right_options))

                # Perfect play simulation
                for p in self.match_sim.pairs:
                    self.match_sim.select_left(p.id)
                    opt = next((o for o in self.match_sim.right_options if o.pair_id == p.id), None)
                    self.assertIsNotNone(opt)
                    self.match_sim.select_right(opt)

                if self.match_sim.is_finished and len(self.match_sim.matched_pairs) == pairs_count:
                    completed_rounds += 1
                    self.assertEqual(self.match_sim.attempts, pairs_count)

        self.assertGreater(total_rounds, 500)
        self.assertEqual(completed_rounds, total_rounds)

    def test_adv_04_matching_view_adversarial_mismatch_and_recovery(self):
        """Adversarial: Test MatchingView under chaotic wrong inputs, random guessing, and error recovery."""
        for _ in range(50):
            self.match_sim.generate_pairs(None)
            if len(self.match_sim.pairs) < 2:
                continue

            pairs_count = len(self.match_sim.pairs)

            # Adversarial step 1: Mismatch deliberately
            p0 = self.match_sim.pairs[0]
            wrong_opt = next(o for o in self.match_sim.right_options if o.pair_id != p0.id)

            self.match_sim.select_left(p0.id)
            self.match_sim.select_right(wrong_opt)

            self.assertEqual(self.match_sim.attempts, 1)
            self.assertNotIn(p0.id, self.match_sim.matched_pairs)
            self.assertIn(p0.id, self.match_sim.wrong_left_ids)
            self.assertIn(wrong_opt.id, self.match_sim.wrong_right_ids)

            # Adversarial step 2: Random guessing until all matched
            unmatched = [p.id for p in self.match_sim.pairs]
            guard_max_iterations = 200
            iteration = 0

            while len(self.match_sim.matched_pairs) < pairs_count and iteration < guard_max_iterations:
                iteration += 1
                left_cand = random.choice([p for p in self.match_sim.pairs if p.id not in self.match_sim.matched_pairs])
                right_cand = random.choice([o for o in self.match_sim.right_options if o.pair_id not in self.match_sim.matched_pairs])

                self.match_sim.select_left(left_cand.id)
                self.match_sim.select_right(right_cand)

            self.assertTrue(self.match_sim.is_finished)
            self.assertEqual(len(self.match_sim.matched_pairs), pairs_count)
            self.assertGreaterEqual(self.match_sim.attempts, pairs_count)

    def test_adv_05_matching_view_synthetic_edge_cases(self):
        """Adversarial: Test MatchingView on zero-synonyms, 1-synonym, dirty synonyms, and toggling."""
        # Case A: 0 words with synonyms
        w_nosyn = [RuntimeWord(word="nosyn", ipa="", unit_numbers=[1], has_audio=False)]
        self.match_sim.generate_pairs(None, custom_source=w_nosyn)
        self.assertEqual(len(self.match_sim.pairs), 0)
        self.assertEqual(len(self.match_sim.right_options), 0)

        # Case B: 1 word with synonym
        w_single = [RuntimeWord(word="lonely", ipa="", unit_numbers=[1], has_audio=False, synonyms=["isolated"])]
        self.match_sim.generate_pairs(None, custom_source=w_single)
        self.assertEqual(len(self.match_sim.pairs), 1)
        self.assertEqual(len(self.match_sim.right_options), 1)

        p = self.match_sim.pairs[0]
        opt = self.match_sim.right_options[0]
        self.match_sim.select_left(p.id)
        self.match_sim.select_right(opt)
        self.assertTrue(self.match_sim.is_finished)
        self.assertEqual(len(self.match_sim.matched_pairs), 1)

        # Case C: Dirty synonyms (self-referential)
        w_dirty = [
            RuntimeWord(word="pure", ipa="", unit_numbers=[1], has_audio=False, synonyms=["pure", "clean", "spotless"]),
            RuntimeWord(word="clean", ipa="", unit_numbers=[1], has_audio=False, synonyms=["clean", "pure"]),
        ]
        self.match_sim.generate_pairs(None, custom_source=w_dirty)
        for p in self.match_sim.pairs:
            self.assertNotEqual(p.synonym.lower(), p.word.word.lower())

        # Case D: Selection toggling / cancellation
        self.match_sim.generate_pairs(None)
        if len(self.match_sim.pairs) >= 2:
            p0 = self.match_sim.pairs[0]
            p1 = self.match_sim.pairs[1]

            self.match_sim.select_left(p0.id)
            self.assertEqual(self.match_sim.selected_left, p0.id)

            # Toggle off
            self.match_sim.select_left(p0.id)
            self.assertIsNone(self.match_sim.selected_left)

            # Switch left
            self.match_sim.select_left(p1.id)
            self.assertEqual(self.match_sim.selected_left, p1.id)


if __name__ == "__main__":
    unittest.main()
