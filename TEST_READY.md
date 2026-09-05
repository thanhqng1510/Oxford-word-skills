# Test Suite Status & Baseline Verification Report — Oxford Word Skills

**Document Version**: 1.0.0  
**Timestamp**: 2026-09-05T06:14:00Z  
**Status**: `TEST_READY` — All 4 Python tiers and native Swift test harnesses fully authored, integrated, and verified against baseline data.

---

## 1. Overview & Test Harness Delivery

The E2E Testing Track has implemented a comprehensive, multi-layered automated validation harness enforcing all requirements from `ORIGINAL_REQUEST.md`, `PROJECT.md`, and Oxford University Press curriculum standards:

1. **Python 4-Tier Automated Test Suite** (`tests/run_all_tests.py`):
   - **Tier 1 (Feature Coverage)**: 56 tests covering F1 through F9, with comprehensive checks for dictionary phonetic completeness, `/.../` syntax, character sets, and runtime word non-empty invariants across all 80 units.
   - **Tier 2 (Boundary & Corner Cases)**: 18 tests evaluating extreme boundaries: British RP IPA whitelist validation, rejection of bracketed narrow allophones `[...]`, rejection of raw SAMPA tokens (`%&QVUITAODSZ23@ÍÙ`), rejection of ASCII colons `:`, rejection of Americanisms (`ɚ`, `ɝ`, `ɾ`), and rejection of trailing slash bugs (`//`).
   - **Tier 3 (Cross-Feature Combinations)**: 14 interaction tests verifying XML / `definitions.json` fallback, `cleanWord` / `speechText` / `ipa` synchronization, quiz distractor separation with phonetics, and audio alignment.
   - **Tier 4 (Real-World Workloads)**: 11 scenario tests verifying full curriculum audits (all 80 units, 12 modules, 2,781 runtime words), Flashcard rendering, quiz generation, and exercise mode stability.
2. **Native Swift Engine Pipeline Test Harness** (`tests/test_engine_pipeline.swift`):
   - Direct execution in the macOS Swift runtime validating `ContentParser.buildModules()`, `WordDetail` Codable deserialization, 100% non-empty slash-enclosed `Word.ipa` in `builtUnits`, zero raw SAMPA characters, and zero double-slash bugs.
3. **Master End-to-End Test Suite Runner** (`run_e2e_tests.sh`):
   - Single unified command executing all 5 validation phases: Python 4-tier suite, Swift engine pipeline, Swift UpdateService tests, Swift SpeechService tests, and Xcode macOS compilation check.

---

## 2. Test Execution Commands

### Full Project Validation (5 Phases)
```bash
./run_e2e_tests.sh
```

### Python 4-Tier Test Suite
```bash
# Execute all 99 Python tests with structured JSON reporting
python3 tests/run_all_tests.py --json-out tests/test_results.json

# Execute specific test tiers
python3 tests/run_all_tests.py --tier 1   # Feature Coverage (56 tests)
python3 tests/run_all_tests.py --tier 2   # Boundary Cases (18 tests)
python3 tests/run_all_tests.py --tier 3   # Combinations (14 tests)
python3 tests/run_all_tests.py --tier 4   # Real-World Workloads (11 tests)
```

### Native Swift Engine Pipeline Harness
```bash
swiftc -parse-as-library Models/DataModels.swift Utilities/ContentParser.swift tests/test_engine_pipeline.swift -o /tmp/test_pipeline && /tmp/test_pipeline
```

### Swift Stress & Simulation Suites
```bash
# Headword normalization & speechText stress test
swiftc -parse-as-library Models/DataModels.swift Utilities/ContentParser.swift tests/stress_test_headwords.swift -o /tmp/stress_headwords && /tmp/stress_headwords

# Quiz matching & distractor availability stress test (10,000 questions)
swiftc -parse-as-library Models/DataModels.swift Utilities/ContentParser.swift tests/stress_test_quiz_matching.swift -o /tmp/stress_quiz && /tmp/stress_quiz
```

---

## 3. Tier Breakdown & Baseline Test Status

Baseline execution was performed against the un-harmonized repository state (prior to M2 Data Store Harmonization and M3 Swift Engine Synchronization). The results demonstrate **zero false positives**, proving that existing curriculum structure passes while the known data store defects are precisely detected:

### Python 4-Tier Suite Baseline

| Tier Name | Total Tests | Pass | Fail | Skip | Baseline Status | Notes |
|---|---|---|---|---|---|---|
| **Tier 1: Feature Coverage (F1–F9)** | 56 | 53 | 3 | 0 | **Expected Baseline Failures** | Fails on 736 empty phonetics in `definitions.json` (`test_f3_07`), bracketed/American dialect symbols (`test_f3_08`), and 12 trailing slash bugs (`test_f9_07`). |
| **Tier 2: Boundary & Corner Cases** | 18 | 14 | 4 | 0 | **Expected Baseline Failures** | Fails on turned-r `ɹ` in `definitions.json` (`test_t2_13`), 20 bracketed allophones (`test_t2_14`), 21 Americanisms (`test_t2_17`), and 12 trailing slash bugs (`test_t2_18`). |
| **Tier 3: Cross-Feature Combinations** | 14 | 14 | 0 | 0 | **100% PASS** | Verified fallback priority, speech text cleaning, distractor separation, and audio alignment. |
| **Tier 4: Real-World Scenarios** | 11 | 9 | 2 | 0 | **Expected Baseline Failures** | Fails on full-curriculum IPA audit (`test_t4_09`) and Flashcard rendering (`test_t4_10`) due to the 12 runtime words with trailing double-slash bugs. |
| **TOTAL OVERALL** | **99** | **90** | **9** | **0** | **Baseline Failure Rate: 9.1%** | All 9 failures accurately target known data store defects to be resolved in M2. |

