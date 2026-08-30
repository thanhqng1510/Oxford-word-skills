//
//  inspect_parenthetical_words.swift
//  OxfordWordSkills Inspection Script
//

import Foundation

@main
struct Inspector {
    static func main() {
        let fileManager = FileManager.default
        let currentDir = fileManager.currentDirectoryPath
        let projectRoot = currentDir.hasSuffix("tests") ? (currentDir as NSString).deletingLastPathComponent : currentDir
        let wordListURL = URL(fileURLWithPath: (projectRoot as NSString).appendingPathComponent("Resources/extrawordlist.xml"))

        let words = ContentParser.parseWordList(from: wordListURL)
        print("Total parsed words: \(words.count)")

        let parenWords = words.filter { $0.word.contains("(") || $0.word.contains(")") }
        print("Words containing parentheses: \(parenWords.count)\n")

        for (index, w) in parenWords.enumerated() {
            print(String(format: "[%3d] Raw: '%@'", index + 1, w.word))
            print("      cleanWord:           '\(w.cleanWord)'")
            print("      parentheticalGloss:  '\(w.parentheticalGloss ?? "nil")'")
            print("      speechText:          '\(w.speechText)'")
            print("      acceptedSpellings:   \(w.acceptedSpellings)")
            print("")
        }
    }
}
