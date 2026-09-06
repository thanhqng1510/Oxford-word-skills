import AVFoundation

/// Supported language locales for vocabulary pronunciation.
enum VoiceLocale: String, Codable, CaseIterable, Identifiable {
    case british = "en-GB"
    case american = "en-US"

    var id: String { rawValue }

    var displayName: String {
        switch self {
        case .british: return "British English"
        case .american: return "American English"
        }
    }

    var shortLabel: String {
        switch self {
        case .british: return "🇬🇧 GB"
        case .american: return "🇺🇸 US"
        }
    }

    var flagEmoji: String {
        switch self {
        case .british: return "🇬🇧"
        case .american: return "🇺🇸"
        }
    }
}

/// Represents a concrete installed system voice with its quality tier and metadata.
struct AppVoice: Identifiable, Hashable {
    let id: String
    let name: String
    let locale: VoiceLocale
    let quality: AVSpeechSynthesisVoiceQuality

    var qualityBadge: String {
        switch quality {
        case .premium: return "Premium ✨"
        case .enhanced: return "Enhanced ⭐️"
        default: return "Standard"
        }
    }

    var qualitySymbol: String {
        switch quality {
        case .premium: return "✨"
        case .enhanced: return "⭐️"
        default: return ""
        }
    }

    var displayLabel: String {
        "\(locale.flagEmoji) \(name)"
    }
}

@Observable
final class SpeechService {
    static let shared = SpeechService()
    static let previewSentence = "Welcome to Oxford Word Skills. Expand your vocabulary and master English pronunciation with confidence."

    /// Cleans macOS system voice names by stripping redundant quality suffixes like (Premium) or (Enhanced).
    static func cleanVoiceName(_ rawName: String) -> String {
        rawName
            .replacingOccurrences(of: "(Premium)", with: "", options: .caseInsensitive)
            .replacingOccurrences(of: "(Enhanced)", with: "", options: .caseInsensitive)
            .trimmingCharacters(in: .whitespaces)
    }

    private let synthesizer = AVSpeechSynthesizer()
    private let voicePrefKey = "selectedVoiceIdentifier"

    /// Installed voices sorted by quality: Premium -> Enhanced -> Standard.
    private(set) var britishVoices: [AppVoice] = []
    private(set) var americanVoices: [AppVoice] = []

    /// All available installed voices across supported accents.
    var allAvailableVoices: [AppVoice] {
        britishVoices + americanVoices
    }

    /// User's currently selected voice. If nil, pronunciation is disabled.
    private(set) var selectedVoice: AppVoice? {
        didSet {
            if let selectedVoice {
                UserDefaults.standard.set(selectedVoice.id, forKey: voicePrefKey)
            } else {
                UserDefaults.standard.removeObject(forKey: voicePrefKey)
            }
        }
    }

    /// True only if a valid voice has been explicitly chosen by the user.
    var canSpeak: Bool {
        selectedVoice != nil
    }

    private init() {
        primeSynthesizerLocale()
        refreshVoices()
        restorePersistedVoice()
    }

    /// Primes AVSpeechSynthesizer with en-GB to ensure internal phoneme tables load correctly (Apple Radar FB9688443).
    private func primeSynthesizerLocale() {
        let preferred = Locale.preferredLanguages
        if preferred.first != "en-GB" {
            let prefKey = "AppleLanguages"
            UserDefaults.standard.set(["en-GB"], forKey: prefKey)
            synthesizer.speak(AVSpeechUtterance(string: ""))
            synthesizer.stopSpeaking(at: .immediate)
            UserDefaults.standard.set(preferred, forKey: prefKey)
        }
    }

    /// Restores the saved voice identifier from UserDefaults if it matches an installed voice.
    private func restorePersistedVoice() {
        if let savedId = UserDefaults.standard.string(forKey: voicePrefKey),
           let matched = allAvailableVoices.first(where: { $0.id == savedId }) {
            self.selectedVoice = matched
        } else {
            self.selectedVoice = nil
        }
    }

