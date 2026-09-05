# Test Infrastructure Specification — Oxford Word Skills

## 1. Test Philosophy & Principles

The test infrastructure for Oxford Word Skills adheres to an **opaque-box, requirement-driven verification methodology** derived directly from `ORIGINAL_REQUEST.md`, `PROJECT.md`, and Oxford University Press curriculum standards.

1. **Requirement-Driven & Opaque-Box**:
   - Tests evaluate system behavior, data integrity, and contract conformance rather than implementation internals.
   - Assertions are derived from authoritative specifications: English Wiktionary (en.wiktionary.org) UK Received Pronunciation (RP) standards, Oxford Word Skills syllabus structures, and Apple framework contracts.
2. **Zero False Positives / Zero Facade Tests**:
   - Every test exercises real data structures and real algorithms. No mocks of core domain data (`definitions.json`, `extrawordlist.xml`, `settings.xml`).
   - Failure messages provide precise diagnostic feedback: headword, unit number, offending character or token, and line-level trace.
3. **Progressive & Multi-Tiered Verification**:
   - Five distinct validation layers ensure complete defect trapping:
     - **Tier 1 (Feature Coverage)**: Validates functional and structural specifications for all system features (F1 through F9).
     - **Tier 2 (Boundary & Corner Cases)**: Stress-tests character sets, string bounds, multi-unit mappings, and malformed token rejections.
     - **Tier 3 (Cross-Feature Combinations)**: Evaluates pairwise module interactions, fallback mechanisms, phonetic/speech synchronization, and persistence stability.
     - **Tier 4 (Real-World Workloads)**: Simulates end-to-end user workflows across all 80 units, 12 modules, and 2,781 runtime words across all five active study modes.
     - **Native Swift Engine Harness**: Validates compilation, typed Codable deserialization, and runtime model building directly within the Swift runtime.
4. **Strict Dialect & Lexicographical Integrity**:
   - British English (Received Pronunciation) standard enforcement across all vocabulary items.
   - Absolute rejection of unconverted legacy ASCII SAMPA tokens, bracketed narrow allophones `[...]`, Americanisms (`ɚ`, `ɝ`, `ɾ`), ASCII colons `:`, and malformed trailing slashes `//`.

---

## 2. Coverage Thresholds & Requirements

| Suite Tier | Scope & Focus | Minimum Coverage Threshold | Primary Verification Target |
|---|---|---|---|
| **Tier 1: Feature Coverage** | Features F1 through F9 functional requirements | **>= 5 tests per feature** | Curriculum schema, exercise mechanics, definition completeness, IPA formatting, British spelling, lexicographical hygiene, quiz distractors, automation, engine integrity |
| **Tier 2: Boundary & Corner Cases** | Extreme boundaries, token sanitization, malformed input rejection | **>= 5 boundary tests per domain** | Character whitelist, SAMPA rejection, bracket rejection, colon rejection, Americanism rejection, trailing slashes, empty strings, punctuation bounds, multi-unit collisions |
| **Tier 3: Combinations** | Cross-feature interactions, fallback, pipeline flow | **Pairwise & multi-feature coverage** | XML / JSON fallback, speechText / cleanWord / IPA alignment, distractor generation with IPA, audio presence, module aggregation |
| **Tier 4: Scenarios** | Full application lifecycles & curriculum traversal | **100% curriculum coverage (80 units, 12 modules)** | Full curriculum audit (all 2,781 runtime words), 15-question quiz sessions, reverse quiz sessions, flashcard deck flows, matching games, search navigation |
| **Native Swift Harness** | Runtime memory model & Codable deserialization | **100% runtime word validation** | `ContentParser.buildModules()`, `WordDetail` decoding, `Word.ipa` invariant verification |

---

## 3. Feature Inventory Test Mapping

Every feature from `PROJECT.md` is mapped to explicit test classes across the test suite:

### Tier 1: Feature Coverage (`tests/test_tier1_features.py`)
- **Feature 1 (F1: XML Schema & Curriculum Invariants)**:
  - Class: `TestTier1Feature1_XMLSchemaAndCurriculum`
  - Tests: Contiguous 80 units (`test_f1_01`), 13 module groupings (`test_f1_02`), word-unit mapping (`test_f1_03`), section counts (`test_f1_04`), valid headwords (`test_f1_05`).
- **Feature 2 (F2: Engine & Exercise Modes)**:
  - Class: `TestTier1Feature2_EngineAndExercises`
  - Tests: Exercise enum completeness (`test_f2_01`), minimum unit words (`test_f2_02`), audio flags (`test_f2_03`), quiz generation sufficiency (`test_f2_04`).
- **Feature 3 (F3: Complete Definition & Phonetic Population)**:
  - Class: `TestTier1Feature3_CompleteDefinitionPopulation`
  - Tests: JSON syntax (`test_f3_01`), 100% headword coverage (`test_f3_02`), non-empty meanings (`test_f3_03`), non-empty definitions (`test_f3_04`), standard POS (`test_f3_05`), 'brackets' headword (`test_f3_06`), **phonetic completeness & /.../ format (`test_f3_07`)**, **zero raw SAMPA or illegal characters (`test_f3_08`)**, **valid length and characters (`test_f3_09`)**.
- **Feature 4 (F4: Example Sentence Generation & Enrichment)**:
  - Class: `TestTier1Feature4_ExampleSentenceGeneration`
  - Tests: 100% example presence (`test_f4_01`), headword inclusion (`test_f4_02`), capitalization & punctuation (`test_f4_03`), no truncated examples (`test_f4_04`), length boundaries (`test_f4_05`).
- **Feature 5 (F5: British English Standardization)**:
  - Class: `TestTier1Feature5_BritishEnglishStandardization`
  - Tests: No US -ize (`test_f5_01`), no US -or (`test_f5_02`), no US -ense (`test_f5_03`), no US -er center/theater (`test_f5_04`), no US -yze (`test_f5_05`), Oxford spelling consistency (`test_f5_06`).
- **Feature 6 (F6: Lexicographical Cleanup)**:
  - Class: `TestTier1Feature6_LexicographicalCleanup`
  - Tests: No emoji (`test_f6_01`), no math symbols (`test_f6_02`), no vulgarities (`test_f6_03`), no self-referential synonyms (`test_f6_04`), no duplicates (`test_f6_05`), no truncated definitions (`test_f6_06`).
- **Feature 7 (F7: Distractor & Synonym Collisions)**:
  - Class: `TestTier1Feature7_DistractorAndSynonymCollisions`
  - Tests: Intra-unit definition uniqueness (`test_f7_01`), distractor availability (`test_f7_02`), synonym uniqueness (`test_f7_03`), quiz separation (`test_f7_04`), synonym/antonym disjointness (`test_f7_05`).
- **Feature 8 (F8: Comprehensive E2E Test Automation)**:
  - Class: `TestTier1Feature8_ComprehensiveE2ETestSuite`
  - Tests: Runner executable (`test_f8_01`), all 4 tier files present (`test_f8_02`), shell exit code fidelity (`test_f8_03`), `TEST_INFRA.md` existence & completeness (`test_f8_04`), `TEST_READY.md` existence & completeness (`test_f8_05`).
- **Feature 9 (F9: Runtime Invariants & Engine Pipeline Integrity)**:
  - Class: `TestTier1Feature9_ProjectCompilationAndEngineIntegrity`
  - Tests: No placeholder synonyms (`test_f9_01`), Swift test harness exists (`test_f9_02`), all words have short definition (`test_f9_03`), persistence key schema (`test_f9_04`), WordDetail Codable schema (`test_f9_05`), exercise back navigation (`test_f9_06`), **runtime words non-empty /.../ IPA completeness (`test_f9_07`)**, **runtime words zero lingering SAMPA characters (`test_f9_08`)**.

