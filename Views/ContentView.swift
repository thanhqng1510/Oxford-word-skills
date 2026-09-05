import SwiftUI
import AVFoundation

struct ContentView: View {
    @State private var viewModel = ContentViewModel()
    @State private var speechService = SpeechService.shared
    @State private var columnVisibility = NavigationSplitViewVisibility.automatic
    var updateService: UpdateService

    @State private var showingVoicePicker = false

    var body: some View {
        NavigationSplitView(columnVisibility: $columnVisibility) {
            SidebarView(viewModel: viewModel)
        } detail: {
            DetailView(viewModel: viewModel)
        }
        .navigationTitle("Oxford Word Skills")
        .frame(minWidth: 900, minHeight: 600)
        .toolbar {
            ToolbarItem(placement: .primaryAction) {
                Button {
                    showingVoicePicker.toggle()
                } label: {
                    HStack(spacing: 6) {
                        if let selected = speechService.selectedVoice {
                            Image(systemName: "speaker.wave.2.fill")
                                .foregroundStyle(.blue)
                            Text(selected.displayLabel)
                                .font(.callout)
                            Text(selected.qualityBadge)
                                .font(.caption2)
                                .padding(.horizontal, 6)
                                .padding(.vertical, 2)
                                .background(.blue.opacity(0.12), in: Capsule())
                        } else {
                            Image(systemName: "speaker.slash.fill")
                                .foregroundStyle(.orange)
                            Text("No Voice Selected")
                                .font(.callout)
                                .foregroundStyle(.secondary)
                        }
                    }
                }
                .popover(isPresented: $showingVoicePicker, arrowEdge: .bottom) {
                    VoicePickerPopover(
                        speechService: speechService,
                        isPresented: $showingVoicePicker
                    )
                }
                .help(speechService.canSpeak ? "Change pronunciation voice" : "Select a voice to enable pronunciation")
            }
        }
        // ── Auto-update ──────────────────────────────────────────────────────
        // Check for a newer release 2 s after launch (avoids blocking startup)
        .task {
            try? await Task.sleep(for: .seconds(2))
            await updateService.checkOnLaunch()
        }
        // Present the update sheet when a newer version is found
        .sheet(isPresented: Bindable(updateService).showingUpdateSheet) {
            UpdateAvailableView(service: updateService)
        }
        // "Already up to date" alert for manual checks
        .alert(
            "You're Up to Date",
            isPresented: Bindable(updateService).showingAlreadyLatestAlert
        ) {
            Button("OK") { }
        } message: {
            Text("Oxford Word Skills is already on the latest version.")
        }
    }
}

struct DetailView: View {
    @Bindable var viewModel: ContentViewModel

    var body: some View {
        Group {
            switch viewModel.selectedNavigation {
            case .allWords:
                VocabularyListView(viewModel: viewModel)
            case .unit(let unitNumber):
                UnitDetailView(viewModel: viewModel, unitNumber: unitNumber)
            case .exercise(let type, let unitNumber):
                ExerciseContainerView(viewModel: viewModel, exerciseType: type, unitNumber: unitNumber)
            case .progress:
                ProgressDashboardView(viewModel: viewModel)
            }
        }
        .searchable(text: $viewModel.searchText, prompt: "Search words or definitions...")
    }
}

struct VoicePickerPopover: View {
    @Bindable var speechService: SpeechService
    @Binding var isPresented: Bool

    var body: some View {
        VStack(spacing: 0) {
            // Header
            VStack(alignment: .leading, spacing: 6) {
                HStack {
                    Text("Pronunciation Voice")
                        .font(.headline)
                    Spacer()
                    Button {
                        speechService.openSystemVoiceSettings()
                    } label: {
                        HStack(spacing: 4) {
                            Image(systemName: "arrow.down.circle")
                            Text("Download More Voices…")
                        }
                        .font(.caption)
                    }
                    .buttonStyle(.link)
                    .help("Open macOS Accessibility settings to download Enhanced and Premium voices")
                }

                Text("Choose a voice to enable pronunciation. Voices are sorted by quality.")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
            .padding()

            Divider()

            ScrollView {
                VStack(alignment: .leading, spacing: 16) {
                    voiceSection(
                        title: "British English",
                        flag: "🇬🇧",
                        voices: speechService.britishVoices
                    )

                    voiceSection(
                        title: "American English",
                        flag: "🇺🇸",
                        voices: speechService.americanVoices
                    )
                }
                .padding()
            }
            .frame(maxHeight: 360)

            Divider()

            // Footer
            HStack {
                Text("Newly downloaded voices in Settings appear automatically.")
                    .font(.caption2)
                    .foregroundStyle(.secondary)
                Spacer()
                Button("Done") {
                    isPresented = false
                }
                .buttonStyle(.bordered)
                .controlSize(.small)
            }
            .padding(.horizontal)
            .padding(.vertical, 8)
        }
        .frame(width: 440)
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
                speechService.selectVoice(voice)
            } label: {
                HStack(spacing: 8) {
                    Image(systemName: isSelected ? "checkmark.circle.fill" : "circle")
                        .foregroundStyle(isSelected ? Color.accentColor : Color.secondary)
                        .imageScale(.medium)

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
                    .foregroundStyle(Color.accentColor)
            }
            .buttonStyle(.plain)
            .help("Preview pronunciation with this voice")
        }
        .padding(.horizontal, 10)
        .padding(.vertical, 6)
        .background(
            RoundedRectangle(cornerRadius: 8)
                .fill(isSelected ? Color.accentColor.opacity(0.1) : Color.clear)
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
                .background(.purple.opacity(0.15), in: Capsule())
                .foregroundStyle(.purple)
        case .enhanced:
            Text("Enhanced ⭐️")
                .font(.caption2)
                .fontWeight(.medium)
                .padding(.horizontal, 6)
                .padding(.vertical, 2)
                .background(.blue.opacity(0.15), in: Capsule())
                .foregroundStyle(.blue)
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

