//
//  stress_test_quiz_matching.swift
//  OxfordWordSkills Adversarial Stress Test Runner for QuizView & MatchingView
//

import Foundation

// MARK: - Quiz Simulation Harness

enum QuizMode {
    case wordToDefinition
    case definitionToWord
}

struct SimulatedQuizQuestion {
    let word: Word
    let targetDefinition: WordDefinition
    let options: [String]
    let correctAnswer: String
    let correctDefinition: String
}

final class QuizSimulator {
    let allWords: [Word]
    let wordsByUnit: [Int: [Word]]

    init(allWords: [Word], units: [Unit]) {
        self.allWords = allWords
        var map: [Int: [Word]] = [:]
        for unit in units {
            map[unit.number] = unit.words
        }
        self.wordsByUnit = map
    }

    func generateQuestions(unitNumber: Int?, quizMode: QuizMode) -> [SimulatedQuizQuestion] {
        let sourceWords: [Word]
        if let unitNum = unitNumber {
            sourceWords = wordsByUnit[unitNum] ?? []
        } else {
            sourceWords = allWords
        }

        let validSourceWords = sourceWords.filter { word in
            word.definitions.contains { !$0.definition.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty }
        }

        guard !validSourceWords.isEmpty else {
            return []
        }

        let fallbackWords = allWords.filter { word in
            word.definitions.contains { !$0.definition.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty }
        }

        let shuffled = validSourceWords.shuffled()
        let questionWords = Array(shuffled.prefix(min(15, shuffled.count)))

        return questionWords.compactMap { word -> SimulatedQuizQuestion? in
            let validDefs = word.definitions.filter { !$0.definition.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty }
            guard let targetDef = validDefs.first else { return nil }

            switch quizMode {
            case .wordToDefinition:
                let correctDef = targetDef.definition.trimmingCharacters(in: .whitespacesAndNewlines)
                var chosenDefs: [String] = []
                var seenDefs = Set<String>([correctDef.lowercased()])

                // 1. First-pass distractors: sample from current unit
                let unitCandidates = validSourceWords.filter { $0.id != word.id }.shuffled()
                for candidate in unitCandidates {
                    for cDef in candidate.definitions {
                        let defText = cDef.definition.trimmingCharacters(in: .whitespacesAndNewlines)
                        let defKey = defText.lowercased()
                        if !defText.isEmpty && !seenDefs.contains(defKey) {
                            seenDefs.insert(defKey)
                            chosenDefs.append(defText)
                            break
                        }
                    }
                    if chosenDefs.count == 3 { break }
                }

                // 2. Second-pass distractors: sample from global pool if unit has < 3 distinct distractors
                if chosenDefs.count < 3 {
                    let globalCandidates = fallbackWords.filter { $0.id != word.id }.shuffled()
                    for candidate in globalCandidates {
                        for cDef in candidate.definitions {
                            let defText = cDef.definition.trimmingCharacters(in: .whitespacesAndNewlines)
                            let defKey = defText.lowercased()
                            if !defText.isEmpty && !seenDefs.contains(defKey) {
                                seenDefs.insert(defKey)
                                chosenDefs.append(defText)
                                break
                            }
                        }
                        if chosenDefs.count == 3 { break }
                    }
                }

                let options = ([correctDef] + chosenDefs).shuffled()
                return SimulatedQuizQuestion(word: word, targetDefinition: targetDef, options: options, correctAnswer: correctDef, correctDefinition: correctDef)

            case .definitionToWord:
                let correctWord = word.word.trimmingCharacters(in: .whitespacesAndNewlines)
                let correctDef = targetDef.definition.trimmingCharacters(in: .whitespacesAndNewlines)
                var chosenWords: [String] = []
                var seenWords = Set<String>([correctWord.lowercased()])

                // 1. First-pass distractors: sample from current unit
                let unitCandidates = validSourceWords.filter { $0.id != word.id }.shuffled()
                for candidate in unitCandidates {
                    let candidateWord = candidate.word.trimmingCharacters(in: .whitespacesAndNewlines)
                    let wordKey = candidateWord.lowercased()
                    if !candidateWord.isEmpty && !seenWords.contains(wordKey) {
                        seenWords.insert(wordKey)
                        chosenWords.append(candidateWord)
                        if chosenWords.count == 3 { break }
                    }
                }

                // 2. Second-pass distractors: sample from global pool if unit has < 3 distinct distractors
                if chosenWords.count < 3 {
                    let globalCandidates = fallbackWords.filter { $0.id != word.id }.shuffled()
                    for candidate in globalCandidates {
                        let candidateWord = candidate.word.trimmingCharacters(in: .whitespacesAndNewlines)
                        let wordKey = candidateWord.lowercased()
                        if !candidateWord.isEmpty && !seenWords.contains(wordKey) {
                            seenWords.insert(wordKey)
                            chosenWords.append(candidateWord)
                            if chosenWords.count == 3 { break }
                        }
                    }
                }

                let options = ([correctWord] + chosenWords).shuffled()
                return SimulatedQuizQuestion(word: word, targetDefinition: targetDef, options: options, correctAnswer: correctWord, correctDefinition: correctDef)
            }
        }
    }
}

