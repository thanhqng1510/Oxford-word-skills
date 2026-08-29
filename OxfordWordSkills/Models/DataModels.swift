import Foundation

struct WordDefinition: Codable, Hashable {
    let partOfSpeech: String
    let definition: String
    let example: String
}

struct WordDetail: Codable {
    let word: String
    let phonetic: String
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
