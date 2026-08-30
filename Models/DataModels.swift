import Foundation

struct WordDefinition: Codable, Hashable {
    let partOfSpeech: String
    let definition: String
    let example: String
}

struct WordDetail: Codable {
    let word: String
    let phonetic: String?
    let meanings: [MeaningDetail]
}

struct MeaningDetail: Codable {
    let partOfSpeech: String
    let definitions: [DefEntry]
    let synonyms: [String]
    let antonyms: [String]
}

struct DefEntry: Codable {
    let definition: String
    let example: String
}

struct Word: Identifiable, Hashable {
    let id = UUID()
    let word: String
    let ipa: String
    let unitNumbers: [Int]
    let hasAudio: Bool
    var definitions: [WordDefinition] = []
    var synonyms: [String] = []
    var antonyms: [String] = []
    var examples: [String] = []

    var shortDefinition: String {
        definitions.first?.definition ?? "No definition available"
    }

    var partOfSpeech: String {
        definitions.first?.partOfSpeech ?? ""
    }

    func hash(into hasher: inout Hasher) {
        hasher.combine(id)
    }

    static func == (lhs: Word, rhs: Word) -> Bool {
        lhs.id == rhs.id
    }
}

struct UnitSection: Identifiable {
    let id = UUID()
    let title: String
    let type: String
}

struct Unit: Identifiable {
    let id = UUID()
    let number: Int
    let title: String
    let sections: [UnitSection]
    var words: [Word] = []
    var learnedCount: Int = 0
    var totalCount: Int { words.count }
    var progress: Double {
        guard totalCount > 0 else { return 0 }
        return Double(learnedCount) / Double(totalCount)
    }
}

struct Module: Identifiable {
    let id = UUID()
    let title: String
    var units: [Unit]
    var wordCount: Int { units.reduce(0) { $0 + $1.words.count } }
    var learnedCount: Int { units.reduce(0) { $0 + $1.learnedCount } }
    var progress: Double {
        guard wordCount > 0 else { return 0 }
        return Double(learnedCount) / Double(wordCount)
    }
}

enum ExerciseType: String, CaseIterable {
    case flashcard = "Flashcards"
    case definitionQuiz = "Word → Definition"
    case reverseQuiz = "Definition → Word"
    case spelling = "Listening & Spelling"
    case matching = "Synonym Match"
    case categorize = "Categorize"

    var icon: String {
        switch self {
        case .flashcard: return "rectangle.stack"
        case .definitionQuiz: return "text.book.closed"
        case .reverseQuiz: return "questionmark.circle"
        case .spelling: return "waveform"
        case .matching: return "arrow.triangle.branch"
        case .categorize: return "square.grid.2x2"
        }
    }
}

enum NavigationTarget: Hashable {
    case allWords
    case unit(Int)
    case exercise(ExerciseType, Int?)
    case progress
}

// MARK: - Word Clean Headword & Spelling Normalization

extension Word {
    /// The base word stripped of parenthetical glosses, e.g. "ad (= advertisement)" -> "ad"
    var cleanWord: String {
        if let parenIndex = word.firstIndex(of: "(") {
            let base = word[..<parenIndex].trimmingCharacters(in: .whitespaces)
            return base.isEmpty ? word : String(base)
        }
        return word
    }

    /// The parenthetical context gloss if present, e.g. "(= advertisement)"
    var parentheticalGloss: String? {
        guard let openParen = word.firstIndex(of: "(") else { return nil }
        let gloss = word[openParen...].trimmingCharacters(in: .whitespaces)
        return gloss.isEmpty ? nil : String(gloss)
    }

    /// Set of acceptable normalized spelling variations for listening & spelling exercises.
    var acceptedSpellings: [String] {
        var accepted: Set<String> = []

        // 1. Raw word string (lowercased, trimmed)
        accepted.insert(word.trimmingCharacters(in: .whitespaces).lowercased())

        // 2. Clean base word
        let clean = cleanWord.trimmingCharacters(in: .whitespaces).lowercased()
        if !clean.isEmpty {
            accepted.insert(clean)
        }

        // 3. Optional suffix variations e.g. "backward(s)" -> "backward" and "backwards"
        if word.contains("(s)") {
            let withS = word.replacingOccurrences(of: "(s)", with: "s")
                .split(separator: "(")[0]
                .trimmingCharacters(in: .whitespaces)
                .lowercased()
            let withoutS = word.replacingOccurrences(of: "(s)", with: "")
                .split(separator: "(")[0]
                .trimmingCharacters(in: .whitespaces)
                .lowercased()
            if !withS.isEmpty { accepted.insert(withS) }
            if !withoutS.isEmpty { accepted.insert(withoutS) }
        }

        // 4. Normalized without punctuation/parentheses/equal signs
        let stripped = word
            .replacingOccurrences(of: "(", with: "")
            .replacingOccurrences(of: ")", with: "")
            .replacingOccurrences(of: "=", with: "")
            .replacingOccurrences(of: "  ", with: " ")
            .trimmingCharacters(in: .whitespaces)
            .lowercased()
        if !stripped.isEmpty {
            accepted.insert(stripped)
        }

        return Array(accepted)
    }

    /// Clean spoken text for TTS synthesis (strips parenthetical glosses and trailing ellipses)
    var speechText: String {
        var text = cleanWord
        text = text.replacingOccurrences(of: "...", with: "")
        text = text.trimmingCharacters(in: .whitespaces)
        return text.isEmpty ? word : text
    }
}

