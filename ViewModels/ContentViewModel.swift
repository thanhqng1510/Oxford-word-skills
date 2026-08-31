import Foundation
import SwiftUI

@Observable
class ContentViewModel {
    var modules: [Module] = []
    var allWords: [Word] = []
    var selectedModuleIndex: Int?
    var selectedUnitNumber: Int?
    var selectedNavigation: NavigationTarget = .allWords
    var searchText: String = ""
    var learnedWordIDs: Set<String> = []

    private let learnedKey = "learnedWords"

    init() {
        loadData()
        loadProgress()
    }

    var filteredWords: [Word] {
        let words: [Word]
        if case .unit(let unitNumber) = selectedNavigation {
            words = wordsForUnit(unitNumber)
        } else {
            words = allWords
        }

        guard !searchText.isEmpty else { return words }
        return words.filter {
            $0.word.localizedCaseInsensitiveContains(searchText) ||
            $0.shortDefinition.localizedCaseInsensitiveContains(searchText) ||
            $0.ipa.localizedCaseInsensitiveContains(searchText)
        }
    }

    var currentUnit: Unit? {
        guard let unitNum = selectedUnitNumber else { return nil }
        for module in modules {
            if let unit = module.units.first(where: { $0.number == unitNum }) {
                return unit
            }
        }
        return nil
    }

    var currentModule: Module? {
        guard let idx = selectedModuleIndex else { return nil }
        guard idx < modules.count else { return nil }
        return modules[idx]
    }

    var totalWordCount: Int { allWords.count }
    var totalLearnedCount: Int { learnedWordIDs.count }
    var overallProgress: Double {
        guard totalWordCount > 0 else { return 0 }
        return Double(totalLearnedCount) / Double(totalWordCount)
    }

    func wordsForUnit(_ unitNumber: Int) -> [Word] {
        for module in modules {
            if let unit = module.units.first(where: { $0.number == unitNumber }) {
                return unit.words
            }
        }
        return []
    }

    func toggleLearned(_ word: Word) {
        let key = wordKey(word)
        if learnedWordIDs.contains(key) {
            learnedWordIDs.remove(key)
        } else {
            learnedWordIDs.insert(key)
        }
        saveProgress()
        updateModuleProgress()
    }

    func isLearned(_ word: Word) -> Bool {
        learnedWordIDs.contains(wordKey(word))
    }

    func markAllLearned(in unitNumber: Int) {
        let words = wordsForUnit(unitNumber)
        for word in words {
            learnedWordIDs.insert(wordKey(word))
        }
        saveProgress()
        updateModuleProgress()
    }

    func resetProgress(for unitNumber: Int) {
        let words = wordsForUnit(unitNumber)
        for word in words {
            learnedWordIDs.remove(wordKey(word))
        }
        saveProgress()
        updateModuleProgress()
    }

    func resetAllProgress() {
        learnedWordIDs.removeAll()
        saveProgress()
        updateModuleProgress()
    }

    func wordsWithDefinitions(in unitNumber: Int? = nil) -> [Word] {
        let source = unitNumber != nil ? wordsForUnit(unitNumber!) : allWords
        return source.filter { !$0.definitions.isEmpty }
    }

    private func wordKey(_ word: Word) -> String {
        "\(word.word)|\(word.unitNumbers.sorted().map(String.init).joined(separator: ","))"
    }

    private func loadData() {
        guard let settingsURL = Bundle.main.url(forResource: "settings", withExtension: "xml"),
              let wordListURL = Bundle.main.url(forResource: "extrawordlist", withExtension: "xml") else {
            return
        }

        let definitionsURL = Bundle.main.url(forResource: "definitions", withExtension: "json")

        modules = ContentParser.buildModules(
            settingsURL: settingsURL,
            wordListURL: wordListURL,
            definitionsURL: definitionsURL
        )

        allWords = ContentParser.parseWordList(from: wordListURL)

        // Merge definitions into allWords too
        if let defURL = definitionsURL {
            let defs = ContentParser.parseDefinitions(from: defURL)
            for i in allWords.indices {
                let key = allWords[i].word
                if let detail = defs[key] {
                    var wordDefs: [WordDefinition] = []
                    var allSyns: [String] = []
                    var allAnts: [String] = []
                    var allExs: [String] = []

                    for meaning in detail.meanings {
                        for def in meaning.definitions {
                            wordDefs.append(WordDefinition(
                                partOfSpeech: meaning.partOfSpeech,
                                definition: def.definition,
                                example: def.example
                            ))
                            if !def.example.isEmpty { allExs.append(def.example) }
                        }
                        allSyns.append(contentsOf: meaning.synonyms)
                        allAnts.append(contentsOf: meaning.antonyms)
                    }

                    allWords[i] = Word(
                        word: allWords[i].word,
                        ipa: allWords[i].ipa,
                        unitNumbers: allWords[i].unitNumbers,
                        hasAudio: allWords[i].hasAudio,
                        definitions: wordDefs,
                        synonyms: Array(allSyns.uniqued().prefix(10)),
                        antonyms: Array(allAnts.uniqued().prefix(10)),
                        examples: Array(allExs.uniqued().prefix(5))
                    )
                }
            }
        }

        allWords.sort { $0.word.lowercased() < $1.word.lowercased() }
    }

    private func loadProgress() {
        if let saved = UserDefaults.standard.stringArray(forKey: learnedKey) {
            learnedWordIDs = Set(saved)
        }
        updateModuleProgress()
    }

    private func saveProgress() {
        UserDefaults.standard.set(Array(learnedWordIDs), forKey: learnedKey)
    }

    private func updateModuleProgress() {
        for moduleIdx in modules.indices {
            for unitIdx in modules[moduleIdx].units.indices {
                let unit = modules[moduleIdx].units[unitIdx]
                modules[moduleIdx].units[unitIdx].learnedCount = unit.words.filter { isLearned($0) }.count
            }
        }
    }
}
