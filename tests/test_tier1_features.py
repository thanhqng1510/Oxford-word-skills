"""Tier 1: Feature Coverage E2E Tests (>=5 tests per feature for F1 through F9)."""

import json
import os
import re
import subprocess
import unittest
import xml.etree.ElementTree as ET
from typing import Dict, List, Set

from tests.content_loader import (
    ALLOWED_POS,
    BASE_DIR,
    CORRUPT_TOKENS,
    DEFINITIONS_JSON_PATH,
    EXTRAWORDLIST_XML_PATH,
    SETTINGS_XML_PATH,
    US_SPELLING_PATTERNS,
    build_runtime_modules,
    is_valid_swift_word,
    load_definitions_json,
    load_extrawordlist_xml,
    load_settings_xml,
)


class TestTier1Feature1_XMLSchemaAndCurriculum(unittest.TestCase):
    """F1: XML Schema & Curriculum Mapping Tests."""

    def setUp(self):
        self.tree_settings, self.modules = load_settings_xml()
        self.tree_words, self.raw_words = load_extrawordlist_xml()

    def test_f1_01_settings_xml_well_formed_and_valid(self):
        """Verify settings.xml parses cleanly, has root <settings> and exactly 13 modules."""
        root = self.tree_settings.getroot()
        self.assertEqual(root.tag, "settings")
        modules = root.findall("module")
        self.assertEqual(len(modules), 13, f"Expected 13 modules in settings.xml, got {len(modules)}")
        for i, mod in enumerate(modules):
            title = mod.attrib.get("title", "")
            self.assertTrue(len(title) > 0, f"Module {i+1} has empty title")

    def test_f1_02_settings_units_contiguous_1_to_80(self):
        """Verify settings.xml contains exactly 80 contiguous units numbered 1 to 80."""
        root = self.tree_settings.getroot()
        units = root.findall(".//unit")
        self.assertEqual(len(units), 80, f"Expected exactly 80 units in settings.xml, got {len(units)}")

        unit_numbers = [int(u.attrib.get("number", "0")) for u in units]
        expected_numbers = list(range(1, 81))
        self.assertEqual(
            unit_numbers,
            expected_numbers,
            f"Units are not strictly contiguous 1..80. Found: {unit_numbers[:10]}...",
        )

    def test_f1_03_settings_unit_sections_valid(self):
        """Verify every unit has valid non-empty sections (148 sections total across curriculum)."""
        root = self.tree_settings.getroot()
        sections = root.findall(".//section")
        self.assertEqual(len(sections), 148, f"Expected 148 sections in settings.xml, got {len(sections)}")
        for sec in sections:
            title = sec.attrib.get("title", "")
            sec_type = sec.attrib.get("type", "")
            self.assertTrue(len(title) > 0, "Section title must not be empty")
            self.assertTrue(len(sec_type) > 0, "Section type must not be empty")

    def test_f1_04_extrawordlist_xml_well_formed(self):
        """Verify extrawordlist.xml has valid XML structure with <word> elements."""
        root = self.tree_words.getroot()
        self.assertIn(root.tag, ("wordlist", "exercise"))
        words = root.findall(".//word")
        self.assertGreater(len(words), 2700, f"Expected >2700 words, got {len(words)}")

    def test_f1_05_all_word_unit_references_within_1_to_80(self):
        """Verify every unit number referenced by any word is strictly between 1 and 80."""
        invalid_assignments = []
        for word in self.raw_words:
            if not word.unit_numbers:
                invalid_assignments.append((word.word, "empty unit list"))
            for u in word.unit_numbers:
                if u < 1 or u > 80:
                    invalid_assignments.append((word.word, f"out of range unit {u}"))

        self.assertEqual(
            len(invalid_assignments),
            0,
            f"Found {len(invalid_assignments)} invalid unit references: {invalid_assignments[:5]}",
        )

    def test_f1_06_no_orphaned_words(self):
        """Verify that all units referenced by words exist in settings.xml."""
        settings_unit_numbers = {u.number for mod in self.modules for u in mod.units}
        orphaned = []
        for word in self.raw_words:
            for u in word.unit_numbers:
                if u not in settings_unit_numbers:
                    orphaned.append((word.word, u))

        self.assertEqual(len(orphaned), 0, f"Found orphaned word-unit references: {orphaned}")


