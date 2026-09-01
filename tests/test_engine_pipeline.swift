//
//  test_engine_pipeline.swift
//  OxfordWordSkills E2E Native Swift Engine Pipeline Test Harness
//

import Foundation

@main
struct PipelineTestRunner {
    static func main() {
        // ANSI colors for CLI output
        let green = "\u{001B}[32m"
        let red = "\u{001B}[31m"
        let yellow = "\u{001B}[33m"
        let bold = "\u{001B}[1m"
        let reset = "\u{001B}[0m"

        print("\(bold)=== Oxford Word Skills Native Swift Pipeline Test Runner ===\(reset)\n")

        // Locate project root and resources
        let fileManager = FileManager.default
        let currentDir = fileManager.currentDirectoryPath
        let projectRoot = currentDir.hasSuffix("tests") ? (currentDir as NSString).deletingLastPathComponent : currentDir
        let resourcesDir = (projectRoot as NSString).appendingPathComponent("Resources")

        let settingsURL = URL(fileURLWithPath: (resourcesDir as NSString).appendingPathComponent("settings.xml"))
        let wordListURL = URL(fileURLWithPath: (resourcesDir as NSString).appendingPathComponent("extrawordlist.xml"))
        let definitionsURL = URL(fileURLWithPath: (resourcesDir as NSString).appendingPathComponent("definitions.json"))

        var failureCount = 0
        var passCount = 0

        func assertTest(_ condition: Bool, _ name: String, _ details: String = "") {
            if condition {
                passCount += 1
                print("  \(green)✓ [PASS]\(reset) \(name)")
            } else {
                failureCount += 1
                print("  \(red)✗ [FAIL]\(reset) \(name)")
                if !details.isEmpty {
                    print("        \(yellow)Details: \(details)\(reset)")
                }
            }
        }

        // 1. Verify resource files exist
        assertTest(fileManager.fileExists(atPath: settingsURL.path), "settings.xml exists", settingsURL.path)
        assertTest(fileManager.fileExists(atPath: wordListURL.path), "extrawordlist.xml exists", wordListURL.path)
        assertTest(fileManager.fileExists(atPath: definitionsURL.path), "definitions.json exists", definitionsURL.path)

        // 2. Test JSON Decoder directly against WordDetail model
        print("\n--- JSON Decoding & Model Schema Tests ---")
        do {
            let defData = try Data(contentsOf: definitionsURL)
            let decoded = try JSONDecoder().decode([String: WordDetail].self, from: defData)
            assertTest(decoded.count > 2700, "definitions.json decoded into [String: WordDetail]", "Count: \(decoded.count)")
            
            var populatedMeaningsCount = 0
            var emptyDefCount = 0
            for (_, detail) in decoded {
                if !detail.meanings.isEmpty {
                    populatedMeaningsCount += 1
                }
                for meaning in detail.meanings {
                    if meaning.definitions.isEmpty {
                        emptyDefCount += 1
                    }
                }
            }
            assertTest(populatedMeaningsCount >= 1500, "At least 1,500 words have populated dictionary meanings", "Found \(populatedMeaningsCount)")
            assertTest(emptyDefCount == 0, "Zero meanings with empty definitions: []", "Found \(emptyDefCount) empty definitions")
        } catch {
            assertTest(false, "definitions.json JSONDecoder decoding", "Error: \(error)")
        }

        // 3. Test ContentParser.parseSettings
        print("\n--- XML Parser & Curriculum Tests ---")
        let settingsModules = ContentParser.parseSettings(from: settingsURL)
        assertTest(settingsModules.count == 13, "ContentParser.parseSettings parsed 13 modules", "Found \(settingsModules.count)")

        let allUnits = settingsModules.flatMap { $0.units }
        assertTest(allUnits.count == 80, "ContentParser.parseSettings parsed 80 units", "Found \(allUnits.count)")

        let unitNumbers = allUnits.map { $0.number }
        let expectedNumbers = Array(1...80)
        assertTest(unitNumbers == expectedNumbers, "Unit numbers are strictly contiguous 1..80", "First 5: \(unitNumbers.prefix(5))")

        let totalSections = allUnits.flatMap { $0.sections }.count
        assertTest(totalSections == 148, "Total sections parsed == 148", "Found \(totalSections)")

        // 4. Test ContentParser.parseWordList & IPA Conversion
        print("\n--- Word List Parser & IPA Conversion Tests ---")
        let parsedWords = ContentParser.parseWordList(from: wordListURL)
        assertTest(parsedWords.count == 2781, "ContentParser.parseWordList parsed exactly 2,781 valid words", "Found \(parsedWords.count)")

        // Test sampaToIPA converter precision
        assertTest(ContentParser.sampaToIPA("@%bri:vi\"eISn") == "/əˌbriːviˈeɪʃn/", "sampaToIPA converts abbreviation to /əˌbriːviˈeɪʃn/", ContentParser.sampaToIPA("@%bri:vi\"eISn"))
        assertTest(ContentParser.sampaToIPA("\"&bs@lu:tli") == "/ˈæbsəluːtli/", "sampaToIPA converts absolutely to /ˈæbsəluːtli/", ContentParser.sampaToIPA("\"&bs@lu:tli"))
        assertTest(ContentParser.sampaToIPA("@\"kju:z") == "/əˈkjuːz/", "sampaToIPA converts accuse to /əˈkjuːz/", ContentParser.sampaToIPA("@\"kju:z"))
        assertTest(ContentParser.sampaToIPA("@k\"nQlIÙ") == "/əkˈnɒlɪdʒ/", "sampaToIPA converts acknowledge to /əkˈnɒlɪdʒ/", ContentParser.sampaToIPA("@k\"nQlIÙ"))
        assertTest(ContentParser.sampaToIPA("@\"Íi:v") == "/əˈtʃiːv/", "sampaToIPA converts achieve to /əˈtʃiːv/", ContentParser.sampaToIPA("@\"Íi:v"))
        assertTest(ContentParser.sampaToIPA("&k\"sel@reIt@(r)") == "/ækˈseləreɪtə(r)/", "sampaToIPA converts accelerator to /ækˈseləreɪtə(r)/", ContentParser.sampaToIPA("&k\"sel@reIt@(r)"))

        // Test that 100% of parsed words have valid, non-empty, slash-enclosed IPA
        var emptyIPACount = 0
        var invalidIPACount = 0
        for w in parsedWords {
            if w.ipa.isEmpty {
                emptyIPACount += 1
            } else if !w.ipa.hasPrefix("/") || !w.ipa.hasSuffix("/") {
                invalidIPACount += 1
            }
        }
        assertTest(emptyIPACount == 0, "100% of parsed words have non-empty IPA pronunciation", "Found \(emptyIPACount) empty")
        assertTest(invalidIPACount == 0, "100% of parsed words have valid slash-wrapped /.../ IPA", "Found \(invalidIPACount) invalid")

        // 5. Test ContentParser.buildModules
        print("\n--- ContentParser.buildModules() Full Pipeline Execution ---")
        let builtModules = ContentParser.buildModules(
            settingsURL: settingsURL,
            wordListURL: wordListURL,
            definitionsURL: definitionsURL
        )
        assertTest(builtModules.count == 13, "buildModules produced 13 Module objects", "Found \(builtModules.count)")

        let builtUnits = builtModules.flatMap { $0.units }
        assertTest(builtUnits.count == 80, "buildModules produced 80 Unit objects", "Found \(builtUnits.count)")

        let totalWordsInUnits = builtUnits.reduce(0) { $0 + $1.words.count }
        assertTest(totalWordsInUnits == 3031, "Total word-unit assignments placed into units == 3,031", "Total words: \(totalWordsInUnits)")

        // 6. Test definition validity across all populated words
        var definedWordsCount = 0
        var emptyDefCount = 0
        for unit in builtUnits {
            for word in unit.words {
                if !word.definitions.isEmpty {
                    definedWordsCount += 1
                    for def in word.definitions {
                        if def.definition.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
                            emptyDefCount += 1
                        }
                    }
                }
            }
        }
        assertTest(definedWordsCount >= 1600, "Curriculum contains >= 1600 word-unit assignments with rich definitions", "Found \(definedWordsCount)")
        assertTest(emptyDefCount == 0, "100% of defined words have non-empty definitions", "Found \(emptyDefCount) empty definitions")