---

### Tier 2: Boundary & Corner Cases (`tests/test_tier2_boundary.py`)
- `test_t2_01_no_empty_string_definitions_or_meanings`: Extreme empty string boundary across all entries.
- `test_t2_02_definition_punctuation_boundaries`: Unbalanced parentheses, brackets, or illegal trailing punctuation.
- `test_t2_03_multi_unit_words_mapping`: 226+ multi-unit words mapped to all designated units.
- `test_t2_04_annotated_headwords_lexicographical_integrity`: Parenthetical glosses (`ad (= advertisement)`).
- `test_t2_05_missing_meanings_detection`: Zero entries with empty meanings array.
- `test_t2_06_missing_headword_brackets_detection`: Explicit verification for Unit 4 headword 'brackets'.
- `test_t2_07_corrupt_tokens_detection`: Universal scan for corrupted tokens and slang.
- `test_t2_08_hyphenated_prefix_words_filtering`: Filter verification for `-ish`, `-shaped`, prefix-hyphens.
- `test_t2_09_duplicate_xml_headword_nodes_consistency`: Consistency across 6 duplicate headwords.
- `test_t2_10_phrase_and_idiom_headwords_presence`: 400+ multi-word expressions and idioms presence.
- `test_t2_11_definition_length_boundaries`: Length guards (5 to 500 characters).
- `test_t2_12_key_whitespace_and_case_exact_match`: Clean whitespace and exact case keys.
- **`test_t2_13_ipa_character_set_whitelist`**: Strict validation against British IPA character whitelist.
- **`test_t2_14_reject_bracketed_allophones`**: Universal rejection of narrow square-bracketed `[...]` transcriptions.
- **`test_t2_15_reject_raw_sampa_tokens`**: Universal rejection of unconverted SAMPA characters (`%&QVUITAODSZ23@ÍÙ`).
- **`test_t2_16_reject_ascii_colons`**: Universal rejection of ASCII `:` in favor of Unicode length mark `ː`.
- **`test_t2_17_reject_americanisms`**: Universal rejection of General American rhotic schwa (`ɚ`, `ɝ`) and flap (`ɾ`).
- **`test_t2_18_reject_trailing_and_double_slashes`**: Universal rejection of trailing slash bugs (`//`).

---

### Tier 3: Cross-Feature Combinations (`tests/test_tier3_combinations.py`)
- `test_t3_01_word_to_unit_cross_referencing`: Bidirectional XML-to-Unit cross-referencing.
- `test_t3_02_module_word_count_aggregation`: Module word count equals sum of unit word counts.
- `test_t3_03_section_to_unit_hierarchy_integrity`: 148 sections strictly partitioned across 80 units.
- `test_t3_04_intra_unit_distractor_collisions_across_all_80_units`: Zero definition collisions in any unit.
- `test_t3_05_intra_unit_synonym_matching_exclusivity`: Synonym matching pair exclusivity.
- `test_t3_06_persistence_key_stability_and_determinism`: Deterministic UserDefaults keys.
- `test_t3_07_multi_unit_word_definition_consistency`: Consistent definitions across units.
- `test_t3_08_progress_calculation_invariants`: Boundary invariants (0.0 to 1.0 progress).
- `test_t3_09_search_filter_cross_referencing`: Substring search filtering across words and definitions.
- `test_t3_10_module_unit_span_contiguous`: Contiguous unit ranges per module.
- **`test_t3_11_content_parser_fallback_xml_and_definitions`**: Validates fallback priority between XML and `definitions.json`.
- **`test_t3_12_speech_text_pronunciation_cleaning_interaction`**: Validates alignment between `cleanWord`, `speechText`, and `ipa`.
- **`test_t3_13_quiz_distractor_matching_with_ipa`**: Validates that quiz questions and options retain distinct phonetic identities.
- **`test_t3_14_ipa_and_audio_alignment`**: Validates audio availability flags against IPA pronunciation presence.

