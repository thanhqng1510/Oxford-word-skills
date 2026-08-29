import SwiftUI

struct VocabularyListView: View {
    @Bindable var viewModel: ContentViewModel

    var body: some View {
        Table(viewModel.filteredWords) {
            TableColumn("Word") { word in
                HStack {
                    Text(word.word)
                        .fontWeight(.medium)
                    Button {
                        SpeechService.shared.speak(word.word)
                    } label: {
                        Image(systemName: "speaker.wave.2")
                            .font(.caption)
                    }
                    .buttonStyle(.plain)
                    .help("Pronounce")
                }
            }
            .width(min: 120, ideal: 180)

            TableColumn("Definition") { word in
                Text(word.shortDefinition)
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .lineLimit(2)
            }
            .width(min: 150, ideal: 250)

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
                    ForEach(ExerciseType.allCases.filter { $0 != .matching && $0 != .categorize }, id: \.self) { type in
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
