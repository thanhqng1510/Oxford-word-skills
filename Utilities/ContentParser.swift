import Foundation

class ContentParser {
    static func parseSettings(from url: URL) -> [(title: String, units: [(number: Int, title: String, sections: [(title: String, type: String)])])] {
        guard let data = try? Data(contentsOf: url),
              let doc = try? XMLDocument(data: data, options: []) else { return [] }

        var modules: [(title: String, units: [(number: Int, title: String, sections: [(title: String, type: String)])])] = []

        guard let moduleNodes = try? doc.nodes(forXPath: "/settings/module") else { return [] }

        for moduleNode in moduleNodes {
            guard let moduleElem = moduleNode as? XMLElement else { continue }
            let moduleTitle = moduleElem.attribute(forName: "title")?.stringValue ?? ""

            var units: [(number: Int, title: String, sections: [(title: String, type: String)])] = []

            guard let unitNodes = try? moduleElem.nodes(forXPath: "unit") else { continue }

            for unitNode in unitNodes {
                guard let unitElem = unitNode as? XMLElement else { continue }
                let unitNumber = Int(unitElem.attribute(forName: "number")?.stringValue ?? "0") ?? 0
                let unitTitle = unitElem.attribute(forName: "title")?.stringValue ?? ""

                var sections: [(title: String, type: String)] = []
                if let sectionNodes = try? unitElem.nodes(forXPath: "section") {
                    for sectionNode in sectionNodes {
                        guard let sectionElem = sectionNode as? XMLElement else { continue }
                        let sectionTitle = sectionElem.attribute(forName: "title")?.stringValue ?? ""
                        let sectionType = sectionElem.attribute(forName: "type")?.stringValue ?? ""
                        sections.append((title: sectionTitle, type: sectionType))
                    }
                }

                units.append((number: unitNumber, title: unitTitle, sections: sections))
            }

            modules.append((title: moduleTitle, units: units))
        }

        return modules
    }

    /// Converts legacy Oxford SAMPA / ASCII phonetic encoding into standard British Unicode IPA enclosed in slashes.
    static func sampaToIPA(_ sampa: String) -> String {
        let trimmed = sampa.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return "" }

        if trimmed.hasPrefix("/") && trimmed.hasSuffix("/") {
            return trimmed
        }

        var text = trimmed
        text = text.replacingOccurrences(of: "”", with: "\"")
        text = text.replacingOccurrences(of: "Í", with: "tS")
        text = text.replacingOccurrences(of: "Ù", with: "dZ")
        text = text.replacingOccurrences(of: "2@", with: "@")
        text = text.replacingOccurrences(of: "Ww", with: "w")
        text = text.replacingOccurrences(of: "2", with: "@")

        let replacements: [(String, String)] = [
            ("\"", "ˈ"),
            ("%", "ˌ"),
            ("tS", "tʃ"),
            ("dZ", "dʒ"),
            ("eI", "eɪ"),
            ("aI", "aɪ"),
            ("OI", "ɔɪ"),
            ("aU", "aʊ"),
            ("@U", "əʊ"),
            ("I@", "ɪə"),
            ("e@", "eə"),
            ("U@", "ʊə"),
            ("3:", "ɜː"),
            ("3", "ɜː"),
            ("i:", "iː"),
            ("u:", "uː"),
            ("A:", "ɑː"),
            ("O:", "ɔː"),
            (":", "ː"),
            ("@", "ə"),
            ("&", "æ"),
            ("A", "ɑː"),
            ("V", "ʌ"),
            ("O", "ɔː"),
            ("Q", "ɒ"),
            ("U", "ʊ"),
            ("I", "ɪ"),
            ("E", "e"),
            ("T", "θ"),
            ("D", "ð"),
            ("S", "ʃ"),
            ("Z", "ʒ"),
            ("N", "ŋ")
        ]

        for (pattern, replacement) in replacements {
            text = text.replacingOccurrences(of: pattern, with: replacement)
        }

        while text.contains("  ") {
            text = text.replacingOccurrences(of: "  ", with: " ")
        }
        text = text.trimmingCharacters(in: .whitespacesAndNewlines)