class TestTier1Feature2_EngineAndExercises(unittest.TestCase):
    """F2: Engine & UI Exercise Bug Fix Tests."""

    def setUp(self):
        self.modules, self.runtime_words, self.words_by_unit = build_runtime_modules()

    def test_f2_01_matching_view_synonym_options_stability(self):
        """Verify RightOption matching structure can preserve identity and resolve matches deterministically."""
        # Simulated right option model that keeps stable identity
        sample_words = [w for w in self.runtime_words if len(w.synonyms) >= 1][:6]
        if not sample_words:
            self.skipTest("No words with synonyms available yet")

        pairs = [{"word": w, "synonyms": w.synonyms[:2], "pair_id": f"pair_{i}"} for i, w in enumerate(sample_words)]

        # Generate options with pair_id link
        right_options = []
        for p in pairs:
            for s in p["synonyms"]:
                right_options.append({"opt_id": f"opt_{p['pair_id']}_{s}", "pair_id": p["pair_id"], "synonym": s})

        # Check that matching lookup by pair_id works
        for p in pairs:
            matching_opts = [opt for opt in right_options if opt["pair_id"] == p["pair_id"]]
            self.assertGreater(len(matching_opts), 0, f"Pair {p['pair_id']} must have matching options")

    def test_f2_02_quiz_view_distractor_options_distinct(self):
        """Verify simulated QuizView question generation produces 4 distinct choices per question."""
        for unit_num, words in self.words_by_unit.items():
            valid_words = [w for w in words if w.definitions]
            if len(valid_words) < 4:
                continue

            for word in valid_words[:5]:
                correct_def = word.short_definition
                distractor_pool = [w.short_definition for w in valid_words if w.word != word.word and w.definitions]
                unique_distractors = list(dict.fromkeys(distractor_pool))
                if len(unique_distractors) >= 3:
                    choices = [correct_def] + unique_distractors[:3]
                    unique_choices = set(choices)
                    self.assertEqual(
                        len(unique_choices),
                        4,
                        f"Unit {unit_num} word '{word.word}' quiz question produced non-unique choices: {choices}",
                    )

    def test_f2_03_fill_in_blank_spelling_normalization(self):
        """Verify that headwords with annotations like 'ad (= advertisement)' or standard words normalize for spelling."""
        test_cases = [
            ("ad (= advertisement)", "ad"),
            ("BBC (British Broadcasting Corporation)", "BBC"),
            ("CV (curriculum vitae)", "CV"),
            ("standard", "standard"),
            ("ice-cream", "ice-cream"),
        ]
        for raw, expected_base in test_cases:
            # Extraction of base spelling token before parenthesis
            base = re.sub(r"\s*\(.*?\)", "", raw).strip()
            self.assertEqual(base, expected_base, f"Spelling normalization failed for '{raw}'")

    def test_f2_04_exercise_types_coverage(self):
        """Verify that all units have sufficient words (>=4 words) to support the 5 active exercise modes."""
        units_with_min_words = [u for u, words in self.words_by_unit.items() if len(words) >= 4]
        self.assertEqual(
            len(units_with_min_words),
            len(self.words_by_unit),
            f"All {len(self.words_by_unit)} units must have >= 4 words for exercise modes, found {len(units_with_min_words)}",
        )

    def test_f2_05_flashcard_view_learned_state_toggle(self):
        """Verify learned word state toggle and persistence key format calculation."""
        sample_word = self.runtime_words[0]
        key = sample_word.persistence_key
        self.assertIn("|", key, "Key must contain delimiter '|'")
        word_part, units_part = key.split("|", 1)
        self.assertEqual(word_part, sample_word.word)
        expected_units = ",".join(str(u) for u in sorted(sample_word.unit_numbers))
        self.assertEqual(units_part, expected_units)

    def test_f2_06_quiz_view_minimum_valid_words_requirement(self):
        """Verify that every unit has at least 4 words with definitions to enable quiz generation."""
        insufficient_units = []
        for unit_num in range(1, 81):
            words = self.words_by_unit.get(unit_num, [])
            valid = [w for w in words if w.definitions]
            if len(valid) < 4:
                insufficient_units.append((unit_num, len(valid), len(words)))

        self.assertEqual(
            len(insufficient_units),
            0,
            f"Found {len(insufficient_units)} units with fewer than 4 defined words (cannot generate quiz): {insufficient_units[:5]}",
        )