---

### Tier 4: Real-World Workloads (`tests/test_tier4_scenarios.py`)
- `test_t4_01_word_to_definition_quiz_simulation_all_80_units`: 15-question quiz generation across all 80 units.
- `test_t4_02_definition_to_word_quiz_simulation_all_80_units`: Reverse quiz generation across all 80 units.
- `test_t4_03_matching_game_simulation`: Synonym matching game across eligible units.
- `test_t4_04_listening_and_spelling_simulation`: Fill-in-the-blank listening exercises with hints.
- `test_t4_05_flashcard_deck_and_learned_progress_simulation`: Card flips, example reveals, and progress state transitions.
- `test_t4_06_curriculum_search_and_navigation_traversal`: Navigation tree traversal and search query resolution.
- `test_t4_07_five_exercise_modes_session_simulation`: Comprehensive 5-mode workout session.
- `test_t4_08_progress_persistence_lifecycle`: Mark learned, reset unit, reset all lifecycle.
- **`test_t4_09_full_curriculum_ipa_audit_all_80_units`**: 100% full-curriculum audit of all 80 units, 12 modules, and 2,781 runtime words for valid British RP IPA.
- **`test_t4_10_flashcard_study_session_ipa_rendering`**: End-to-end Flashcard rendering simulation verifying clean phonetic presentation.
- **`test_t4_11_exercise_container_pronunciation_fidelity`**: Active exercise execution ensuring uninterrupted pronunciation access.

---

### Native Swift Engine Pipeline Harness (`tests/test_engine_pipeline.swift`)
- Section 1: Resource file accessibility.
- Section 2: JSON decoding into `[String: WordDetail]` Swift Codable models; **`WordDetail.phonetic` presence and slash format**.
- Section 3: `ContentParser.parseSettings` (13 modules, 80 contiguous units, 148 sections).
- Section 4: `ContentParser.parseWordList` (2,781 words, `sampaToIPA` conversion precision, non-empty `/.../` IPA).
- Section 5: `ContentParser.buildModules` full pipeline execution; **100% runtime words across all built units have non-empty `/.../` IPA and zero forbidden SAMPA characters**.
- Section 6: Definition completeness across all populated words.
- Section 7: Persistence key uniqueness across all parsed words.
- Section 8: Word normalization computed properties (`cleanWord`, `parentheticalGloss`, `speechText`, `acceptedSpellings`).

---

## 4. Test Execution & Automation Commands

### Master Automated Test Runner (All 5 Phases)
```bash
./run_e2e_tests.sh
```

### Python 4-Tier Test Suite
```bash
# Run all 4 tiers with JSON reporting
python3 tests/run_all_tests.py --json-out tests/test_results.json

# Run individual tiers
python3 tests/run_all_tests.py --tier 1
python3 tests/run_all_tests.py --tier 2
python3 tests/run_all_tests.py --tier 3
python3 tests/run_all_tests.py --tier 4
```

### Native Swift Engine Pipeline Harness
```bash
swiftc -parse-as-library Models/DataModels.swift Utilities/ContentParser.swift tests/test_engine_pipeline.swift -o /tmp/test_pipeline && /tmp/test_pipeline
```

### Swift Stress Test Suites
```bash
# Headword normalization & speechText stress test
swiftc -parse-as-library Models/DataModels.swift Utilities/ContentParser.swift tests/stress_test_headwords.swift -o /tmp/stress_headwords && /tmp/stress_headwords

# Quiz matching & distractor simulation (10,000 questions)
swiftc -parse-as-library Models/DataModels.swift Utilities/ContentParser.swift tests/stress_test_quiz_matching.swift -o /tmp/stress_quiz && /tmp/stress_quiz
```

### macOS Application Compilation Verification
```bash
xcodebuild build -scheme OxfordWordSkills -destination 'platform=macOS' -derivedDataPath /tmp/DerivedData -quiet
```