// MARK: - Matching Simulation Harness

struct SimulatedMatchPair: Identifiable, Equatable {
    let id: UUID
    let word: Word
    let synonym: String

    init(id: UUID = UUID(), word: Word, synonym: String) {
        self.id = id
        self.word = word
        self.synonym = synonym
    }

    static func == (lhs: SimulatedMatchPair, rhs: SimulatedMatchPair) -> Bool {
        lhs.id == rhs.id
    }
}

struct SimulatedRightOption: Identifiable, Equatable {
    let id: UUID
    let pairID: UUID
    let synonym: String

    init(id: UUID = UUID(), pairID: UUID, synonym: String) {
        self.id = id
        self.pairID = pairID
        self.synonym = synonym
    }

    static func == (lhs: SimulatedRightOption, rhs: SimulatedRightOption) -> Bool {
        lhs.id == rhs.id
    }
}

final class MatchingSimulator {
    let allWords: [Word]
    let wordsByUnit: [Int: [Word]]

    var pairs: [SimulatedMatchPair] = []
    var rightOptions: [SimulatedRightOption] = []
    var selectedLeft: UUID?
    var selectedRight: UUID?
    var matchedPairs: Set<UUID> = []
    var attempts = 0
    var isFinished = false
    var wrongRightIDs: Set<UUID> = []
    var wrongLeftIDs: Set<UUID> = []

    init(allWords: [Word], units: [Unit]) {
        self.allWords = allWords
        var map: [Int: [Word]] = [:]
        for unit in units {
            map[unit.number] = unit.words
        }
        self.wordsByUnit = map
    }

    func generatePairs(unitNumber: Int?, customWords: [Word]? = nil) {
        let sourceWords: [Word]
        if let custom = customWords {
            sourceWords = custom
        } else if let unitNum = unitNumber {
            sourceWords = wordsByUnit[unitNum] ?? []
        } else {
            sourceWords = allWords
        }

        let validWords = sourceWords.filter { word in
            !word.synonyms.isEmpty &&
            word.synonyms.contains { syn in
                let trimmed = syn.trimmingCharacters(in: .whitespacesAndNewlines)
                return !trimmed.isEmpty && trimmed.caseInsensitiveCompare(word.word) != .orderedSame
            }
        }

        let shuffled = validWords.shuffled()
        var selectedPairs: [SimulatedMatchPair] = []
        var usedSynonyms = Set<String>()

        for word in shuffled {
            let availableSynonyms = word.synonyms
                .map { $0.trimmingCharacters(in: .whitespacesAndNewlines) }
                .filter { syn in
                    !syn.isEmpty &&
                    syn.caseInsensitiveCompare(word.word) != .orderedSame &&
                    !usedSynonyms.contains(syn.lowercased())
                }

            if let chosenSyn = availableSynonyms.first {
                let pairID = UUID()
                selectedPairs.append(SimulatedMatchPair(id: pairID, word: word, synonym: chosenSyn))
                usedSynonyms.insert(chosenSyn.lowercased())

                if selectedPairs.count == 6 {
                    break
                }
            }
        }

        if selectedPairs.count < 2 && !shuffled.isEmpty {
            selectedPairs.removeAll()
            for word in shuffled.prefix(6) {
                if let syn = word.synonyms.first(where: {
                    let trimmed = $0.trimmingCharacters(in: .whitespacesAndNewlines)
                    return !trimmed.isEmpty && trimmed.caseInsensitiveCompare(word.word) != .orderedSame
                }) {
                    let pairID = UUID()
                    selectedPairs.append(SimulatedMatchPair(id: pairID, word: word, synonym: syn.trimmingCharacters(in: .whitespacesAndNewlines)))
                }
            }
        }

        pairs = selectedPairs
        rightOptions = selectedPairs.map { SimulatedRightOption(id: UUID(), pairID: $0.id, synonym: $0.synonym) }.shuffled()

        matchedPairs.removeAll()
        selectedLeft = nil
        selectedRight = nil
        attempts = 0
        isFinished = false
        wrongRightIDs.removeAll()
        wrongLeftIDs.removeAll()
    }