    /// Scans installed voices, filters for en-GB and en-US, and sorts by quality (Premium > Enhanced > Standard).
    func refreshVoices() {
        let allVoices = AVSpeechSynthesisVoice.speechVoices()

        func processVoices(for locale: VoiceLocale) -> [AppVoice] {
            let matching = allVoices.filter { $0.language == locale.rawValue }

            // Filter out novelty voices and legacy 1990s Eloquence screen-readers
            let filtered = matching.filter { voice in
                if voice.identifier.contains("speech.synthesis.voice.") { return false }
                if voice.identifier.contains("eloquence") { return false }
                // De-duplicate super-compact if compact or higher quality is available
                if voice.identifier.contains("super-compact") {
                    let hasBetter = matching.contains {
                        $0.name == voice.name && !$0.identifier.contains("super-compact")
                    }
                    if hasBetter { return false }
                }
                return true
            }

            // Sort by quality descending (3 -> 2 -> 1), then by name ascending
            let sorted = filtered.sorted { v1, v2 in
                if v1.quality.rawValue != v2.quality.rawValue {
                    return v1.quality.rawValue > v2.quality.rawValue
                }
                let clean1 = SpeechService.cleanVoiceName(v1.name)
                let clean2 = SpeechService.cleanVoiceName(v2.name)
                return clean1.localizedStandardCompare(clean2) == .orderedAscending
            }

            return sorted.map { voice in
                AppVoice(
                    id: voice.identifier,
                    name: SpeechService.cleanVoiceName(voice.name),
                    locale: locale,
                    quality: voice.quality
                )
            }
        }

        britishVoices = processVoices(for: .british)
        americanVoices = processVoices(for: .american)

        // Validate that currently selected voice is still installed
        if let current = selectedVoice {
            if let updated = allAvailableVoices.first(where: { $0.id == current.id }) {
                selectedVoice = updated
            } else {
                selectedVoice = nil
            }
        }
    }

    /// Unicode dash variants mapped to syllable separators.
    private static let dashCharacters = [
        "\u{002D}", // hyphen-minus
        "\u{2010}", // hyphen
        "\u{2011}", // non-breaking hyphen
        "\u{2012}", // figure dash
        "\u{2013}", // en dash
        "\u{2014}", // em dash
        "\u{2212}"  // minus sign
    ]

    /// Legacy compatibility alias for cleanIPAString.
    static func cleanIPAString(_ rawIPA: String) -> String {
        adjustIPAForApple(rawIPA)
    }

