import SwiftUI

struct VocabularyListView: View {
    @Bindable var viewModel: ContentViewModel
    @State private var selectedWordForDetail: Word?

    var body: some View {
        Table(viewModel.filteredWords) {
            TableColumn("Word") { word in
                HStack(spacing: 6) {
                    Text(word.word)
                        .fontWeight(.medium)
                    Button {
                        SpeechService.shared.speak(word.speechText)
                    } label: {
                        Image(systemName: "speaker.wave.2")
                            .font(.caption)
                    }
                    .buttonStyle(.plain)
                    .help("Pronounce")
                }
            }
            .width(min: 120, ideal: 180)

            TableColumn("Pronunciation") { word in
                if !word.ipa.isEmpty {
                    Text(word.ipa)
                        .font(.system(.body, design: .serif))
                        .foregroundStyle(.secondary)
                }
            }
            .width(min: 110, ideal: 140)

            TableColumn("Definition") { word in
                HStack(spacing: 6) {
                    if let firstDef = word.definitions.first {
                        if !firstDef.partOfSpeech.isEmpty {
                            Text(firstDef.partOfSpeech)
                                .font(.caption2)
                                .fontWeight(.semibold)
                                .padding(.horizontal, 5)
                                .padding(.vertical, 1)
                                .background(.blue.opacity(0.12), in: Capsule())
                        }
                        Text(firstDef.definition)
                            .font(.caption)
                            .foregroundStyle(.secondary)
                            .lineLimit(2)
                    } else {
                        Text("No definition available")
                            .font(.caption)
                            .foregroundStyle(.tertiary)
                    }

                    if word.definitions.count > 1 {
                        Button {
                            selectedWordForDetail = word
                        } label: {
                            Text("+\(word.definitions.count - 1)")
                                .font(.caption2)
                                .fontWeight(.semibold)
                                .padding(.horizontal, 5)
                                .padding(.vertical, 2)
                                .background(.blue.opacity(0.15), in: Capsule())
                        }
                        .buttonStyle(.plain)
                        .help("View all \(word.definitions.count) meanings")
                    }

                    Spacer(minLength: 0)

                    Button {
                        selectedWordForDetail = word
                    } label: {
                        Image(systemName: "info.circle")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                    .buttonStyle(.plain)
                    .help("View full dictionary details")
                }
            }
            .width(min: 160, ideal: 280)

            TableColumn("Units") { word in
                Text(word.unitNumbers.map(String.init).joined(separator: ", "))
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
            .width(min: 60, ideal: 80)

            TableColumn("Learned") { word in
                Button {
                    viewModel.toggleLearned(word)
                } label: {
                    Image(systemName: viewModel.isLearned(word) ? "checkmark.circle.fill" : "circle")
                        .foregroundStyle(viewModel.isLearned(word) ? .green : .secondary)
                }
                .buttonStyle(.plain)
            }
            .width(60)
        }
        .sheet(item: $selectedWordForDetail) { word in
            WordDetailSheet(word: word, viewModel: viewModel)
        }
        .overlay {
            if viewModel.filteredWords.isEmpty {
                ContentUnavailableView.search
            }
        }
    }
}

struct UnitDetailView: View {
    @Bindable var viewModel: ContentViewModel
    let unitNumber: Int

    private var unit: Unit? {
        viewModel.currentUnit
    }

    var body: some View {
        VStack(spacing: 0) {
            if let unit = unit {
                UnitHeaderView(unit: unit, viewModel: viewModel)

                Divider()

                VocabularyListView(viewModel: viewModel)
            } else {
                ContentUnavailableView("Select a Unit", systemImage: "book.closed", description: Text("Choose a unit from the sidebar"))
            }
        }
    }
}

struct UnitHeaderView: View {
    let unit: Unit
    @Bindable var viewModel: ContentViewModel

    var body: some View {
        VStack(spacing: 8) {
            HStack {
                VStack(alignment: .leading) {
                    Text("Unit \(unit.number)")
                        .font(.title2)
                        .fontWeight(.bold)
                    Text(unit.title)
                        .font(.headline)
                        .foregroundStyle(.secondary)
                }
                Spacer()
                HStack(spacing: 12) {
                    ForEach(ExerciseType.allCases, id: \.self) { type in
                        Button {
                            viewModel.selectedNavigation = .exercise(type, unit.number)
                        } label: {
                            VStack(spacing: 4) {
                                Image(systemName: type.icon)
                                    .font(.title3)
                                Text(type.rawValue)
                                    .font(.caption2)
                            }
                            .frame(width: 70, height: 50)
                        }
                        .buttonStyle(.bordered)
                    }
                }
            }

            HStack {
                Text("\(unit.learnedCount) / \(unit.words.count) words learned")
                    .font(.callout)
                    .foregroundStyle(.secondary)
                ProgressView(value: unit.progress)
                    .frame(maxWidth: 120)
                Spacer()
                Button("Mark All Learned") {
                    viewModel.markAllLearned(in: unit.number)
                }
                .buttonStyle(.bordered)
                .controlSize(.small)
                Button("Reset") {
                    viewModel.resetProgress(for: unit.number)
                }
                .buttonStyle(.bordered)
                .controlSize(.small)
            }
        }
        .padding()
    }
}

struct WordDetailSheet: View {
    let word: Word
    @Bindable var viewModel: ContentViewModel
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        VStack(spacing: 0) {
            // Header
            HStack {
                VStack(alignment: .leading, spacing: 4) {
                    HStack(spacing: 8) {
                        Text(word.word)
                            .font(.title)
                            .fontWeight(.bold)
                        Button {
                            SpeechService.shared.speak(word.speechText)
                        } label: {
                            Image(systemName: "speaker.wave.2.fill")
                                .font(.title3)
                        }
                        .buttonStyle(.plain)
                        .help("Listen to British pronunciation")
                    }

                    if !word.ipa.isEmpty {
                        Text(word.ipa)
                            .font(.title3)
                            .foregroundStyle(.secondary)
                    }
                }

                Spacer()

                Button {
                    viewModel.toggleLearned(word)
                } label: {
                    Label(
                        viewModel.isLearned(word) ? "Learned" : "Mark Learned",
                        systemImage: viewModel.isLearned(word) ? "checkmark.circle.fill" : "circle"
                    )
                }
                .buttonStyle(.bordered)
                .tint(viewModel.isLearned(word) ? .green : .accentColor)

                Button("Done") {
                    dismiss()
                }
                .buttonStyle(.borderedProminent)
                .controlSize(.regular)
            }
            .padding()

            Divider()

            // Content
            ScrollView {
                VStack(alignment: .leading, spacing: 20) {
                    // Units
                    if !word.unitNumbers.isEmpty {
                        HStack(spacing: 6) {
                            Text("Units:")
                                .font(.headline)
                                .foregroundStyle(.secondary)
                            ForEach(word.unitNumbers, id: \.self) { u in
                                Text("Unit \(u)")
                                    .font(.caption)
                                    .padding(.horizontal, 8)
                                    .padding(.vertical, 3)
                                    .background(.secondary.opacity(0.12), in: Capsule())
                            }
                        }
                    }

                    // Meanings & Definitions
                    VStack(alignment: .leading, spacing: 12) {
                        Text("Definitions (\(word.definitions.count))")
                            .font(.headline)

                        ForEach(Array(word.definitions.enumerated()), id: \.offset) { idx, def in
                            VStack(alignment: .leading, spacing: 6) {
                                HStack(alignment: .top, spacing: 8) {
                                    Text("\(idx + 1).")
                                        .font(.subheadline)
                                        .fontWeight(.bold)
                                        .foregroundStyle(.secondary)

                                    if !def.partOfSpeech.isEmpty {
                                        Text(def.partOfSpeech)
                                            .font(.caption)
                                            .fontWeight(.semibold)
                                            .padding(.horizontal, 8)
                                            .padding(.vertical, 2)
                                            .background(.blue.opacity(0.15), in: Capsule())
                                    }

                                    Text(def.definition)
                                        .font(.body)
                                }

                                if !def.example.isEmpty {
                                    Text("“\(def.example)”")
                                        .font(.callout)
                                        .foregroundStyle(.secondary)
                                        .italic()
                                        .padding(.leading, 24)
                                }
                            }
                            .padding(10)
                            .frame(maxWidth: .infinity, alignment: .leading)
                            .background(Color(nsColor: .controlBackgroundColor), in: RoundedRectangle(cornerRadius: 10))
                        }
                    }

                    // Synonyms
                    if !word.synonyms.isEmpty {
                        VStack(alignment: .leading, spacing: 8) {
                            Text("Synonyms")
                                .font(.headline)
                            FlowLayout(spacing: 6) {
                                ForEach(word.synonyms, id: \.self) { syn in
                                    Text(syn)
                                        .font(.caption)
                                        .padding(.horizontal, 10)
                                        .padding(.vertical, 4)
                                        .background(.green.opacity(0.12), in: Capsule())
                                }
                            }
                        }
                    }

                    // Antonyms
                    if !word.antonyms.isEmpty {
                        VStack(alignment: .leading, spacing: 8) {
                            Text("Antonyms")
                                .font(.headline)
                            FlowLayout(spacing: 6) {
                                ForEach(word.antonyms, id: \.self) { ant in
                                    Text(ant)
                                        .font(.caption)
                                        .padding(.horizontal, 10)
                                        .padding(.vertical, 4)
                                        .background(.red.opacity(0.12), in: Capsule())
                                }
                            }
                        }
                    }
                }
                .padding()
            }
        }
        .frame(minWidth: 540, minHeight: 440)
    }
}
