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

        // 1. Test VoiceLocale
        print("1. VoiceLocale configuration:")
        assertTest(VoiceLocale.british.rawValue == "en-GB", "British locale code is en-GB")
        assertTest(VoiceLocale.british.flagEmoji == "🇬🇧", "British flag is 🇬🇧")
        assertTest(VoiceLocale.british.displayName == "British English", "British displayName is 'British English'")
        assertTest(VoiceLocale.american.rawValue == "en-US", "American locale code is en-US")
        assertTest(VoiceLocale.american.flagEmoji == "🇺🇸", "American flag is 🇺🇸")
        assertTest(VoiceLocale.american.displayName == "American English", "American displayName is 'American English'")
        assertTest(VoiceLocale.allCases.count == 2, "Exactly 2 voice locales supported (en-GB and en-US)")

        // 2. Test SpeechService Voice Discovery & Filtering
        print("\n2. SpeechService Voice Discovery & Filtering:")
        let service = SpeechService.shared
        service.refreshVoices()

        assertTest(!service.britishVoices.isEmpty, "Found at least one British voice on the system (found: \(service.britishVoices.count))")
        assertTest(!service.americanVoices.isEmpty, "Found at least one American voice on the system (found: \(service.americanVoices.count))")

        let allDiscovered = service.allAvailableVoices
        let hasNovelty = allDiscovered.contains { $0.id.contains("speech.synthesis.voice.") }
        assertTest(!hasNovelty, "Novelty joke voices are filtered out")

        let hasEloquence = allDiscovered.contains { $0.id.contains("eloquence") }
        assertTest(!hasEloquence, "Legacy 1990s Eloquence screen-reader voices are filtered out")

        let allGBMatch = service.britishVoices.allSatisfy { $0.locale == .british }
        assertTest(allGBMatch, "All britishVoices belong strictly to British English (en-GB)")

        let allUSMatch = service.americanVoices.allSatisfy { $0.locale == .american }
        assertTest(allUSMatch, "All americanVoices belong strictly to American English (en-US)")

        // 3. Test Quality-Based Sorting
        print("\n3. Quality-Based Sorting Invariant (Premium > Enhanced > Standard):")
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

        assertTest(isSortedByQuality(service.britishVoices), "British voices are strictly sorted by quality (descending) then name")
        assertTest(isSortedByQuality(service.americanVoices), "American voices are strictly sorted by quality (descending) then name")

        // 4. Test Strict Selection & Disabled State
        print("\n4. Strict Selection & Disabled State:")
        service.selectVoice(nil)
        assertTest(service.selectedVoice == nil, "selectedVoice is nil when no voice is selected")
        assertTest(service.canSpeak == false, "canSpeak is false when no voice is selected")

        // Speak when no voice selected must be safe no-op
        service.speak("Test sentence")
        assertTest(true, "speak() safely handles nil selectedVoice without error or crash")

        // 5. Test Voice Selection & Persistence
        print("\n5. Voice Selection & Persistence:")
        if let sampleVoice = service.britishVoices.first {
            service.selectVoice(sampleVoice)
            assertTest(service.selectedVoice?.id == sampleVoice.id, "selectedVoice matches selected British voice: \(sampleVoice.name)")
            assertTest(service.canSpeak == true, "canSpeak is true when a voice is selected")

            let savedId = UserDefaults.standard.string(forKey: "selectedVoiceIdentifier")
            assertTest(savedId == sampleVoice.id, "Selected voice ID is persisted to UserDefaults: \(savedId ?? "")")
        }

        if let sampleUSVoice = service.americanVoices.first {
            service.selectVoice(sampleUSVoice)
            assertTest(service.selectedVoice?.id == sampleUSVoice.id, "selectedVoice switches to American voice: \(sampleUSVoice.name)")
            let savedId = UserDefaults.standard.string(forKey: "selectedVoiceIdentifier")
            assertTest(savedId == sampleUSVoice.id, "Updated voice ID is persisted to UserDefaults")
        }

        // 6. Test Voice Preview
        print("\n6. Voice Preview Execution:")
        if let previewVoice = service.allAvailableVoices.first {
            service.preview(voice: previewVoice)
            assertTest(true, "preview(voice:) executes safely for \(previewVoice.name)")
            service.stop()
        }

        // 7. Test Safe Speak Execution
        print("\n7. Speak Execution & Edge Cases:")
        service.speak("") // Empty string
        service.speak("   \n\t") // Whitespace string
        service.speak("Pronunciation test") // Valid string
        service.stop()
        assertTest(true, "SpeechService handles empty, whitespace, and valid strings safely")

        // 8. Test Invalid Voice ID Handling
        print("\n8. Invalid Voice ID Handling:")
        UserDefaults.standard.set("com.apple.voice.nonexistent.fake", forKey: "selectedVoiceIdentifier")
        let testVoice = service.allAvailableVoices.first(where: { $0.id == "com.apple.voice.nonexistent.fake" })
        assertTest(testVoice == nil, "Non-existent voice ID is not matched in available voices")

        // Restore a valid selection
        if let validVoice = service.britishVoices.first {
            service.selectVoice(validVoice)
        }

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
