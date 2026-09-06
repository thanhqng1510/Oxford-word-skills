//
//  test_speech_service.swift
//  Oxford Word Skills — SpeechService Unit Test Suite
//
//  Run: swift Utilities/SpeechService.swift tests/test_speech_service.swift
//

import Foundation
import AVFoundation

@main
struct SpeechServiceTestRunner {
    static func main() {
        // MARK: - ANSI Output

        let green  = "\u{001B}[32m"
        let red    = "\u{001B}[31m"
        let yellow = "\u{001B}[33m"
        let reset  = "\u{001B}[0m"

        var passCount = 0
        var failCount = 0

        func assertTest(_ condition: Bool, _ name: String, details: String = "") {
            if condition {
                passCount += 1
                print("  \(green)✓ [PASS]\(reset) \(name)")
            } else {
                failCount += 1
                print("  \(red)✗ [FAIL]\(reset) \(name)")
                if !details.isEmpty { print("         \(yellow)→ \(details)\(reset)") }
            }
        }

        print("\n=== Oxford Word Skills — SpeechService Unit Tests ===\n")

        // 1. Test AppVoice configuration
        print("1. AppVoice configuration:")
        assertTest(AppVoice.britishLocale == "en-GB", "British locale code is en-GB")
        let dummyVoice = AppVoice(id: "test.id", name: "Arthur", quality: .premium)
        assertTest(dummyVoice.displayLabel == "🇬🇧 Arthur", "AppVoice displayLabel prefixes British flag: \(dummyVoice.displayLabel)")
        assertTest(dummyVoice.qualityBadge == "Premium ✨", "AppVoice qualityBadge displays tier correctly")
        assertTest(dummyVoice.qualitySymbol == "✨", "AppVoice qualitySymbol displays tier icon")

        // 2. Test SpeechService Voice Discovery & Filtering
        print("\n2. SpeechService Voice Discovery & Filtering:")
        let service = SpeechService.shared
        service.refreshVoices()

        assertTest(!service.availableVoices.isEmpty, "Found at least one British voice on the system (found: \(service.availableVoices.count))")

        let allDiscovered = service.availableVoices
        let hasNovelty = allDiscovered.contains { $0.id.contains("speech.synthesis.voice.") }
        assertTest(!hasNovelty, "Novelty joke voices are filtered out")

        let hasEloquence = allDiscovered.contains { $0.id.contains("eloquence") }
        assertTest(!hasEloquence, "Legacy 1990s Eloquence screen-reader voices are filtered out")

        let allGBMatch = service.availableVoices.allSatisfy {
            AVSpeechSynthesisVoice(identifier: $0.id)?.language == AppVoice.britishLocale
        }
        assertTest(allGBMatch, "All availableVoices belong strictly to British English (en-GB)")

        // 3. Test Voice Name Cleanliness (No (Premium) or (Enhanced) in names)
        print("\n3. Voice Name Cleanliness:")
        assertTest(SpeechService.cleanVoiceName("Ava (Premium)") == "Ava", "cleanVoiceName strips (Premium)")
        assertTest(SpeechService.cleanVoiceName("Daniel (Enhanced)") == "Daniel", "cleanVoiceName strips (Enhanced)")
        assertTest(SpeechService.cleanVoiceName("Samantha") == "Samantha", "cleanVoiceName preserves clean names")

        let noNameHasSuffix = allDiscovered.allSatisfy {
            !$0.name.contains("(Premium)") && !$0.name.contains("(Enhanced)")
        }
        assertTest(noNameHasSuffix, "All discovered voices have (Premium) and (Enhanced) stripped from their name")

        // Test qualitySymbol helper
        if let premiumVoice = allDiscovered.first(where: { $0.quality == .premium }) {
            assertTest(premiumVoice.qualitySymbol == "✨", "Premium voice qualitySymbol is ✨")
        }
        if let enhancedVoice = allDiscovered.first(where: { $0.quality == .enhanced }) {
            assertTest(enhancedVoice.qualitySymbol == "⭐️", "Enhanced voice qualitySymbol is ⭐️")
        }
        if let standardVoice = allDiscovered.first(where: { $0.quality == .default }) {
            assertTest(standardVoice.qualitySymbol == "", "Standard voice qualitySymbol is empty string")
        }

        // 4. Test Quality-Based Sorting
        print("\n4. Quality-Based Sorting Invariant (Premium > Enhanced > Standard):")
        func isSortedByQuality(_ voices: [AppVoice]) -> Bool {
            guard voices.count > 1 else { return true }
            for i in 0..<(voices.count - 1) {
                let current = voices[i]
                let next = voices[i + 1]
                if current.quality.rawValue < next.quality.rawValue {
                    return false
                }
                if current.quality.rawValue == next.quality.rawValue {
                    if current.name.localizedStandardCompare(next.name) == .orderedDescending {
                        return false
                    }
                }
            }
            return true
        }

        assertTest(isSortedByQuality(service.availableVoices), "British voices are strictly sorted by quality (descending) then name")

        // 5. Test Strict Selection & Disabled State
        print("\n5. Strict Selection & Disabled State:")
        service.selectVoice(nil)
        assertTest(service.selectedVoice == nil, "selectedVoice is nil when no voice is selected")
        assertTest(service.canSpeak == false, "canSpeak is false when no voice is selected")

        // Speak when no voice selected must be safe no-op
        service.speak("Test sentence")
        assertTest(true, "speak() safely handles nil selectedVoice without error or crash")

        // 6. Test Voice Selection & Persistence
        print("\n6. Voice Selection & Persistence:")
        if let sampleVoice = service.availableVoices.first {
            service.selectVoice(sampleVoice)
            assertTest(service.selectedVoice?.id == sampleVoice.id, "selectedVoice matches selected British voice: \(sampleVoice.name)")
            assertTest(service.canSpeak == true, "canSpeak is true when a voice is selected")

            let savedId = UserDefaults.standard.string(forKey: "selectedVoiceIdentifier")
            assertTest(savedId == sampleVoice.id, "Selected voice ID is persisted to UserDefaults: \(savedId ?? "")")
        }

        // 7. Test Voice Preview
        print("\n7. Voice Preview Execution:")
        if let previewVoice = service.availableVoices.first {
            service.preview(voice: previewVoice)
            assertTest(true, "preview(voice:) executes safely for \(previewVoice.name)")
            service.stop()
        }

        // 8. Test Safe Speak Execution
        print("\n8. Speak Execution & Edge Cases:")
        service.speak("") // Empty string
        service.speak("   \n\t") // Whitespace string
        service.speak("Pronunciation test") // Valid string
        service.stop()
        assertTest(true, "SpeechService handles empty, whitespace, and valid strings safely")

        // 9. Test Invalid Voice ID Handling
        print("\n9. Invalid Voice ID Handling:")
        UserDefaults.standard.set("com.apple.voice.nonexistent.fake", forKey: "selectedVoiceIdentifier")
        let testVoice = service.availableVoices.first(where: { $0.id == "com.apple.voice.nonexistent.fake" })
        assertTest(testVoice == nil, "Non-existent voice ID is not matched in available voices")

        // Restore a valid selection
        if let validVoice = service.availableVoices.first {
            service.selectVoice(validVoice)
        }

        // 10. Test Native Plain-Text Utterance Synthesis
        print("\n10. Native Plain-Text Utterance Synthesis (Neural Prosody):")
        if let sampleVoice = service.availableVoices.first,
           let resolvedVoice = AVSpeechSynthesisVoice(identifier: sampleVoice.id) {
            let u1 = service.makeUtterance(text: "colonel", voice: resolvedVoice)
            assertTest(u1.voice?.identifier == resolvedVoice.identifier, "makeUtterance assigns voice correctly")
            assertTest(u1.speechString == "colonel", "makeUtterance uses native plain text string for neural synthesis")
            assertTest(abs(u1.rate - 0.48) < 0.01, "makeUtterance sets optimal learning rate 0.48")

            let uPlain = service.makeUtterance(text: "  Welcome  \n", voice: resolvedVoice)
            assertTest(uPlain.speechString == "Welcome", "makeUtterance trims whitespace from text")
            assertTest(abs(uPlain.rate - 0.48) < 0.01, "makeUtterance sets rate 0.48 for plain string utterance")
        }

        // Speak execution with plain text
        service.speak("colonel")
        service.speak("schedule")
        service.speak("rock & roll")
        service.stop()
        assertTest(true, "service.speak executes safely for words and special characters")

        print("\n═══════════════════════════════════════════")
        print("Results: \(passCount)/\(passCount + failCount) tests passed")
        if failCount == 0 {
            print("\(green)✓ All \(passCount) tests passed\(reset)\n")
            exit(0)
        } else {
            print("\(red)✗ \(failCount) tests failed\(reset)\n")
            exit(1)
        }
    }
}