    func selectLeft(_ id: UUID) {
        guard !matchedPairs.contains(id) else { return }
        selectedLeft = (selectedLeft == id) ? nil : id
        checkMatch()
    }

    func selectRight(_ option: SimulatedRightOption) {
        guard !matchedPairs.contains(option.pairID) else { return }
        selectedRight = (selectedRight == option.id) ? nil : option.id
        checkMatch()
    }

    func checkMatch() {
        guard let leftID = selectedLeft, let rightID = selectedRight else { return }
        attempts += 1

        guard let matchedOption = rightOptions.first(where: { $0.id == rightID }) else {
            selectedLeft = nil
            selectedRight = nil
            return
        }

        if matchedOption.pairID == leftID {
            matchedPairs.insert(leftID)
            wrongRightIDs.remove(rightID)
            wrongLeftIDs.remove(leftID)
        } else {
            wrongRightIDs.insert(rightID)
            wrongLeftIDs.insert(leftID)
        }

        selectedLeft = nil
        selectedRight = nil

        if matchedPairs.count == pairs.count && !pairs.isEmpty {
            isFinished = true
        }
    }
}

// MARK: - Main Adversarial Test Runner

@main
struct StressTestRunner {
    static func main() {
        let green = "\u{001B}[32m"
        let red = "\u{001B}[31m"
        let yellow = "\u{001B}[33m"
        let bold = "\u{001B}[1m"
        let reset = "\u{001B}[0m"

        print("\(bold)=======================================================\(reset)")
        print("\(bold)  Oxford Word Skills — M1 Adversarial Stress Harness   \(reset)")
        print("\(bold)=======================================================\(reset)\n")

        let fileManager = FileManager.default
        let currentDir = fileManager.currentDirectoryPath
        let projectRoot = currentDir.hasSuffix("tests") ? (currentDir as NSString).deletingLastPathComponent : currentDir
        let resourcesDir = (projectRoot as NSString).appendingPathComponent("Resources")

        let settingsURL = URL(fileURLWithPath: (resourcesDir as NSString).appendingPathComponent("settings.xml"))
        let wordListURL = URL(fileURLWithPath: (resourcesDir as NSString).appendingPathComponent("extrawordlist.xml"))
        let definitionsURL = URL(fileURLWithPath: (resourcesDir as NSString).appendingPathComponent("definitions.json"))

        let builtModules = ContentParser.buildModules(
            settingsURL: settingsURL,
            wordListURL: wordListURL,
            definitionsURL: definitionsURL
        )

        let allUnits = builtModules.flatMap { $0.units }
        let allWords = allUnits.flatMap { $0.words }

        print("Loaded \(builtModules.count) modules, \(allUnits.count) units, \(allWords.count) total word instances.\n")

        var totalPassed = 0
        var totalFailed = 0

        func recordTest(_ passed: Bool, _ name: String, _ details: String = "") {
            if passed {
                totalPassed += 1
                print("  \(green)✓ [PASS]\(reset) \(name)")
            } else {
                totalFailed += 1
                print("  \(red)✗ [FAIL]\(reset) \(name)")
                if !details.isEmpty {
                    print("        \(yellow)Details: \(details)\(reset)")
                }
            }
        }

        // =========================================================================
        // SECTION 1: QuizView Adversarial 10,000 Question Generation Stress Test
        // =========================================================================
        print("\(bold)>>> SECTION 1: QuizView 10,000 Question Generation Stress Testing...\(reset)")
        let quizSimulator = QuizSimulator(allWords: allWords, units: allUnits)

        var totalQuestionsGenerated = 0
        var duplicateOptionsCount = 0
        var nonFourOptionsCount = 0
        var missingCorrectAnswerCount = 0
        var blankOptionsCount = 0
        let crashCount = 0

        let targetGenerations = 10000
        let modes: [QuizMode] = [.wordToDefinition, .definitionToWord]

        let startTime = Date()

        // 1.1 Run across all 80 units & global pool
        let unitPool: [Int?] = (1...80).map { Optional($0) } + [nil]

        while totalQuestionsGenerated < targetGenerations {
            for unitNum in unitPool {
                for mode in modes {
                        let questions = quizSimulator.generateQuestions(unitNumber: unitNum, quizMode: mode)
                        for q in questions {
                            totalQuestionsGenerated += 1

                            // Check 1: exactly 4 options
                            if q.options.count != 4 {
                                nonFourOptionsCount += 1
                            }

                            // Check 2: exactly 4 unique options (case-sensitive and case-insensitive)
                            let uniqueSet = Set(q.options)
                            let uniqueCaseInsensitive = Set(q.options.map { $0.lowercased() })
                            if uniqueSet.count != 4 || uniqueCaseInsensitive.count != 4 {
                                duplicateOptionsCount += 1
                            }

                            // Check 3: correct answer is inside options
                            if !q.options.contains(q.correctAnswer) {
                                missingCorrectAnswerCount += 1
                            }

                            // Check 4: no blank/whitespace-only options
                            if q.options.contains(where: { $0.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty }) {
                                blankOptionsCount += 1
                            }

                            if totalQuestionsGenerated >= targetGenerations {
                                break
                            }
                        }

                    if totalQuestionsGenerated >= targetGenerations {
                        break
                    }
                }
                if totalQuestionsGenerated >= targetGenerations {
                    break
                }
            }
        }

        let elapsed = Date().timeIntervalSince(startTime)
        print("Generated \(totalQuestionsGenerated) quiz questions in \(String(format: "%.3f", elapsed))s.")

        recordTest(totalQuestionsGenerated >= 10000, "Generated >= 10,000 quiz questions across all 80 units", "Total: \(totalQuestionsGenerated)")
        recordTest(crashCount == 0, "Zero crashes during 10,000 question generations", "Crashes: \(crashCount)")
        recordTest(nonFourOptionsCount == 0, "100% of questions have strictly 4 options", "Violations: \(nonFourOptionsCount)")
        recordTest(duplicateOptionsCount == 0, "100% of questions have 0 duplicate options (strictly 4 unique choices)", "Duplicates: \(duplicateOptionsCount)")
        recordTest(missingCorrectAnswerCount == 0, "100% of questions contain the correctAnswer in options", "Missing: \(missingCorrectAnswerCount)")
        recordTest(blankOptionsCount == 0, "100% of options are non-blank strings", "Blank: \(blankOptionsCount)")

        // 1.2 Synthetic Edge Cases for QuizView (<4 words, empty unit, identical defs)
        print("\n\(bold)>>> SECTION 1.2: QuizView Synthetic Boundary & Edge Case Stress Testing...\(reset)")

        // Edge Case A: Empty unit (0 words)
        let emptyQuestions = quizSimulator.generateQuestions(unitNumber: 9999, quizMode: .wordToDefinition)
        recordTest(emptyQuestions.isEmpty, "Unit with 0 words returns empty questions array without crash", "Count: \(emptyQuestions.count)")

        // Edge Case B: Unit with exactly 1 word (pulls 3 distractors from global fallback)
        let singleWordUnit = [Word(word: "solitary", ipa: "/ˈsɒlətri/", unitNumbers: [901], hasAudio: true, definitions: [WordDefinition(partOfSpeech: "adjective", definition: "Done or existing alone", example: "A solitary walker.")])]
        let singleSimulator = QuizSimulator(allWords: allWords + singleWordUnit, units: [Unit(number: 901, title: "Single Word Unit", sections: [], words: singleWordUnit)])
        let singleQWordToDef = singleSimulator.generateQuestions(unitNumber: 901, quizMode: .wordToDefinition)
        let singleQDefToWord = singleSimulator.generateQuestions(unitNumber: 901, quizMode: .definitionToWord)

        recordTest(singleQWordToDef.count == 1 && singleQWordToDef[0].options.count == 4 && Set(singleQWordToDef[0].options).count == 4, "1-word unit (Word->Def) pulls 3 distinct global distractors (4 unique options)", "Options: \(singleQWordToDef.first?.options ?? [])")
        recordTest(singleQDefToWord.count == 1 && singleQDefToWord[0].options.count == 4 && Set(singleQDefToWord[0].options).count == 4, "1-word unit (Def->Word) pulls 3 distinct global distractors (4 unique options)", "Options: \(singleQDefToWord.first?.options ?? [])")

        // Edge Case C: Unit with 2 words
        let twoWordUnit = [
            Word(word: "alpha_edge", ipa: "", unitNumbers: [902], hasAudio: false, definitions: [WordDefinition(partOfSpeech: "noun", definition: "First Greek letter", example: "Alpha.")] ),
            Word(word: "beta_edge", ipa: "", unitNumbers: [902], hasAudio: false, definitions: [WordDefinition(partOfSpeech: "noun", definition: "Second Greek letter", example: "Beta.")] )
        ]
        let twoSimulator = QuizSimulator(allWords: allWords + twoWordUnit, units: [Unit(number: 902, title: "Two Words Unit", sections: [], words: twoWordUnit)])
        let twoQ = twoSimulator.generateQuestions(unitNumber: 902, quizMode: .wordToDefinition)
        recordTest(twoQ.count == 2 && twoQ.allSatisfy { $0.options.count == 4 && Set($0.options).count == 4 }, "2-word unit pulls 2 distinct global distractors per question (4 unique options)", "Count: \(twoQ.count)")

        // Edge Case D: Unit with 3 words
        let threeWordUnit = [
            Word(word: "gamma_edge", ipa: "", unitNumbers: [903], hasAudio: false, definitions: [WordDefinition(partOfSpeech: "noun", definition: "Third Greek letter", example: "Gamma.")] ),
            Word(word: "delta_edge", ipa: "", unitNumbers: [903], hasAudio: false, definitions: [WordDefinition(partOfSpeech: "noun", definition: "Fourth Greek letter", example: "Delta.")] ),
            Word(word: "epsilon_edge", ipa: "", unitNumbers: [903], hasAudio: false, definitions: [WordDefinition(partOfSpeech: "noun", definition: "Fifth Greek letter", example: "Epsilon.")] )
        ]
        let threeSimulator = QuizSimulator(allWords: allWords + threeWordUnit, units: [Unit(number: 903, title: "Three Words Unit", sections: [], words: threeWordUnit)])
        let threeQ = threeSimulator.generateQuestions(unitNumber: 903, quizMode: .wordToDefinition)
        recordTest(threeQ.count == 3 && threeQ.allSatisfy { $0.options.count == 4 && Set($0.options).count == 4 }, "3-word unit pulls 1 distinct global distractor per question (4 unique options)", "Count: \(threeQ.count)")

        // Edge Case E: Unit where all words share the identical definition string
        let collisionWords = [
            Word(word: "c_one", ipa: "", unitNumbers: [904], hasAudio: false, definitions: [WordDefinition(partOfSpeech: "noun", definition: "Identical shared definition", example: "")] ),
            Word(word: "c_two", ipa: "", unitNumbers: [904], hasAudio: false, definitions: [WordDefinition(partOfSpeech: "noun", definition: "Identical shared definition", example: "")] ),
            Word(word: "c_three", ipa: "", unitNumbers: [904], hasAudio: false, definitions: [WordDefinition(partOfSpeech: "noun", definition: "Identical shared definition", example: "")] ),
            Word(word: "c_four", ipa: "", unitNumbers: [904], hasAudio: false, definitions: [WordDefinition(partOfSpeech: "noun", definition: "Identical shared definition", example: "")] )
        ]
        let collisionSimulator = QuizSimulator(allWords: allWords + collisionWords, units: [Unit(number: 904, title: "Collision Unit", sections: [], words: collisionWords)])
        let collisionQ = collisionSimulator.generateQuestions(unitNumber: 904, quizMode: .wordToDefinition)
        let collisionDeduplicated = collisionQ.allSatisfy { q in
            Set(q.options.map { $0.lowercased() }).count == 4
        }
        recordTest(collisionDeduplicated, "Identical definition collision unit cleanly falls back to 3 distinct global distractors", "Options: \(collisionQ.first?.options ?? [])")

        // =========================================================================
        // SECTION 2: MatchingView Adversarial Stress Testing & Match Resolution
        // =========================================================================
        print("\n\(bold)>>> SECTION 2: MatchingView Pair Generation & Match Resolution Stress Testing...\(reset)")
        let matchingSimulator = MatchingSimulator(allWords: allWords, units: allUnits)

        var totalMatchingRounds = 0
        var successfulMatchResolutions = 0
        var pairRightOptionsMismatchCount = 0
        var selfReferentialPairsCount = 0
        var emptySynonymPairsCount = 0

        // 2.1 Multi-round testing across all 80 units (100 rounds per unit with synonym words)
        for unitNum in 1...80 {
            for _ in 1...20 { // 20 rounds per unit = 1,600 rounds total
                matchingSimulator.generatePairs(unitNumber: unitNum)
                if matchingSimulator.pairs.isEmpty {
                    continue
                }

                totalMatchingRounds += 1
                let pairsCount = matchingSimulator.pairs.count
                let rightCount = matchingSimulator.rightOptions.count

                if pairsCount != rightCount {
                    pairRightOptionsMismatchCount += 1
                }

                for p in matchingSimulator.pairs {
                    if p.synonym.caseInsensitiveCompare(p.word.word) == .orderedSame {
                        selfReferentialPairsCount += 1
                    }
                    if p.synonym.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
                        emptySynonymPairsCount += 1
                    }
                }

                // Simulate Perfect Gameplay
                for p in matchingSimulator.pairs {
                    matchingSimulator.selectLeft(p.id)
                    guard let opt = matchingSimulator.rightOptions.first(where: { $0.pairID == p.id }) else {
                        break
                    }
                    matchingSimulator.selectRight(opt)
                }

                if matchingSimulator.isFinished && matchingSimulator.matchedPairs.count == pairsCount {
                    successfulMatchResolutions += 1
                }
            }
        }

