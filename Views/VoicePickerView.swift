//
//  VoicePickerView.swift
//  Oxford Word Skills
//

import SwiftUI
import AVFoundation

struct VoicePickerView: View {
    @Bindable var speechService: SpeechService
    @Binding var isPresented: Bool
    @Environment(\.openURL) private var openURL

    var body: some View {
        VStack(spacing: 0) {
            // Header with System Settings deep-link
            HStack {
                Text("Pronunciation Voice")
                    .font(.headline)
                Spacer()
                Button {
                    if let url = URL(string: "x-apple.systempreferences:com.apple.preference.universalaccess?SpokenContent") {
                        openURL(url)
                    }
                } label: {
                    HStack(spacing: 4) {
                        Image(systemName: "arrow.down.circle")
                        Text("Download Voices…")
                    }
                    .font(.caption)
                }
                .buttonStyle(.link)
            }
            .padding(.horizontal, 16)
            .padding(.vertical, 12)

            Divider()

            ScrollView {
                VStack(alignment: .leading, spacing: 14) {
                    voiceSection(
                        title: "British English",
                        flag: "🇬🇧",
                        voices: speechService.britishVoices
                    )

                    Divider()

                    voiceSection(
                        title: "American English",
                        flag: "🇺🇸",
                        voices: speechService.americanVoices
                    )
                }
                .padding(.horizontal, 14)
                .padding(.vertical, 12)
            }
            .frame(maxHeight: 360)
        }
        .frame(width: 320)
        .onAppear {
            speechService.refreshVoices()
        }
        .onReceive(NotificationCenter.default.publisher(for: NSApplication.didBecomeActiveNotification)) { _ in
            speechService.refreshVoices()
        }
    }

    @ViewBuilder
    private func voiceSection(title: String, flag: String, voices: [AppVoice]) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack(spacing: 6) {
                Text(flag)
                Text(title)
                    .font(.subheadline)
                    .fontWeight(.semibold)
                    .foregroundStyle(.secondary)
            }

            if voices.isEmpty {
                Text("No voices installed for this accent.")
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .padding(.vertical, 4)
            } else {
                VStack(spacing: 4) {
                    ForEach(voices) { voice in
                        voiceRow(voice)
                    }
                }
            }
        }
    }

    @ViewBuilder
    private func voiceRow(_ voice: AppVoice) -> some View {
        let isSelected = speechService.selectedVoice?.id == voice.id

        HStack(spacing: 8) {
            Button {
                if isSelected {
                    speechService.selectVoice(nil)
                } else {
                    speechService.selectVoice(voice)
                    isPresented = false
                }
            } label: {
                HStack(spacing: 8) {
                    Image(systemName: isSelected ? "checkmark.circle.fill" : "circle")
                        .foregroundStyle(isSelected ? AnyShapeStyle(.tint) : AnyShapeStyle(.secondary))
                        .font(.system(size: 14, weight: .medium))

                    Text(voice.name)
                        .font(.body)
                        .fontWeight(isSelected ? .semibold : .regular)

                    Spacer()

                    badgeView(for: voice.quality)
                }
                .contentShape(Rectangle())
            }
            .buttonStyle(.plain)

            Button {
                speechService.preview(voice: voice)
            } label: {
                Image(systemName: "speaker.wave.2.circle.fill")
                    .font(.title3)
                    .foregroundStyle(.tint)
            }
            .buttonStyle(.plain)
            .help("Preview pronunciation with this voice")
        }
        .padding(.horizontal, 10)
        .padding(.vertical, 6)
        .background(
            RoundedRectangle(cornerRadius: 8)
                .fill(isSelected ? AnyShapeStyle(.tint.opacity(0.1)) : AnyShapeStyle(.clear))
        )
    }

    @ViewBuilder
    private func badgeView(for quality: AVSpeechSynthesisVoiceQuality) -> some View {
        switch quality {
        case .premium:
            Text("Premium ✨")
                .font(.caption2)
                .fontWeight(.medium)
                .padding(.horizontal, 6)
                .padding(.vertical, 2)
                .background(.tint.opacity(0.18), in: Capsule())
                .foregroundStyle(.tint)
        case .enhanced:
            Text("Enhanced ⭐️")
                .font(.caption2)
                .fontWeight(.medium)
                .padding(.horizontal, 6)
                .padding(.vertical, 2)
                .background(.secondary.opacity(0.15), in: Capsule())
                .foregroundStyle(.primary)
        default:
            Text("Standard")
                .font(.caption2)
                .padding(.horizontal, 6)
                .padding(.vertical, 2)
                .background(.secondary.opacity(0.12), in: Capsule())
                .foregroundStyle(.secondary)
        }
    }
}