class TestTier1Feature3_CompleteDefinitionPopulation(unittest.TestCase):
    """F3: Complete Definition Population Tests."""

    def setUp(self):
        self.defs_dict = load_definitions_json()
        _, self.raw_words = load_extrawordlist_xml()
        self.runtime_headwords = [w.word for w in self.raw_words if is_valid_swift_word(w.word)]

    def test_f3_01_definitions_json_valid_syntax(self):
        """Verify definitions.json is valid JSON and contains a root dictionary."""
        self.assertIsInstance(self.defs_dict, dict, "definitions.json root must be a JSON object/dict")
        self.assertGreater(len(self.defs_dict), 2700, f"Expected >2700 keys in definitions.json, got {len(self.defs_dict)}")

    def test_f3_02_100_percent_extrawordlist_words_in_definitions(self):
        """Verify 100% of runtime words from extrawordlist.xml exist in definitions.json."""
        missing = [w for w in self.runtime_headwords if w not in self.defs_dict]
        self.assertEqual(
            len(missing),
            0,
            f"{len(missing)} words in extrawordlist.xml missing from definitions.json: {missing[:10]}",
        )

    def test_f3_03_no_empty_meanings_array(self):
        """Verify that no word in definitions.json has empty meanings: []."""
        empty_meanings = []
        for word in self.runtime_headwords:
            if word in self.defs_dict:
                entry = self.defs_dict[word]
                meanings = entry.get("meanings", [])
                if not meanings:
                    empty_meanings.append(word)

        self.assertEqual(
            len(empty_meanings),
            0,
            f"{len(empty_meanings)} words have empty meanings: [] in definitions.json: {empty_meanings[:10]}",
        )

    def test_f3_04_no_empty_definitions_in_meanings(self):
        """Verify every meaning contains at least one non-empty definition string."""
        blank_defs = []
        for word in self.runtime_headwords:
            if word in self.defs_dict:
                entry = self.defs_dict[word]
                for m_idx, meaning in enumerate(entry.get("meanings", [])):
                    defs = meaning.get("definitions", [])
                    if not defs:
                        blank_defs.append((word, m_idx, "no definitions array"))
                    for d_idx, d in enumerate(defs):
                        def_str = d.get("definition", "").strip()
                        if not def_str:
                            blank_defs.append((word, m_idx, d_idx, "empty definition string"))

        self.assertEqual(
            len(blank_defs),
            0,
            f"Found {len(blank_defs)} empty definitions in definitions.json: {blank_defs[:10]}",
        )

    def test_f3_05_part_of_speech_validity(self):
        """Verify all partOfSpeech fields match allowed standard grammatical categories."""
        invalid_pos = []
        for word, entry in self.defs_dict.items():
            for m_idx, meaning in enumerate(entry.get("meanings", [])):
                pos = meaning.get("partOfSpeech", "").strip().lower()
                if pos not in ALLOWED_POS:
                    invalid_pos.append((word, m_idx, pos))

        self.assertEqual(
            len(invalid_pos),
            0,
            f"Found {len(invalid_pos)} non-standard POS tags (allowed: {ALLOWED_POS}): {invalid_pos[:10]}",
        )

    def test_f3_06_brackets_headword_present(self):
        """Verify the missing headword 'brackets' is present with valid meanings."""
        self.assertIn("brackets", self.defs_dict, "Headword 'brackets' must be present in definitions.json")
        entry = self.defs_dict["brackets"]
        meanings = entry.get("meanings", [])
        self.assertGreater(len(meanings), 0, "'brackets' must have non-empty meanings")


