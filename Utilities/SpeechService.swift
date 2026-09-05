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
        refreshVoices()
        restorePersistedVoice()
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

    /// Selects a voice preference. Passing nil clears the selection.
    func selectVoice(_ voice: AppVoice?) {
        selectedVoice = voice
    }

    /// Pronounces text using the selected voice. If no voice is selected, this is a safe no-op.
    func speak(_ text: String) {
        guard canSpeak, let voice = selectedVoice else { return }
        let trimmed = text.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return }

        stop()
        guard let resolvedVoice = AVSpeechSynthesisVoice(identifier: voice.id) else { return }
        let utterance = AVSpeechUtterance(string: trimmed)
        utterance.voice = resolvedVoice
        utterance.rate = 0.45
        utterance.pitchMultiplier = 1.0
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
