import AVFoundation

/// Represents a configurable pronunciation voice option.
struct VoiceOption: Identifiable, Hashable, Codable {
    let id: String           // Unique identifier e.g. "en-GB"
    let languageCode: String // BCP-47 language tag e.g. "en-GB"
    let displayName: String  // User-facing name e.g. "British"
    let countryCode: String  // 2-letter region e.g. "GB"
    let flagEmoji: String    // Regional flag emoji e.g. "🇬🇧"

    var shortLabel: String {
        "\(flagEmoji) \(countryCode)"
    }

    static let british = VoiceOption(
        id: "en-GB",
        languageCode: "en-GB",
        displayName: "British",
        countryCode: "GB",
        flagEmoji: "🇬🇧"
    )

    static let american = VoiceOption(
        id: "en-US",
        languageCode: "en-US",
        displayName: "American",
        countryCode: "US",
        flagEmoji: "🇺🇸"
    )

    /// Pre-configured supported voice options.
    /// Additional accents can be added here seamlessly without changing UI or engine logic.
    static let supportedVoices: [VoiceOption] = [
        .british,
        .american
    ]

    static let `default` = british
}

final class SpeechService {
    static let shared = SpeechService()
    private let synthesizer = AVSpeechSynthesizer()
    private var voiceCache: [String: AVSpeechSynthesisVoice] = [:]

    /// Active voice selected by the user state.
    var activeVoice: VoiceOption = .default

    private init() {
        populateInitialVoices()
    }

    private func populateInitialVoices() {
        let systemVoices = AVSpeechSynthesisVoice.speechVoices()
        for option in VoiceOption.supportedVoices {
            if let best = systemVoices
                .filter({ $0.language == option.languageCode })
                .max(by: { $0.quality.rawValue < $1.quality.rawValue }) {
                voiceCache[option.id] = best
            }
        }
    }

    /// Resolves the highest-quality synthesis voice for the requested voice option with a multi-tier fallback chain.
    func voice(for option: VoiceOption) -> AVSpeechSynthesisVoice? {
        // 1. Cached high-quality system voice
        if let cached = voiceCache[option.id] {
            return cached
        }
        // 2. Language-code synthesized voice
        if let fallback = AVSpeechSynthesisVoice(language: option.languageCode) {
            voiceCache[option.id] = fallback
            return fallback
        }
        // 3. Fallback to default voice
        if option.id != VoiceOption.default.id, let defaultVoice = voice(for: .default) {
            return defaultVoice
        }
        // 4. System English fallback
        return AVSpeechSynthesisVoice(language: "en-GB") ?? AVSpeechSynthesisVoice(language: "en-US")
    }

    /// Pronounces text using the active voice from state, or an optional override voice if specified.
    func speak(_ text: String, voice overrideVoice: VoiceOption? = nil) {
        let trimmed = text.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return }

        stop()
        let utterance = AVSpeechUtterance(string: trimmed)
        let targetVoice = overrideVoice ?? activeVoice
        if let resolvedVoice = voice(for: targetVoice) {
            utterance.voice = resolvedVoice
        }
        utterance.rate = 0.45
        utterance.pitchMultiplier = 1.0
        synthesizer.speak(utterance)
    }

    func stop() {
        if synthesizer.isSpeaking {
            synthesizer.stopSpeaking(at: .immediate)
        }
    }
}
