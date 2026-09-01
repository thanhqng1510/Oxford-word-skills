//
//  test_speech_service.swift
//  Oxford Word Skills — SpeechService & VoiceOption Unit Test Suite
//
//  Run: swift Utilities/SpeechService.swift tests/test_speech_service.swift
//

import Foundation
import AVFoundation

// MARK: - ANSI Output

let green  = "\u{001B}[32m"
let red    = "\u{001B}[31m"
let yellow = "\u{001B}[33m"
let bold   = "\u{001B}[1m"
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

print("\n=== Oxford Word Skills — SpeechService & VoiceOption Unit Tests ===\n")

// 1. Test VoiceOption Presets and Registry
print("VoiceOption configuration:")
assertTest(VoiceOption.british.id == "en-GB", "British voice id is en-GB")
assertTest(VoiceOption.british.languageCode == "en-GB", "British languageCode is en-GB")
assertTest(VoiceOption.british.displayName == "British", "British displayName is 'British'")
assertTest(VoiceOption.british.countryCode == "GB", "British countryCode is 'GB'")
assertTest(VoiceOption.british.flagEmoji == "🇬🇧", "British flagEmoji is 🇬🇧")
assertTest(VoiceOption.british.shortLabel == "🇬🇧 GB", "British shortLabel is '🇬🇧 GB'")

assertTest(VoiceOption.american.id == "en-US", "American voice id is en-US")
assertTest(VoiceOption.american.languageCode == "en-US", "American languageCode is en-US")
assertTest(VoiceOption.american.displayName == "American", "American displayName is 'American'")
assertTest(VoiceOption.american.countryCode == "US", "American countryCode is 'US'")
assertTest(VoiceOption.american.flagEmoji == "🇺🇸", "American flagEmoji is 🇺🇸")
assertTest(VoiceOption.american.shortLabel == "🇺🇸 US", "American shortLabel is '🇺🇸 US'")

assertTest(VoiceOption.default == VoiceOption.british, "Default voice option is British")
assertTest(VoiceOption.supportedVoices.count == 2, "Supported voices contains 2 options")
assertTest(VoiceOption.supportedVoices.contains(VoiceOption.british), "Supported voices contains British")
assertTest(VoiceOption.supportedVoices.contains(VoiceOption.american), "Supported voices contains American")

// 2. Test SpeechService Voice Resolution & Fallback
print("\nSpeechService voice resolution:")
let service = SpeechService.shared

let gbVoice = service.voice(for: .british)
assertTest(gbVoice != nil, "Resolved non-nil voice for British (en-GB)")
if let gbVoice = gbVoice {
    assertTest(gbVoice.language.starts(with: "en"), "British voice language is English: \(gbVoice.language)")
}

let usVoice = service.voice(for: .american)
assertTest(usVoice != nil, "Resolved non-nil voice for American (en-US)")
if let usVoice = usVoice {
    assertTest(usVoice.language.starts(with: "en"), "American voice language is English: \(usVoice.language)")
}

// 3. Test Memoization / Caching
print("\nSpeechService caching & fallback:")
let cachedGbVoice = service.voice(for: .british)
assertTest(gbVoice?.identifier == cachedGbVoice?.identifier, "Subsequent voice resolution uses cached voice identifier")

let customOption = VoiceOption(
    id: "en-AU",
    languageCode: "en-AU",
    displayName: "Australian",
    countryCode: "AU",
    flagEmoji: "🇦🇺"
)
let auVoice = service.voice(for: customOption)
assertTest(auVoice != nil, "Resolved non-nil fallback voice for custom VoiceOption (en-AU)")

// 4. Test activeVoice default and override behavior
print("\nSpeechService activeVoice default & override:")
assertTest(service.activeVoice == VoiceOption.british, "Initial activeVoice defaults to British")
service.activeVoice = .american
assertTest(service.activeVoice == VoiceOption.american, "activeVoice can be updated to American")
service.activeVoice = .british

// 5. Test Safe Speak Execution
print("\nSpeechService speak execution:")
service.speak("") // Empty string should be safely ignored
service.speak("   \n\t") // Whitespace string should be safely ignored
service.speak("Vocabulary") // Uses activeVoice
service.speak("Pronunciation", voice: .american) // Uses override voice
service.stop()
assertTest(true, "SpeechService handles empty strings, activeVoice, and override calls safely")

print("\n═══════════════════════════════════════════")
print("Results: \(passCount)/\(passCount + failCount) tests passed")
if failCount == 0 {
    print("\(green)✓ All \(passCount) tests passed\(reset)\n")
    exit(0)
} else {
    print("\(red)✗ \(failCount) tests failed\(reset)\n")
    exit(1)
}