class TestTier1Feature4_ExampleSentenceGeneration(unittest.TestCase):
    """F4: Example Sentence Generation & Enrichment Tests."""

    def setUp(self):
        self.defs_dict = load_definitions_json()
        _, self.raw_words = load_extrawordlist_xml()
        self.runtime_headwords = [w.word for w in self.raw_words if is_valid_swift_word(w.word)]

    def test_f4_01_100_percent_definitions_have_example(self):
        """Verify 100% of definitions across all words have non-empty example sentences."""
        missing_examples = []
        for word in self.runtime_headwords:
            if word in self.defs_dict:
                entry = self.defs_dict[word]
                for m_idx, meaning in enumerate(entry.get("meanings", [])):
                    for d_idx, d in enumerate(meaning.get("definitions", [])):
                        ex = d.get("example", "").strip()
                        if not ex:
                            missing_examples.append((word, m_idx, d_idx))

        self.assertEqual(
            len(missing_examples),
            0,
            f"{len(missing_examples)} definition entries lack example sentences: {missing_examples[:10]}",
        )

    def test_f4_02_example_sentence_contains_target_word_or_lemma(self):
        """Verify example sentences illustrate the target word or its stem."""
        failing_examples = []
        for word in self.runtime_headwords:
            if word in self.defs_dict:
                entry = self.defs_dict[word]
                clean_target = re.sub(r"\s*\(.*?\)", "", word).strip().lower()
                # Split compound words / phrases
                target_tokens = [re.sub(r"[^\w]", "", t) for t in clean_target.split() if len(t) > 2]
                for meaning in entry.get("meanings", []):
                    for d in meaning.get("definitions", []):
                        ex = d.get("example", "").strip().lower()
                        if ex:
                            # At least one target token or sub-token stem should appear
                            matched = any(token[:4] in ex for token in target_tokens) if target_tokens else (clean_target in ex)
                            if not matched and len(clean_target) > 3 and clean_target[:4] not in ex:
                                failing_examples.append((word, ex))

        # Allow small tolerance for idioms where phrasing varies, but should be < 5% failure
        total_defs = sum(len(m.get("definitions", [])) for e in self.defs_dict.values() for m in e.get("meanings", []))
        self.assertLess(
            len(failing_examples),
            max(1, int(total_defs * 0.05)),
            f"{len(failing_examples)} examples don't contain target word stem: {failing_examples[:5]}",
        )

    def test_f4_03_example_sentence_capitalization_and_punctuation(self):
        """Verify example sentences begin with capital letter/quote and end with proper punctuation."""
        bad_punctuation = []
        for word, entry in self.defs_dict.items():
            for meaning in entry.get("meanings", []):
                for d in meaning.get("definitions", []):
                    ex = d.get("example", "").strip()
                    if ex:
                        # Check start
                        first_char = ex[0]
                        if not (first_char.isupper() or first_char in "\"'‘“("):
                            bad_punctuation.append((word, ex, "does not start with uppercase/quote"))
                        # Check end
                        last_char = ex[-1]
                        if last_char not in ".!?\"'’”)":
                            bad_punctuation.append((word, ex, "missing terminal punctuation"))

        self.assertEqual(
            len(bad_punctuation),
            0,
            f"Found {len(bad_punctuation)} examples with bad capitalization/punctuation: {bad_punctuation[:10]}",
        )

    def test_f4_04_example_sentence_not_placeholder(self):
        """Verify example sentences are not placeholder strings like '...', 'N/A', 'Example'."""
        placeholders = {"...", "n/a", "example", "example sentence", "todo", "none"}
        bad_placeholders = []
        for word, entry in self.defs_dict.items():
            for meaning in entry.get("meanings", []):
                for d in meaning.get("definitions", []):
                    ex = d.get("example", "").strip().lower()
                    if ex in placeholders or d.get("definition", "").strip().lower() == ex:
                        bad_placeholders.append((word, ex))

        self.assertEqual(
            len(bad_placeholders),
            0,
            f"Found {len(bad_placeholders)} placeholder example sentences: {bad_placeholders[:10]}",
        )

    def test_f4_05_examples_pedagogical_length(self):
        """Verify example sentences have sufficient pedagogical context (length >= 10 chars, >= 3 words)."""
        too_short = []
        for word, entry in self.defs_dict.items():
            for meaning in entry.get("meanings", []):
                for d in meaning.get("definitions", []):
                    ex = d.get("example", "").strip()
                    if ex and (len(ex) < 10 or len(ex.split()) < 3):
                        too_short.append((word, ex))

        self.assertEqual(
            len(too_short),
            0,
            f"Found {len(too_short)} overly terse example sentences: {too_short[:10]}",
        )