    /// Tunes raw dictionary IPA specifically for Apple's speech synthesis engine:
    /// - Normalizes dashes to syllable dots
    /// - Replaces unsupported secondary stress ˌ with primary stress ˈ
    /// - Adds combining tie bars to affricates (tʃ → t͡ʃ, dʒ → d͡ʒ)
    /// - Normalizes long vowels (iː, uː, ɑː, ɔː, ɜː) that Apple TTS elongates unnaturally
    /// - Resolves non-rhotic (r) and dictionary parentheses
    static func adjustIPAForApple(_ rawIPA: String) -> String {
        var ipa = rawIPA
            .replacingOccurrences(of: "\u{00A0}", with: " ")
            .trimmingCharacters(in: CharacterSet(charactersIn: "/[] \t\r\n"))

        guard !ipa.isEmpty else { return "" }

        // 1. Remove non-rhotic linking (r) for isolation pronunciation
        ipa = ipa.replacingOccurrences(of: "(r)", with: "")

        // 2. Yod-dropping after l: l(j) -> l (e.g. absolutely)
        ipa = ipa.replacingOccurrences(of: "l(j)", with: "l")

        // 3. Strip remaining dictionary parentheses
        ipa = ipa.replacingOccurrences(of: "(", with: "")
                 .replacingOccurrences(of: ")", with: "")

        // 4. Convert all Unicode dash types to syllable dots
        for dash in dashCharacters {
            ipa = ipa.replacingOccurrences(of: dash, with: ".")
        }

        // 5. Replace secondary stress with primary stress (secondary not supported by Apple TTS)
        ipa = ipa.replacingOccurrences(of: "ˌ", with: "ˈ")

        // 6. Tie affricates so Apple TTS does not pronounce separate consonants (e.g. chance, bridge)
        ipa = ipa.replacingOccurrences(of: "t͡ʃ", with: "tʃ")
                 .replacingOccurrences(of: "d͡ʒ", with: "dʒ")
        ipa = ipa.replacingOccurrences(of: "tʃ", with: "t͡ʃ")
                 .replacingOccurrences(of: "dʒ", with: "d͡ʒ")

        // 7. Simplify long vowels that Apple TTS elongates into robotic drones
        ipa = ipa.replacingOccurrences(of: "iː", with: "i")
                 .replacingOccurrences(of: "uː", with: "u")
                 .replacingOccurrences(of: "ɑː", with: "ɑ")
                 .replacingOccurrences(of: "ɔː", with: "ɔ")
                 .replacingOccurrences(of: "ɜː", with: "ɜ")
                 .replacingOccurrences(of: "eː", with: "e͡ɪ")
                 .replacingOccurrences(of: "oː", with: "o͡ʊ")
                 .replacingOccurrences(of: "æː", with: "æ")
                 .replacingOccurrences(of: "ː", with: "")
                 .replacingOccurrences(of: ":", with: "")

        // 8. Clean up consecutive punctuation and stresses
        while ipa.contains("..") {
            ipa = ipa.replacingOccurrences(of: "..", with: ".")
        }
        while ipa.contains("ˈˈ") {
            ipa = ipa.replacingOccurrences(of: "ˈˈ", with: "ˈ")
        }
        ipa = ipa.replacingOccurrences(of: ".ˈ", with: "ˈ")
                 .replacingOccurrences(of: "ˈ.", with: "ˈ")

        return ipa.trimmingCharacters(in: CharacterSet(charactersIn: "."))
    }

    /// Creates an AVSpeechUtterance, prioritizing tuned Apple IPA notation if available, or falling back to plain text.
    func makeUtterance(text: String, ipa: String?, voice: AVSpeechSynthesisVoice) -> AVSpeechUtterance {
        let trimmedText = text.trimmingCharacters(in: .whitespacesAndNewlines)
        let tunedIPA = ipa.map(Self.adjustIPAForApple) ?? ""

        let utterance: AVSpeechUtterance
        if !tunedIPA.isEmpty {
            let attrStr = NSMutableAttributedString(string: trimmedText)
            let ipaKey = NSAttributedString.Key(rawValue: AVSpeechSynthesisIPANotationAttribute)
            attrStr.addAttribute(ipaKey, value: tunedIPA, range: NSRange(location: 0, length: trimmedText.utf16.count))
            utterance = AVSpeechUtterance(attributedString: attrStr)
        } else {
            utterance = AVSpeechUtterance(string: trimmedText)
        }

        utterance.voice = voice
        utterance.rate = 0.45
        utterance.pitchMultiplier = 1.0
        return utterance
    }

    /// Selects a voice preference. Passing nil clears the selection.
    func selectVoice(_ voice: AppVoice?) {
        selectedVoice = voice
    }

    /// Pronounces text using the selected voice. If an IPA string is provided, synthesizes using native IPA notation.
    func speak(_ text: String, ipa: String? = nil) {
        guard canSpeak, let voice = selectedVoice else { return }
        let trimmed = text.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return }

        stop()
        guard let resolvedVoice = AVSpeechSynthesisVoice(identifier: voice.id) else { return }
        let utterance = makeUtterance(text: trimmed, ipa: ipa, voice: resolvedVoice)
        synthesizer.speak(utterance)
    }

    /// Plays a sample audio preview using a specific voice.
    func preview(voice: AppVoice) {
        stop()
        guard let resolvedVoice = AVSpeechSynthesisVoice(identifier: voice.id) else { return }
        let utterance = AVSpeechUtterance(string: Self.previewSentence)
        utterance.voice = resolvedVoice
        utterance.rate = 0.45
        synthesizer.speak(utterance)
    }

    /// Stops any in-progress speech playback.
    func stop() {
        if synthesizer.isSpeaking {
            synthesizer.stopSpeaking(at: .immediate)
        }
    }
}