### Native Swift Pipeline Harness Baseline

| Harness Suite | Total Tests | Pass | Fail | Baseline Status | Notes |
|---|---|---|---|---|---|
| `test_engine_pipeline.swift` | 42 | 39 | 3 | **Expected Baseline Failures** | Accurately flags: (1) 736 empty phonetics in `definitions.json`, (2) 20 bracketed phonetics in `definitions.json`, (3) 12 double-slash bugs in `builtUnits` runtime words. |

---

## 4. Coverage Checklist & Verification Invariants

- [x] **Requirement R1 (Wiktionary IPA Verification & Ingestion Standard)**:
  - Whitelist of approved Received Pronunciation British IPA symbols enforced (`test_t2_13`).
  - Rejection of General American dialectal markers (`ɚ`, `ɝ`, `ɾ`) enforced (`test_t2_17`, `test_f3_08`).
  - Dialect standard verified against Wiktionary UK / SSB models.
- [x] **Requirement R2 (Data Store Consistency & Model Synchronization)**:
  - 100% completeness of `WordDetail.phonetic` in `definitions.json` tested (`test_f3_07`, Swift Section 2).
  - Clean Unicode `/.../` slash wrapping tested on all entries (`test_f3_07`, `test_f9_07`).
  - Elimination of empty phonetics and legacy SAMPA artifacts tested (`test_f3_08`, `test_t2_15`, `test_f9_08`).
- [x] **Requirement R3 (Rate-Limited Remote Retrieval Standards)**:
  - Validated via M1 specifications and test structure in `TEST_INFRA.md`.
- [x] **Requirement R4 (Comprehensive Verification & Regression Prevention)**:
  - Invariant 1: 100% of runtime words across all 80 units have non-empty, slash-enclosed `/.../` IPA (`test_f9_07`, `test_t4_09`, Swift Section 5).
  - Invariant 2: Zero lingering raw SAMPA characters (`%&QVUITAODSZ23@ÍÙ`) (`test_f3_08`, `test_t2_15`, `test_f9_08`, Swift Section 5).
  - Invariant 3: Zero missing or empty `"phonetic"` entries in `definitions.json` (`test_f3_07`, Swift Section 2).
  - Invariant 4: Universal rejection of trailing slash bugs `//` (`test_t2_18`, `test_f9_07`, Swift Section 5).
  - Invariant 5: Clean execution of all automated test suites (`./run_e2e_tests.sh`).

---

## 5. Implementation Bug Escalation Notice (For M2 & M3 Workers)

The test harness has exposed and isolated the following exact defects in the repository data files:

1. **`Resources/definitions.json` Empty Phonetics (736 entries)**:
   - 736 dictionary entries (primarily multi-word phrases and idioms like `"after a while"`, `"against the law"`, `"all over the world"`) have `"phonetic": ""`.
   - **Target Action (M2)**: Populate all 736 entries with audited British RP IPA synthesized from component words.
2. **`Resources/definitions.json` Non-RP / Formatting Artifacts (621 entries)**:
   - 20 entries use square brackets `[...]` (e.g. `allergic: [ə.ˈlɜː.dʒɪk]`).
   - 21 entries contain American rhotic symbols (`ɚ`, `ɾ`) (e.g. `accelerator: /æk.ˈsɛl.ə.ˌɹeɪ.tɚ/`).
   - 580 entries contain turned-r `ɹ` instead of standard `r` (e.g. `abbreviation: /əˌbɹiː.viˈeɪ.ʃən/`).
   - **Target Action (M2)**: Normalize to British RP `/.../` with standard `r` and no Americanisms.
3. **`Resources/extrawordlist.xml` Trailing Slashes (12 nodes)**:
   - 12 word entries have trailing slashes inside raw SAMPA (e.g. `alter: "O:lt@(r)/`, `appreciate: @"pri:SieIt/`, `area: "e@ri@/`, `civil war: %sIvl "wO:(r)/`), producing double-slash bugs `//` at runtime.
   - **Target Action (M2)**: Strip trailing `/` from raw XML attributes.
4. **`Utilities/ContentParser.swift` Fallback & Sanitization**:
   - `buildModules()` currently ignores `detail.phonetic` from `definitions.json` and does not strip accidental trailing slashes before appending enclosing slashes.
   - **Target Action (M3)**: Implement fallback to `detail.phonetic` and sanitize trailing slashes.