        // 7. Test Persistence Key schema
        var duplicateKeys = Set<String>()
        var seenKeys = Set<String>()
        for word in parsedWords {
            let key = "\(word.word)|\(word.unitNumbers.sorted().map(String.init).joined(separator: ","))"
            if seenKeys.contains(key) {
                duplicateKeys.insert(key)
            }
            seenKeys.insert(key)
        }
        assertTest(duplicateKeys.isEmpty, "Persistence keys are unique across all words", "Duplicates: \(duplicateKeys)")

        // 8. Test Word Headword Sanitization & Normalization Computed Properties
        print("\n--- Word Normalization & Spelling Properties Tests ---")
        let testWord1 = Word(word: "ad (= advertisement)", ipa: "/æd/", unitNumbers: [79], hasAudio: true)
        assertTest(testWord1.cleanWord == "ad", "cleanWord on 'ad (= advertisement)' is 'ad'", "Got: '\(testWord1.cleanWord)'")
        assertTest(testWord1.parentheticalGloss == "(= advertisement)", "parentheticalGloss on 'ad (= advertisement)' is '(= advertisement)'", "Got: '\(testWord1.parentheticalGloss ?? "nil")'")
        assertTest(testWord1.speechText == "ad", "speechText on 'ad (= advertisement)' is 'ad'", "Got: '\(testWord1.speechText)'")
        assertTest(testWord1.acceptedSpellings.contains("ad"), "acceptedSpellings contains 'ad'", "Got: \(testWord1.acceptedSpellings)")
        assertTest(testWord1.acceptedSpellings.contains("ad (= advertisement)"), "acceptedSpellings contains raw lowercased", "Got: \(testWord1.acceptedSpellings)")