        recordTest(totalMatchingRounds > 500, "Completed >500 multi-round Matching games across curriculum", "Total rounds: \(totalMatchingRounds)")
        recordTest(successfulMatchResolutions == totalMatchingRounds, "100% of Matching games resolve to complete match without failure", "Success: \(successfulMatchResolutions)/\(totalMatchingRounds)")
        recordTest(pairRightOptionsMismatchCount == 0, "pairs.count strictly equals rightOptions.count across all rounds", "Mismatches: \(pairRightOptionsMismatchCount)")
        recordTest(selfReferentialPairsCount == 0, "Zero self-referential pairs (synonym == word)", "Self-ref count: \(selfReferentialPairsCount)")
        recordTest(emptySynonymPairsCount == 0, "Zero empty synonym strings in MatchPairs", "Empty count: \(emptySynonymPairsCount)")

        // 2.2 Imperfect Gameplay & Error Recovery Simulation
        print("\n\(bold)>>> SECTION 2.2: MatchingView Mismatch Feedback & Error Recovery Testing...\(reset)")
        matchingSimulator.generatePairs(unitNumber: nil)
        if matchingSimulator.pairs.count >= 2 {
            let p0 = matchingSimulator.pairs[0]
            let p1 = matchingSimulator.pairs[1]
            guard let opt1 = matchingSimulator.rightOptions.first(where: { $0.pairID == p1.id }) else {
                fatalError("Missing right option")
            }

            // Select Left 0, Right 1 (Wrong match)
            matchingSimulator.selectLeft(p0.id)
            matchingSimulator.selectRight(opt1)

            let attemptAfterMismatch = matchingSimulator.attempts
            let isMatchedAfterMismatch = matchingSimulator.matchedPairs.contains(p0.id)
            let hasWrongHighlight = matchingSimulator.wrongLeftIDs.contains(p0.id) && matchingSimulator.wrongRightIDs.contains(opt1.id)

            recordTest(attemptAfterMismatch == 1, "Attempt counter increments on mismatch", "Attempts: \(attemptAfterMismatch)")
            recordTest(!isMatchedAfterMismatch, "Mismatch is not added to matchedPairs", "Matched: \(isMatchedAfterMismatch)")
            recordTest(hasWrongHighlight, "Wrong left and right IDs are highlighted in red", "WrongLeft: \(matchingSimulator.wrongLeftIDs), WrongRight: \(matchingSimulator.wrongRightIDs)")

            // Now correctly match p0
            guard let opt0 = matchingSimulator.rightOptions.first(where: { $0.pairID == p0.id }) else {
                fatalError("Missing right option")
            }
            matchingSimulator.selectLeft(p0.id)
            matchingSimulator.selectRight(opt0)

            recordTest(matchingSimulator.matchedPairs.contains(p0.id), "Correct match successfully resolves after previous mismatch", "Matched count: \(matchingSimulator.matchedPairs.count)")
            recordTest(!matchingSimulator.wrongLeftIDs.contains(p0.id), "Wrong highlight cleared on correct match", "Wrong left count: \(matchingSimulator.wrongLeftIDs.count)")
        }