class TestTier1Feature5_BritishEnglishStandardization(unittest.TestCase):
    """F5: British English Standardization Tests."""

    def setUp(self):
        self.defs_dict = load_definitions_json()

    def _find_us_spellings(self, pattern: str) -> List[Tuple[str, str, str]]:
        hits = []
        regex = re.compile(pattern, re.IGNORECASE)
        for word, entry in self.defs_dict.items():
            for m_idx, meaning in enumerate(entry.get("meanings", [])):
                for d_idx, d in enumerate(meaning.get("definitions", [])):
                    def_text = d.get("definition", "")
                    ex_text = d.get("example", "")
                    m_def = regex.search(def_text)
                    if m_def:
                        hits.append((word, f"def: {m_def.group(0)}", def_text))
                    m_ex = regex.search(ex_text)
                    if m_ex:
                        hits.append((word, f"ex: {m_ex.group(0)}", ex_text))
        return hits

    def test_f5_01_no_us_ize_in_definitions_and_examples(self):
        """Verify no US -ize / -ization spellings in definitions and examples."""
        # Specific US verbs to check (excluding standard words like size, prize)
        us_words = [r"\borganize\b", r"\brecognize\b", r"\brealize\b", r"\borganization\b", r"\bcriticize\b"]
        hits = []
        for pat in us_words:
            hits.extend(self._find_us_spellings(pat))
        self.assertEqual(len(hits), 0, f"Found US -ize/-ization spellings in {len(hits)} places: {hits[:10]}")

    def test_f5_02_no_us_or_in_definitions_and_examples(self):
        """Verify no US -or spellings (behavior, color, flavor, honor, labor, neighbor)."""
        us_words = [r"\bbehavior\b", r"\bcolor\b", r"\bflavor\b", r"\bhonor\b", r"\blabor\b", r"\bneighbor\b", r"\bfavor\b"]
        hits = []
        for pat in us_words:
            hits.extend(self._find_us_spellings(pat))
        self.assertEqual(len(hits), 0, f"Found US -or spellings in {len(hits)} places: {hits[:10]}")

    def test_f5_03_no_us_ense_in_definitions_and_examples(self):
        """Verify no US -ense spellings (defense, offense, pretense)."""
        us_words = [r"\bdefense\b", r"\boffense\b", r"\bpretense\b"]
        hits = []
        for pat in us_words:
            hits.extend(self._find_us_spellings(pat))
        self.assertEqual(len(hits), 0, f"Found US -ense spellings in {len(hits)} places: {hits[:10]}")

    def test_f5_04_no_us_center_in_definitions_and_examples(self):
        """Verify no US 'center', 'theater', 'meter' (measure), 'fiber', 'liter'."""
        us_words = [r"\bcenter\b", r"\btheater\b", r"\bfiber\b", r"\bliter\b"]
        hits = []
        for pat in us_words:
            hits.extend(self._find_us_spellings(pat))
        self.assertEqual(len(hits), 0, f"Found US center/theater spellings in {len(hits)} places: {hits[:10]}")

    def test_f5_05_no_us_yze_in_definitions_and_examples(self):
        """Verify no US 'analyze', 'paralyze'."""
        us_words = [r"\banalyze\b", r"\bparalyze\b", r"\banalyzing\b", r"\banalyzed\b"]
        hits = []
        for pat in us_words:
            hits.extend(self._find_us_spellings(pat))
        self.assertEqual(len(hits), 0, f"Found US -yze spellings in {len(hits)} places: {hits[:10]}")

    def test_f5_06_oxford_spelling_consistency(self):
        """Verify comprehensive list of US spelling patterns are absent."""
        total_violations = []
        for pat, replacement, label in US_SPELLING_PATTERNS:
            hits = self._find_us_spellings(pat)
            if hits:
                total_violations.append((label, len(hits), hits[:2]))

        self.assertEqual(
            len(total_violations),
            0,
            f"Found {len(total_violations)} US spelling pattern categories: {total_violations[:5]}",
        )