        return "/\(text)/"
    }

    static func parseWordList(from url: URL) -> [Word] {
        guard let data = try? Data(contentsOf: url),
              let doc = try? XMLDocument(data: data, options: []) else { return [] }

        var words: [Word] = []
        guard let wordNodes = try? doc.nodes(forXPath: "//word") else { return [] }

        for wordNode in wordNodes {
            guard let wordElem = wordNode as? XMLElement else { continue }
            let str = wordElem.attribute(forName: "str")?.stringValue ?? ""
            let unitStr = wordElem.attribute(forName: "unit")?.stringValue ?? ""

            let unitNumbers = unitStr.components(separatedBy: ",")
                .map { $0.trimmingCharacters(in: .whitespaces) }
                .compactMap { Int($0) }

            let ipaNodes = try? wordElem.nodes(forXPath: "ipa")
            let rawIpa = ipaNodes?.first?.stringValue ?? ""
            let ipa = sampaToIPA(rawIpa)

            let audioNodes = try? wordElem.nodes(forXPath: "audio")
            let hasAudio = !(audioNodes ?? []).isEmpty

            let word = Word(
                word: str,
                ipa: ipa,
                unitNumbers: unitNumbers,
                hasAudio: hasAudio
            )
            if isValidWord(str) {
                words.append(word)
            }
        }

        return words
    }

    private static func isValidWord(_ str: String) -> Bool {
        let trimmed = str.trimmingCharacters(in: .whitespaces)
        if trimmed.count < 2 { return false }
        if trimmed.hasPrefix("-") || trimmed.hasSuffix("-") { return false }
        return true
    }

    static func parseDefinitions(from url: URL) -> [String: WordDetail] {
        guard let data = try? Data(contentsOf: url) else { return [:] }
        guard let decoded = try? JSONDecoder().decode([String: WordDetail].self, from: data) else { return [:] }
        return decoded
    }

    static func buildModules(settingsURL: URL, wordListURL: URL, definitionsURL: URL?) -> [Module] {
        let settingsData = parseSettings(from: settingsURL)
        var allWords = parseWordList(from: wordListURL)

        // Load definitions if available
        var definitions: [String: WordDetail] = [:]
        if let defURL = definitionsURL {
            definitions = parseDefinitions(from: defURL)
        }

        // Merge definitions into words
        for i in allWords.indices {
            let key = allWords[i].word
            if let detail = definitions[key] {
                var defs: [WordDefinition] = []
                var allSynonyms: [String] = []
                var allAntonyms: [String] = []
                var allExamples: [String] = []

                for meaning in detail.meanings {
                    for def in meaning.definitions {
                        defs.append(WordDefinition(
                            partOfSpeech: meaning.partOfSpeech,
                            definition: def.definition,
                            example: def.example
                        ))
                        if !def.example.isEmpty {
                            allExamples.append(def.example)
                        }
                    }
                    allSynonyms.append(contentsOf: meaning.synonyms)
                    allAntonyms.append(contentsOf: meaning.antonyms)
                }

                let cleanSynonyms = allSynonyms
                    .map { $0.trimmingCharacters(in: .whitespacesAndNewlines) }
                    .filter { syn in
                        !syn.isEmpty &&
                        syn.caseInsensitiveCompare(key) != .orderedSame &&
                        !syn.localizedCaseInsensitiveContains("equivalent") &&
                        !syn.localizedCaseInsensitiveContains("placeholder")
                    }

                let cleanAntonyms = allAntonyms
                    .map { $0.trimmingCharacters(in: .whitespacesAndNewlines) }
                    .filter { ant in
                        !ant.isEmpty &&
                        ant.caseInsensitiveCompare(key) != .orderedSame &&
                        !ant.localizedCaseInsensitiveContains("equivalent") &&
                        !ant.localizedCaseInsensitiveContains("placeholder")
                    }

                allWords[i] = Word(
                    word: allWords[i].word,
                    ipa: allWords[i].ipa,
                    unitNumbers: allWords[i].unitNumbers,
                    hasAudio: allWords[i].hasAudio,
                    definitions: defs,
                    synonyms: Array(cleanSynonyms.uniqued().prefix(10)),
                    antonyms: Array(cleanAntonyms.uniqued().prefix(10)),
                    examples: Array(allExamples.uniqued().prefix(5))
                )
            }
        }

        var wordsByUnit: [Int: [Word]] = [:]
        for word in allWords {
            for unitNum in word.unitNumbers {
                wordsByUnit[unitNum, default: []].append(word)
            }
        }

        return settingsData.map { moduleData in
            let units = moduleData.units.map { unitData in
                Unit(
                    number: unitData.number,
                    title: unitData.title,
                    sections: unitData.sections.map {
                        UnitSection(title: $0.title, type: $0.type)
                    },
                    words: (wordsByUnit[unitData.number] ?? []).sorted { $0.word.lowercased() < $1.word.lowercased() }
                )
            }
            return Module(title: moduleData.title, units: units)
        }
    }
}

extension Sequence where Element: Hashable {
    func uniqued() -> [Element] {
        var seen = Set<Element>()
        return filter { seen.insert($0).inserted }
    }
}