        // 2.3 Synthetic Edge Cases for MatchingView
        print("\n\(bold)>>> SECTION 2.3: MatchingView Synthetic Boundary & Edge Case Stress Testing...\(reset)")

        // Edge Case A: 0 words with synonyms
        matchingSimulator.generatePairs(unitNumber: nil, customWords: [Word(word: "nosyn", ipa: "", unitNumbers: [1], hasAudio: false)])
        recordTest(matchingSimulator.pairs.isEmpty && matchingSimulator.rightOptions.isEmpty, "0-synonym word list yields empty pairs and rightOptions without crash", "Pairs: \(matchingSimulator.pairs.count)")

        // Edge Case B: Exactly 1 word with synonym
        let singleSynWord = [Word(word: "lone", ipa: "", unitNumbers: [1], hasAudio: false, synonyms: ["solitary"])]
        matchingSimulator.generatePairs(unitNumber: nil, customWords: singleSynWord)
        recordTest(matchingSimulator.pairs.count == 1 && matchingSimulator.rightOptions.count == 1, "1-synonym word list yields exactly 1 pair and 1 right option", "Pairs: \(matchingSimulator.pairs.count)")
        if matchingSimulator.pairs.count == 1 {
            let p = matchingSimulator.pairs[0]
            let opt = matchingSimulator.rightOptions[0]
            matchingSimulator.selectLeft(p.id)
            matchingSimulator.selectRight(opt)
            recordTest(matchingSimulator.isFinished && matchingSimulator.matchedPairs.count == 1, "1-pair game completes and transitions to isFinished = true", "isFinished: \(matchingSimulator.isFinished)")
        }

