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
    var selectedVoice: VoiceOption = .default {
        didSet {
            UserDefaults.standard.set(selectedVoice.id, forKey: voicePrefKey)
            SpeechService.shared.activeVoice = selectedVoice
        }
    }

    private let learnedKey = "learnedWords"
    private let voicePrefKey = "selectedVoiceId"

    init() {
        loadData()
        loadProgress()
        loadVoicePreference()
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
            $0.definitions.contains { $0.definition.localizedCaseInsensitiveContains(searchText) } ||
            $0.allPartsOfSpeech.contains { $0.localizedCaseInsensitiveContains(searchText) } ||
            $0.synonyms.contains { $0.localizedCaseInsensitiveContains(searchText) } ||
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

        var seenWords = Set<String>()
        allWords = modules
            .flatMap { $0.units.flatMap { $0.words } }
            .filter { seenWords.insert($0.word).inserted }
            .sorted { $0.word.lowercased() < $1.word.lowercased() }
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

    private func loadVoicePreference() {
        if let savedId = UserDefaults.standard.string(forKey: voicePrefKey),
           let match = VoiceOption.supportedVoices.first(where: { $0.id == savedId }) {
            self.selectedVoice = match
        }
        SpeechService.shared.activeVoice = self.selectedVoice
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
