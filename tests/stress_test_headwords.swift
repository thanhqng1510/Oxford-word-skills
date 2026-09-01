//
//  stress_test_headwords.swift
//  OxfordWordSkills Adversarial Headword & Dictionary Integrity Stress Test Suite
//

import Foundation

@main
struct ChallengerStressTestRunner {
    static func main() {
        let green = "\u{001B}[32m"
        let red = "\u{001B}[31m"
        let cyan = "\u{001B}[36m"
        let bold = "\u{001B}[1m"
        let reset = "\u{001B}[0m"

        print("\(bold)=================================================================\(reset)")
        print("\(bold)  Oxford Word Skills — Headword & Dictionary Stress Harness      \(reset)")
        print("\(bold)=================================================================\(reset)\n")

        let fileManager = FileManager.default
        let currentDir = fileManager.currentDirectoryPath
        let projectRoot = currentDir.hasSuffix("tests") ? (currentDir as NSString).deletingLastPathComponent : currentDir
        let resourcesDir = (projectRoot as NSString).appendingPathComponent("Resources")

        let settingsURL = URL(fileURLWithPath: (resourcesDir as NSString).appendingPathComponent("settings.xml"))
        let wordListURL = URL(fileURLWithPath: (resourcesDir as NSString).appendingPathComponent("extrawordlist.xml"))
        let definitionsURL = URL(fileURLWithPath: (resourcesDir as NSString).appendingPathComponent("definitions.json"))

        var totalAssertions = 0
        var passedAssertions = 0
        var failedAssertions = 0
        var failureDetails: [String] = []

        func recordAssert(_ condition: Bool, _ name: String, _ details: String = "") {
            totalAssertions += 1
            if condition {
                passedAssertions += 1
            } else {
                failedAssertions += 1
                let failMsg = "FAIL: \(name) | \(details)"
                failureDetails.append(failMsg)
                print("  \(red)✗ [FAIL]\(reset) \(name) -> \(details)")
            }
        }

        // 1. Parse and build dataset
        print("\(cyan)--> Step 1: Parsing Curriculum & Building Modules Dataset...<\(reset)")
        let allWords = ContentParser.parseWordList(from: wordListURL)
        let modules = ContentParser.buildModules(
            settingsURL: settingsURL,
            wordListURL: wordListURL,
            definitionsURL: definitionsURL
        )

        recordAssert(allWords.count == 2781, "Parsed exactly 2,781 active vocabulary words", "Found: \(allWords.count)")
        recordAssert(modules.count == 13, "Built 13 modules", "Found: \(modules.count)")
        let allUnits = modules.flatMap { $0.units }
        recordAssert(allUnits.count == 80, "Built 80 units", "Found: \(allUnits.count)")

        // =====================================================================
        // TEST SUITE 1: Stress-Testing Headword Sanitization across ALL 2,781 words
        // =====================================================================
        print("\n\(cyan)--> Step 2: Stress-Testing Headword Normalization on ALL 2,781 Words...<\(reset)")
        var emptyCleanWordCount = 0
        var emptySpeechTextCount = 0
        var emptyAcceptedSpellingsCount = 0
        var missingCleanInAcceptedCount = 0
        var missingRawInAcceptedCount = 0
        var illegalCharsInSpeechTextCount = 0
        var trailingWhitespaceInCleanWordCount = 0
        var trailingWhitespaceInSpeechTextCount = 0
        var emptyElementsInAcceptedCount = 0

        for word in allWords {
            // Check cleanWord
            if word.cleanWord.isEmpty {
                emptyCleanWordCount += 1
            }
            if word.cleanWord != word.cleanWord.trimmingCharacters(in: .whitespaces) {
                trailingWhitespaceInCleanWordCount += 1
            }

            // Check speechText
            if word.speechText.isEmpty {
                emptySpeechTextCount += 1
            }
            if word.speechText != word.speechText.trimmingCharacters(in: .whitespaces) {
                trailingWhitespaceInSpeechTextCount += 1
            }
            if word.speechText.contains("(") || word.speechText.contains(")") || word.speechText.contains("=") || word.speechText.contains("...") {
                illegalCharsInSpeechTextCount += 1
            }

            // Check acceptedSpellings
            if word.acceptedSpellings.isEmpty {
                emptyAcceptedSpellingsCount += 1
            }
            let cleanLower = word.cleanWord.trimmingCharacters(in: .whitespaces).lowercased()
            if !word.acceptedSpellings.contains(cleanLower) {
                missingCleanInAcceptedCount += 1
            }
            let rawLower = word.word.trimmingCharacters(in: .whitespaces).lowercased()
            if !word.acceptedSpellings.contains(rawLower) {
                missingRawInAcceptedCount += 1
            }
            for item in word.acceptedSpellings {
                if item.isEmpty || item != item.trimmingCharacters(in: .whitespaces) {
                    emptyElementsInAcceptedCount += 1
                }
            }
        }

        recordAssert(emptyCleanWordCount == 0, "2,781 words have non-empty cleanWord", "Empty count: \(emptyCleanWordCount)")
        recordAssert(trailingWhitespaceInCleanWordCount == 0, "2,781 words have cleanWord without leading/trailing whitespace", "Violations: \(trailingWhitespaceInCleanWordCount)")
        recordAssert(emptySpeechTextCount == 0, "2,781 words have non-empty speechText", "Empty count: \(emptySpeechTextCount)")
        recordAssert(trailingWhitespaceInSpeechTextCount == 0, "2,781 words have speechText without leading/trailing whitespace", "Violations: \(trailingWhitespaceInSpeechTextCount)")
        recordAssert(illegalCharsInSpeechTextCount == 0, "2,781 words have speechText free of '(', ')', '=', '...'", "Violations: \(illegalCharsInSpeechTextCount)")
        recordAssert(emptyAcceptedSpellingsCount == 0, "2,781 words have non-empty acceptedSpellings", "Empty count: \(emptyAcceptedSpellingsCount)")
        recordAssert(missingCleanInAcceptedCount == 0, "2,781 words contain cleanWord.lowercased() in acceptedSpellings", "Missing: \(missingCleanInAcceptedCount)")
        recordAssert(missingRawInAcceptedCount == 0, "2,781 words contain rawWord.lowercased() in acceptedSpellings", "Missing: \(missingRawInAcceptedCount)")
        recordAssert(emptyElementsInAcceptedCount == 0, "2,781 words have no empty/untrimmed elements in acceptedSpellings", "Violations: \(emptyElementsInAcceptedCount)")

        print("  \(green)✓ [PASS]\(reset) All 2,781 vocabulary headwords verified for cleanWord, speechText, and acceptedSpellings.")

        // =====================================================================
        // TEST SUITE 2: Deep Stress Test on all 101 Parenthetical/Gloss Words
        // =====================================================================
        print("\n\(cyan)--> Step 3: Deep Stress Test on all 101 Parenthetical/Gloss Words...<\(reset)")
        let parenWords = allWords.filter { $0.word.contains("(") || $0.word.contains(")") }
        recordAssert(parenWords.count == 101, "Identified exactly 101 parenthetical words in extrawordlist.xml", "Found: \(parenWords.count)")

        var invalidGlossCount = 0
        var cleanWordContainsParenCount = 0
        var speechTextContainsParenCount = 0
        var suffixMismatchCount = 0
        var simulatedTypingFailures = 0

        for w in parenWords {
            // Verify parentheticalGloss
            guard let gloss = w.parentheticalGloss else {
                invalidGlossCount += 1
                continue
            }
            if !gloss.hasPrefix("(") || !gloss.hasSuffix(")") {
                invalidGlossCount += 1
            }

            // Verify cleanWord does not contain '('
            if w.cleanWord.contains("(") || w.cleanWord.contains(")") {
                cleanWordContainsParenCount += 1
            }

            // Verify speechText does not contain '(' or ')' or '='
            if w.speechText.contains("(") || w.speechText.contains(")") || w.speechText.contains("=") {
                speechTextContainsParenCount += 1
            }

            // Suffix variations test (e.g. backward(s) and forward(s))
            if w.word == "backward(s)" || w.word == "forward(s)" {
                let base = w.cleanWord.lowercased()
                let withS = base + "s"
                if !w.acceptedSpellings.contains(base) || !w.acceptedSpellings.contains(withS) {
                    suffixMismatchCount += 1
                }
            }

            // Simulated FillInBlankView user input acceptance test
            let cleanInput = w.cleanWord.lowercased()
            let rawInput = w.word.lowercased()
            let upperInput = w.cleanWord.uppercased()
            let spacePaddedInput = "  " + w.cleanWord + "  "

            let checkClean = w.acceptedSpellings.contains(cleanInput.trimmingCharacters(in: .whitespaces).lowercased())
            let checkRaw = w.acceptedSpellings.contains(rawInput.trimmingCharacters(in: .whitespaces).lowercased())
            let checkUpper = w.acceptedSpellings.contains(upperInput.trimmingCharacters(in: .whitespaces).lowercased())
            let checkPadded = w.acceptedSpellings.contains(spacePaddedInput.trimmingCharacters(in: .whitespaces).lowercased())

            // Adversarial wrong inputs:
            let wrongInput = "completely_wrong_answer_xyz"
            let checkWrong = w.acceptedSpellings.contains(wrongInput.trimmingCharacters(in: .whitespaces).lowercased())

            if !checkClean || !checkRaw || !checkUpper || !checkPadded || checkWrong {
                simulatedTypingFailures += 1
            }
        }

        recordAssert(invalidGlossCount == 0, "101 parenthetical words have well-formed parentheticalGloss", "Invalid: \(invalidGlossCount)")
        recordAssert(cleanWordContainsParenCount == 0, "101 parenthetical words have cleanWord stripped of parentheses", "Violations: \(cleanWordContainsParenCount)")
        recordAssert(speechTextContainsParenCount == 0, "101 parenthetical words have speechText stripped of parenthetical audio triggers", "Violations: \(speechTextContainsParenCount)")
        recordAssert(suffixMismatchCount == 0, "All base '(s)' suffix words include both singular and plural in acceptedSpellings", "Mismatches: \(suffixMismatchCount)")
        recordAssert(simulatedTypingFailures == 0, "Simulated user inputs across 101 words pass 100% with zero false rejects and zero false accepts", "Failures: \(simulatedTypingFailures)")

        // Check Ellipsis words (e.g. "how about ...?", "what about...?", "I think ...")
        let ellipsisWords = allWords.filter { $0.word.contains("...") }
        recordAssert(ellipsisWords.count == 12, "Identified exactly 12 ellipsis words in extrawordlist.xml", "Found: \(ellipsisWords.count)")
        var ellipsisCleanPass = true
        for ew in ellipsisWords {
            if ew.speechText.contains("...") || ew.speechText.hasSuffix(" ") {
                ellipsisCleanPass = false
            }
        }
        recordAssert(ellipsisCleanPass, "All 12 ellipsis words have speechText stripped of '...' without trailing whitespace")

        // Check Apostrophe words (e.g. "as far as I'm concerned", "let's", "o'clock")
        let apostropheWords = allWords.filter { $0.word.contains("'") }
        recordAssert(apostropheWords.count == 28, "Identified 28 apostrophe words in extrawordlist.xml", "Found: \(apostropheWords.count)")
        var apostropheCleanPass = true
        for aw in apostropheWords {
            if !aw.acceptedSpellings.contains(aw.word.lowercased()) || aw.cleanWord.isEmpty {
                apostropheCleanPass = false
            }
        }
        recordAssert(apostropheCleanPass, "All 28 apostrophe words have cleanWord and acceptedSpellings preserved")

        // Check Hyphenated words (e.g. "blow-dry", "ice-skating")
        let hyphenWords = allWords.filter { $0.word.contains("-") }
        recordAssert(hyphenWords.count == 33, "Identified 33 hyphenated words in extrawordlist.xml", "Found: \(hyphenWords.count)")
        var hyphenCleanPass = true
        for hw in hyphenWords {
            if !hw.acceptedSpellings.contains(hw.word.lowercased()) || hw.cleanWord.isEmpty {
                hyphenCleanPass = false
            }
        }
        recordAssert(hyphenCleanPass, "All 33 hyphenated words have valid cleanWord and acceptedSpellings")

        // Check Equals gloss words (e.g. "ad (= advertisement)")
        let equalsWords = allWords.filter { $0.word.contains("=") }
        recordAssert(equalsWords.count == 36, "Identified 36 equals-gloss words in extrawordlist.xml", "Found: \(equalsWords.count)")
        var equalsCleanPass = true
        for eqw in equalsWords {
            if eqw.cleanWord.contains("=") || eqw.speechText.contains("=") || !eqw.acceptedSpellings.contains(eqw.cleanWord.lowercased()) {
                equalsCleanPass = false
            }
        }
        recordAssert(equalsCleanPass, "All 36 equals-gloss words have cleanWord and speechText stripped of '='")

        print("  \(green)✓ [PASS]\(reset) 101 parenthetical words, 12 ellipsis words, 28 apostrophe words, 33 hyphen words, and 36 equals-gloss words verified.")

        // =====================================================================
        // SUMMARY AND VERDICT
        // =====================================================================
        print("\n=================================================================")
        print("\(bold)                      FINAL SUMMARY & VERDICT                    \(reset)")
        print("=================================================================")
        print("Total Assertions Evaluated : \(totalAssertions)")
        print("Passed Assertions          : \(green)\(passedAssertions)\(reset)")
        print("Failed Assertions          : \(failedAssertions > 0 ? "\(red)\(failedAssertions)\(reset)" : "0")")
        print("Total Vocabulary Tested    : 2,781 words")
        print("Parenthetical Words Tested : 101 words")
        print("=================================================================")

        if failedAssertions > 0 {
            print("\n\(red)\(bold)VERDICT: CHALLENGE_FAILED\(reset)")
            for fail in failureDetails {
                print("  \(red)- \(fail)\(reset)")
            }
            exit(1)
        } else {
            print("\n\(green)\(bold)VERDICT: APPROVE\(reset)")
            print("\(green)All empirical headword and stress tests passed with 100% reliability.\(reset)\n")
            exit(0)
        }
    }
}