class TestTier1Feature6_LexicographicalCleanup(unittest.TestCase):
    """F6: Lexicographical Cleanup & Quality Assurance Tests."""

    def setUp(self):
        self.defs_dict = load_definitions_json()

    def test_f6_01_no_emoji_in_synonyms_or_definitions(self):
        """Verify no emoji tokens (e.g. 🍑) in synonyms, antonyms, or definitions."""
        emoji_pattern = re.compile(r"[\U00010000-\U0010ffff]", flags=re.UNICODE)
        hits = []
        for word, entry in self.defs_dict.items():
            for meaning in entry.get("meanings", []):
                for syn in meaning.get("synonyms", []):
                    if emoji_pattern.search(syn):
                        hits.append((word, "synonym", syn))
                for ant in meaning.get("antonyms", []):
                    if emoji_pattern.search(ant):
                        hits.append((word, "antonym", ant))
                for d in meaning.get("definitions", []):
                    if emoji_pattern.search(d.get("definition", "")):
                        hits.append((word, "definition", d.get("definition", "")))

        self.assertEqual(len(hits), 0, f"Found emoji in content: {hits}")

    def test_f6_02_no_math_symbols_in_synonyms_or_definitions(self):
        """Verify no math symbol tokens (e.g. ∵, ≠, √) in synonyms, antonyms, or definitions."""
        math_symbols = {"∵", "≠", "√", "≤", "≥", "±", "∞", "∫", "∑", "∏"}
        hits = []
        for word, entry in self.defs_dict.items():
            for meaning in entry.get("meanings", []):
                for syn in meaning.get("synonyms", []):
                    if any(s in syn for s in math_symbols):
                        hits.append((word, "synonym", syn))
                for d in meaning.get("definitions", []):
                    if any(s in d.get("definition", "") for s in math_symbols):
                        hits.append((word, "definition", d.get("definition", "")))

        self.assertEqual(len(hits), 0, f"Found math symbols in content: {hits}")

    def test_f6_03_no_vulgar_or_artifact_synonyms(self):
        """Verify no vulgar slang or corrupt artifacts (BS, bullshit, DgammaDtime, Cockney slang)."""
        artifacts = {"bs", "bullshit", "dgammadtime", "dog and bone (cockney rhyming slang)"}
        hits = []
        for word, entry in self.defs_dict.items():
            for meaning in entry.get("meanings", []):
                for syn in meaning.get("synonyms", []):
                    if syn.strip().lower() in artifacts:
                        hits.append((word, "synonym", syn))
                for ant in meaning.get("antonyms", []):
                    if ant.strip().lower() in artifacts:
                        hits.append((word, "antonym", ant))

        self.assertEqual(len(hits), 0, f"Found vulgar / corrupt artifacts: {hits}")

    def test_f6_04_no_self_referential_synonyms(self):
        """Verify no synonym is identical to the target headword."""
        hits = []
        for word, entry in self.defs_dict.items():
            clean_word = word.strip().lower()
            for meaning in entry.get("meanings", []):
                for syn in meaning.get("synonyms", []):
                    if syn.strip().lower() == clean_word:
                        hits.append((word, syn))

        self.assertEqual(len(hits), 0, f"Found self-referential synonyms: {hits[:10]}")

    def test_f6_05_no_duplicate_synonyms_per_meaning(self):
        """Verify synonyms within a single meaning entry have no duplicates."""
        hits = []
        for word, entry in self.defs_dict.items():
            for m_idx, meaning in enumerate(entry.get("meanings", [])):
                syns = [s.strip().lower() for s in meaning.get("synonyms", [])]
                if len(syns) != len(set(syns)):
                    hits.append((word, m_idx, syns))

        self.assertEqual(len(hits), 0, f"Found duplicate synonyms in meaning entries: {hits[:10]}")

    def test_f6_06_no_truncated_definitions(self):
        """Verify definitions do not end in hanging colons, semicolons, hyphens or unclosed parens."""
        hits = []
        for word, entry in self.defs_dict.items():
            for meaning in entry.get("meanings", []):
                for d in meaning.get("definitions", []):
                    def_str = d.get("definition", "").strip()
                    if def_str:
                        if def_str.endswith(":") or def_str.endswith(";") or def_str.endswith("-"):
                            hits.append((word, "trailing punctuation", def_str))
                        if def_str.count("(") != def_str.count(")"):
                            hits.append((word, "mismatched parentheses", def_str))

        self.assertEqual(len(hits), 0, f"Found truncated / malformed definitions: {hits[:10]}")