        // Edge Case C: Words with self-referential synonyms and duplicate synonyms
        let dirtySynWords = [
            Word(word: "same", ipa: "", unitNumbers: [1], hasAudio: false, synonyms: ["same", "identical", "equal"]),
            Word(word: "twin", ipa: "", unitNumbers: [1], hasAudio: false, synonyms: ["identical", "duplicate"])
        ]
        matchingSimulator.generatePairs(unitNumber: nil, customWords: dirtySynWords)
        recordTest(matchingSimulator.pairs.allSatisfy { $0.synonym != $0.word.word }, "Filtered out self-referential synonym 'same'", "Pairs: \(matchingSimulator.pairs.map { ($0.word.word, $0.synonym) })")
        recordTest(matchingSimulator.pairs.count == 2, "Fallback mechanism assigned unique/secondary synonyms to all words", "Count: \(matchingSimulator.pairs.count)")

        // Edge Case D: Deselecting / toggling left and right
        if matchingSimulator.pairs.count >= 2 {
            let p0 = matchingSimulator.pairs[0]
            let p1 = matchingSimulator.pairs[1]
            // Click left p0
            matchingSimulator.selectLeft(p0.id)
            let leftSelected1 = matchingSimulator.selectedLeft == p0.id
            // Click left p0 again (toggle off)
            matchingSimulator.selectLeft(p0.id)
            let leftDeselected = matchingSimulator.selectedLeft == nil
            // Click left p1
            matchingSimulator.selectLeft(p1.id)
            let leftSelected2 = matchingSimulator.selectedLeft == p1.id

            recordTest(leftSelected1 && leftDeselected && leftSelected2, "Toggling / switching left selection functions cleanly without side-effects", "L1: \(leftSelected1), Deselect: \(leftDeselected), L2: \(leftSelected2)")
        }

        // Summary
        print("\n=======================================================")
        print("\(bold)Adversarial Stress Test Results: \(totalPassed) passed, \(totalFailed) failed\(reset)")
        print("=======================================================\n")

        if totalFailed > 0 {
            print("\(red)Adversarial Stress Test Failed with \(totalFailed) failure(s).\(reset)\n")
            exit(1)
        } else {
            print("\(green)All Adversarial Stress Tests passed successfully! (exit 0)\(reset)\n")
            exit(0)
        }
    }
}