        let testWord2 = Word(word: "backward(s)", ipa: "/ˈbækwəd(z)/", unitNumbers: [20], hasAudio: true)
        assertTest(testWord2.cleanWord == "backward", "cleanWord on 'backward(s)' is 'backward'", "Got: '\(testWord2.cleanWord)'")
        assertTest(testWord2.acceptedSpellings.contains("backward"), "acceptedSpellings contains 'backward'", "Got: \(testWord2.acceptedSpellings)")
        assertTest(testWord2.acceptedSpellings.contains("backwards"), "acceptedSpellings contains 'backwards'", "Got: \(testWord2.acceptedSpellings)")

        let testWord3 = Word(word: "how about ...?", ipa: "", unitNumbers: [77], hasAudio: false)
        assertTest(testWord3.speechText == "how about ?", "speechText strips ellipses from 'how about ...?'", "Got: '\(testWord3.speechText)'")

        let testWord4 = Word(word: "regular", ipa: "/ˈreɡjələ(r)/", unitNumbers: [5], hasAudio: true)
        assertTest(testWord4.cleanWord == "regular", "cleanWord on regular headword remains identical", "Got: '\(testWord4.cleanWord)'")
        assertTest(testWord4.parentheticalGloss == nil, "parentheticalGloss is nil when no parentheses", "Got: '\(testWord4.parentheticalGloss ?? "nil")'")

        // 9. Verify Sibling Unit Categorization Availability Across All 80 Units
        print("\n--- Categorization Sibling Availability Across All 80 Units ---")
        var failedUnits: [Int] = []
        for unitNum in 1...80 {
            var moduleUnits: [Unit] = []
            for module in builtModules {
                if module.units.contains(where: { $0.number == unitNum }) {
                    moduleUnits = module.units
                    break
                }
            }
            let validSiblings = moduleUnits.filter { $0.number != unitNum && $0.words.count >= 3 }
            if validSiblings.isEmpty {
                // Check fallback across all modules
                let allOtherUnits = builtModules.flatMap { $0.units }.filter { $0.number != unitNum && $0.words.count >= 3 }
                if allOtherUnits.count < 1 {
                    failedUnits.append(unitNum)
                }
            }
        }
        assertTest(failedUnits.isEmpty, "All 80 units have >= 1 valid sibling or fallback units with >= 3 words", "Failed on units: \(failedUnits)")

        // Summary
        print("\n=======================================================")
        print("\(bold)Swift Engine Pipeline Results: \(passCount) passed, \(failureCount) failed\(reset)")
        print("=======================================================\n")

        if failureCount > 0 {
            print("\(red)Swift Pipeline tests failed with \(failureCount) failure(s).\(reset)\n")
            exit(1)
        } else {
            print("\(green)All Swift Pipeline tests passed successfully! (exit 0)\(reset)\n")
            exit(0)
        }
    }
}