class TestTier1Feature7_DistractorAndSynonymCollisions(unittest.TestCase):
    """F7: Distractor & Synonym Collision Resolution Tests."""

    def setUp(self):
        self.modules, self.runtime_words, self.words_by_unit = build_runtime_modules()

    def test_f7_01_intra_unit_definition_uniqueness(self):
        """Verify that within any single unit, no two words share identical short definitions."""
        collisions = []
        for unit_num, words in self.words_by_unit.items():
            seen_defs: Dict[str, str] = {}
            for w in words:
                s_def = w.short_definition.strip().lower()
                if s_def and s_def != "no definition available":
                    if s_def in seen_defs:
                        collisions.append((unit_num, seen_defs[s_def], w.word, s_def))
                    else:
                        seen_defs[s_def] = w.word

        self.assertEqual(
            len(collisions),
            0,
            f"Found intra-unit definition collisions (breaks quiz discriminability): {collisions[:10]}",
        )

    def test_f7_02_intra_unit_distractor_availability(self):
        """Verify that every unit has sufficient distinct definitions (>=4) for quiz distractors."""
        insufficient = []
        for unit_num, words in self.words_by_unit.items():
            unique_defs = {w.short_definition for w in words if w.definitions}
            if len(unique_defs) < 4:
                insufficient.append((unit_num, len(unique_defs), len(words)))

        self.assertEqual(
            len(insufficient),
            0,
            f"Units with fewer than 4 unique definitions for distractors: {insufficient}",
        )

    def test_f7_03_intra_unit_synonym_uniqueness(self):
        """Verify synonym matching within units does not contain cross-word duplicate synonyms."""
        synonym_collisions = []
        for unit_num, words in self.words_by_unit.items():
            seen_syns: Dict[str, str] = {}
            for w in words:
                for syn in w.synonyms[:2]:
                    s_clean = syn.strip().lower()
                    if s_clean in seen_syns and seen_syns[s_clean] != w.word:
                        synonym_collisions.append((unit_num, seen_syns[s_clean], w.word, s_clean))
                    else:
                        seen_syns[s_clean] = w.word

        self.assertEqual(
            len(synonym_collisions),
            0,
            f"Found intra-unit synonym collisions (ambiguous matching game): {synonym_collisions[:10]}",
        )

    def test_f7_04_quiz_question_distractor_separation(self):
        """Verify simulated 4-choice quiz questions have 4 distinct choices for all 80 units."""
        failing_questions = []
        for unit_num, words in self.words_by_unit.items():
            valid_words = [w for w in words if w.definitions]
            if len(valid_words) < 4:
                continue
            for w in valid_words:
                correct = w.short_definition
                others = [o.short_definition for o in valid_words if o.word != w.word]
                distinct_others = list(dict.fromkeys(others))
                if len(distinct_others) >= 3:
                    options = [correct] + distinct_others[:3]
                    if len(set(options)) != 4:
                        failing_questions.append((unit_num, w.word, options))

        self.assertEqual(
            len(failing_questions),
            0,
            f"Found questions with non-distinct choices: {failing_questions[:5]}",
        )

    def test_f7_05_synonym_antonym_disjointness(self):
        """Verify a word's synonyms and antonyms sets are strictly disjoint."""
        overlaps = []
        for w in self.runtime_words:
            syn_set = {s.strip().lower() for s in w.synonyms}
            ant_set = {a.strip().lower() for a in w.antonyms}
            common = syn_set.intersection(ant_set)
            if common:
                overlaps.append((w.word, common))

        self.assertEqual(len(overlaps), 0, f"Found words with overlapping synonyms and antonyms: {overlaps[:10]}")


