#!/usr/bin/env bash
set -eo pipefail

# =============================================================================
# Oxford Word Skills — Master End-to-End Test Suite Runner
# =============================================================================

BOLD="\033[1m"
GREEN="\033[92m"
RED="\033[91m"
YELLOW="\033[93m"
CYAN="\033[96m"
RESET="\033[0m"

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

echo -e "\n${BOLD}${CYAN}=======================================================${RESET}"
echo -e "${BOLD}${CYAN}   Oxford Word Skills — Master E2E Validation Suite    ${RESET}"
echo -e "${BOLD}${CYAN}=======================================================${RESET}\n"

FAILURES=0

# 1. Run Python Comprehensive 4-Tier Test Suite
echo -e "${BOLD}>>> Step 1/4: Executing Python 4-Tier Test Suite...${RESET}\n"
if python3 tests/run_all_tests.py --json-out tests/test_results.json; then
    echo -e "\n${GREEN}✓ Step 1 Passed: All 4 Test Tiers executed successfully.${RESET}\n"
else
    echo -e "\n${RED}✗ Step 1 Failed: Content/engine violations detected in Python test suite.${RESET}\n"
    FAILURES=$((FAILURES + 1))
fi

# 2. Run Native Swift Engine Pipeline Test
echo -e "${BOLD}>>> Step 2/4: Executing Native Swift Engine Pipeline Test...${RESET}\n"
if swift Models/DataModels.swift Utilities/ContentParser.swift tests/test_engine_pipeline.swift; then
    echo -e "\n${GREEN}✓ Step 2 Passed: Native Swift pipeline parsing & model decoding succeeded.${RESET}\n"
else
    echo -e "\n${RED}✗ Step 2 Failed: Swift ContentParser / WordDetail pipeline failed.${RESET}\n"
    FAILURES=$((FAILURES + 1))
fi

# 3. Run UpdateService Unit Tests
echo -e "${BOLD}>>> Step 3/5: Executing UpdateService Unit Tests...${RESET}\n"
if swift tests/test_update_service.swift; then
    echo -e "\n${GREEN}✓ Step 3 Passed: UpdateService version comparison & JSON parsing tests passed.${RESET}\n"
else
    echo -e "\n${RED}✗ Step 3 Failed: UpdateService unit tests failed.${RESET}\n"
    FAILURES=$((FAILURES + 1))
fi

# 4. Run SpeechService & VoiceOption Unit Tests
echo -e "${BOLD}>>> Step 4/5: Executing SpeechService Unit Tests...${RESET}\n"
if swift Utilities/SpeechService.swift tests/test_speech_service.swift; then
    echo -e "\n${GREEN}✓ Step 4 Passed: SpeechService & VoiceOption unit tests passed.${RESET}\n"
else
    echo -e "\n${RED}✗ Step 4 Failed: SpeechService unit tests failed.${RESET}\n"
    FAILURES=$((FAILURES + 1))
fi

# 5. Run Xcode Project Compilation Check
echo -e "${BOLD}>>> Step 5/5: Executing Xcode Build Verification...${RESET}\n"
if xcodebuild build -scheme OxfordWordSkills -destination 'platform=macOS' -derivedDataPath /tmp/DerivedData -quiet; then
    echo -e "${GREEN}✓ Step 5 Passed: Xcode project compiled cleanly.${RESET}\n"
else
    echo -e "${RED}✗ Step 5 Failed: Xcode compilation failed.${RESET}\n"
    FAILURES=$((FAILURES + 1))
fi

# Summary
echo -e "${BOLD}=======================================================${RESET}"
if [ $FAILURES -eq 0 ]; then
    echo -e "${BOLD}${GREEN}  >>> ALL 5 VALIDATION PHASES PASSED (Exit Code: 0) <<<${RESET}"
    echo -e "${BOLD}=======================================================\n"
    exit 0
else
    echo -e "${BOLD}${RED}  >>> $FAILURES / 5 VALIDATION PHASES FAILED (Exit Code: 1) <<<${RESET}"
    echo -e "${BOLD}=======================================================\n"
    exit 1
fi