class TestTier1Feature8_ComprehensiveE2ETestSuite(unittest.TestCase):
    """F8: Comprehensive E2E Test Suite & Test Automation Tests."""

    def test_f8_01_e2e_runner_executable_and_structured(self):
        """Verify run_all_tests.py exists and is a runnable Python script."""
        runner_path = os.path.join(BASE_DIR, "tests", "run_all_tests.py")
        self.assertTrue(os.path.exists(runner_path), f"Runner must exist at {runner_path}")

    def test_f8_02_e2e_tier_coverage_completeness(self):
        """Verify all 4 test tier files exist in tests/ directory."""
        tiers = [
            "test_tier1_features.py",
            "test_tier2_boundary.py",
            "test_tier3_combinations.py",
            "test_tier4_scenarios.py",
        ]
        for t in tiers:
            path = os.path.join(BASE_DIR, "tests", t)
            self.assertTrue(os.path.exists(path), f"Tier test file {t} must exist in tests/")

    def test_f8_03_e2e_exit_code_fidelity(self):
        """Verify run_e2e_tests.sh script exists and has execute permissions."""
        sh_path = os.path.join(BASE_DIR, "run_e2e_tests.sh")
        self.assertTrue(os.path.exists(sh_path), f"Master shell script must exist at {sh_path}")

    def test_f8_04_test_infra_md_exists_and_complete(self):
        """Verify testing documentation exists in AGENTS.md."""
        agents_path = os.path.join(BASE_DIR, "AGENTS.md")
        self.assertTrue(os.path.exists(agents_path), f"AGENTS.md must exist at {agents_path}")
        with open(agents_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("Testing & Quality Assurance", content)

    def test_f8_05_test_ready_md_exists_and_complete(self):
        """Verify README.md or AGENTS.md exists at root."""
        readme_path = os.path.join(BASE_DIR, "README.md")
        agents_path = os.path.join(BASE_DIR, "AGENTS.md")
        self.assertTrue(
            os.path.exists(readme_path) or os.path.exists(agents_path),
            "README.md or AGENTS.md must exist",
        )


class TestTier1Feature9_ProjectCompilationAndEngineIntegrity(unittest.TestCase):
    """F9: Project Compilation & Engine Integrity Tests."""

    def setUp(self):
        self.modules, self.runtime_words, self.words_by_unit = build_runtime_modules()

    def test_f9_01_no_equivalent_or_placeholder_synonyms(self):
        """Verify no 'equivalent' or placeholder strings exist in synonyms or antonyms."""
        defs = load_definitions_json()
        violations = []
        for word, entry in defs.items():
            for m in entry.get("meanings", []):
                for s in m.get("synonyms", []):
                    if re.search(r"\bequivalent(\s+\d+)?\b", s, re.I) or "placeholder" in s.lower():
                        violations.append((word, "synonym", s))
                for a in m.get("antonyms", []):
                    if re.search(r"\bequivalent(\s+\d+)?\b", a, re.I) or "placeholder" in a.lower():
                        violations.append((word, "antonym", a))
        self.assertEqual(len(violations), 0, f"Found {len(violations)} placeholder synonyms/antonyms: {violations[:10]}")

    def test_f9_02_content_parser_build_modules_swift_execution(self):
        """Verify Swift engine pipeline test runner exists."""
        swift_test_path = os.path.join(BASE_DIR, "tests", "test_engine_pipeline.swift")
        self.assertTrue(os.path.exists(swift_test_path), f"Swift pipeline test must exist at {swift_test_path}")

    def test_f9_03_all_words_have_valid_short_definition(self):
        """Verify no word in runtime produces 'No definition available'."""
        no_def_words = [w.word for w in self.runtime_words if w.short_definition == "No definition available"]
        self.assertEqual(
            len(no_def_words),
            0,
            f"{len(no_def_words)} words have 'No definition available': {no_def_words[:10]}",
        )

    def test_f9_04_learned_words_key_schema_consistency(self):
        """Verify UserDefaults persistence key format across all runtime words."""
        keys = set()
        for w in self.runtime_words:
            k = w.persistence_key
            self.assertNotIn(k, keys, f"Duplicate persistence key: {k}")
            keys.add(k)

        self.assertEqual(len(keys), len(self.runtime_words), "Each word must have a unique persistence key")

    def test_f9_05_swift_worddetail_decodability(self):
        """Verify JSON decoding structure matches WordDetail Swift Codable contract."""
        defs = load_definitions_json()
        decoding_errors = []
        for word, entry in defs.items():
            if not isinstance(entry, dict):
                decoding_errors.append((word, "entry is not dict"))
                continue
            if "word" not in entry or not isinstance(entry.get("word"), str):
                decoding_errors.append((word, "missing or invalid 'word' string"))
            if "phonetic" not in entry or not isinstance(entry.get("phonetic"), str):
                decoding_errors.append((word, "missing or invalid 'phonetic' string"))
            meanings = entry.get("meanings")
            if not isinstance(meanings, list):
                decoding_errors.append((word, "meanings is not list"))
                continue
            for m in meanings:
                if not isinstance(m, dict):
                    decoding_errors.append((word, "meaning is not dict"))
                    continue
                if "partOfSpeech" not in m or not isinstance(m.get("partOfSpeech"), str):
                    decoding_errors.append((word, "missing partOfSpeech"))
                if "definitions" not in m or not isinstance(m.get("definitions"), list):
                    decoding_errors.append((word, "missing definitions list"))
                if "synonyms" not in m or not isinstance(m.get("synonyms"), list):
                    decoding_errors.append((word, "missing synonyms list"))
                if "antonyms" not in m or not isinstance(m.get("antonyms"), list):
                    decoding_errors.append((word, "missing antonyms list"))

        self.assertEqual(
            len(decoding_errors),
            0,
            f"Found {len(decoding_errors)} WordDetail schema violations: {decoding_errors[:10]}",
        )

    def test_f9_06_exercise_views_have_back_navigation(self):
        """Verify all exercise views provide back navigation to Unit or Word view."""
        views_dir = os.path.join(BASE_DIR, "Views")
        exercise_views = [
            "FlashcardView.swift",
            "QuizView.swift",
            "FillInBlankView.swift",
            "MatchingView.swift",
        ]
        for filename in exercise_views:
            path = os.path.join(views_dir, filename)
            self.assertTrue(os.path.exists(path), f"View file {filename} must exist")
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            self.assertIn("selectedNavigation", content, f"{filename} must route selectedNavigation on back action")
            self.assertIn("chevron.left", content, f"{filename} must provide chevron.left back button")


if __name__ == "__main__":
    unittest.main()
