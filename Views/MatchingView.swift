import SwiftUI

struct MatchingView: View {
    @Bindable var viewModel: ContentViewModel
    let unitNumber: Int?
    @State private var pairs: [MatchPair] = []
    @State private var selectedLeft: UUID?
    @State private var selectedRight: UUID?
    @State private var matchedPairs: Set<UUID> = []
    @State private var attempts = 0
    @State private var isFinished = false
    @State private var wrongRightIDs: Set<UUID> = []

    private var progress: Double {
        guard !pairs.isEmpty else { return 0 }
        return Double(matchedPairs.count) / Double(pairs.count)
    }

    var body: some View {
        VStack(spacing: 20) {
            header

            if pairs.isEmpty {
                ContentUnavailableView("No Words with Synonyms", systemImage: "arrow.triangle.branch", description: Text("Need words with synonym data"))
            } else if isFinished {
                resultScreen
            } else {
                matchingArea
            }
        }
        .padding()
        .onAppear { generatePairs() }
    }

    private var header: some View {
        HStack {
            Text(unitNumber != nil ? "Unit \(unitNumber!) — Synonym Match" : "All Words — Synonym Match")
                .font(.title2)
                .fontWeight(.bold)
            Spacer()
            Text("\(matchedPairs.count) / \(pairs.count) matched")
                .font(.callout)
                .foregroundStyle(.secondary)
            ProgressView(value: progress)
                .frame(width: 100)
            Text("Attempts: \(attempts)")
                .font(.caption)
                .foregroundStyle(.secondary)
        }
    }

    private var matchingArea: some View {
        HStack(spacing: 30) {
            // Left column: words
            VStack(spacing: 8) {
                Text("Words")
                    .font(.headline)
                    .foregroundStyle(.secondary)
                ForEach(pairs) { pair in
                    matchButton(
                        id: pair.id,
                        text: pair.word.word,
                        isSelected: selectedLeft == pair.id,
                        isMatched: matchedPairs.contains(pair.id)
                    ) {
                        selectLeft(pair.id)
                    }
                }
            }

            VStack(spacing: 8) {
                Image(systemName: "arrow.right")
                    .font(.title2)
                    .foregroundStyle(.secondary)
                Image(systemName: "arrow.left")
                    .font(.title2)
                    .foregroundStyle(.secondary)
            }

            // Right column: synonyms (shuffled)
            VStack(spacing: 8) {
                Text("Synonyms")
                    .font(.headline)
                    .foregroundStyle(.secondary)
                ForEach(rightOptions) { option in
                    matchButton(
                        id: option.id,
                        text: option.synonym,
                        isSelected: selectedRight == option.id,
                        isMatched: matchedPairs.contains(option.pairID),
                        isWrong: wrongRightIDs.contains(option.id)
                    ) {
                        selectRight(option)
                    }
                }
            }
        }
        .frame(maxWidth: 600)
    }

    private struct RightOption: Identifiable {
        let id = UUID()
        let pairID: UUID
        let synonym: String
    }

    private var rightOptions: [RightOption] {
        pairs.flatMap { pair in
            pair.synonyms.prefix(2).map { RightOption(pairID: pair.id, synonym: $0) }
        }.shuffled()
    }

    private func matchButton(id: UUID, text: String, isSelected: Bool, isMatched: Bool, isWrong: Bool = false, action: @escaping () -> Void) -> some View {
        Button(action: action) {
            Text(text)
                .frame(maxWidth: .infinity, minHeight: 44)
                .padding(.horizontal)
        }
        .buttonStyle(.bordered)
        .tint(isMatched ? .green : isWrong ? .red : isSelected ? .orange : .accentColor)
        .disabled(isMatched)
        .opacity(isMatched ? 0.5 : 1.0)
    }

    private func selectLeft(_ id: UUID) {
        guard !matchedPairs.contains(id) else { return }
        selectedLeft = id
        checkMatch()
    }

    private func selectRight(_ option: RightOption) {
        guard !matchedPairs.contains(option.pairID) else { return }
        selectedRight = option.id
        checkMatch()
    }

    private func checkMatch() {
        guard let leftID = selectedLeft, let rightID = selectedRight else { return }
        attempts += 1

        let matchedOption = rightOptions.first { $0.id == rightID }

        if let option = matchedOption, option.pairID == leftID {
            matchedPairs.insert(leftID)
            wrongRightIDs.remove(rightID)
        } else {
            wrongRightIDs.insert(rightID)
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.5) {
                wrongRightIDs.remove(rightID)
            }
        }

        selectedLeft = nil
        selectedRight = nil

        if matchedPairs.count == pairs.count {
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.5) {
                isFinished = true
            }
        }
    }

    private var resultScreen: some View {
        VStack(spacing: 24) {
            Image(systemName: attempts <= pairs.count + 2 ? "star.fill" : "checkmark.circle.fill")
                .font(.system(size: 60))
                .foregroundStyle(attempts <= pairs.count + 2 ? .yellow : .green)

            Text("All Matched!")
                .font(.largeTitle)
                .fontWeight(.bold)

            Text("\(pairs.count) pairs in \(attempts) attempts")
                .font(.title2)

            HStack {
                Button("Play Again") { generatePairs() }
                    .buttonStyle(.bordered)
                Button("Back to Words") {
                    viewModel.selectedNavigation = unitNumber.map { .unit($0) } ?? .allWords
                }
                .buttonStyle(.borderedProminent)
            }
        }
    }

    private func generatePairs() {
        let sourceWords: [Word]
        if let unitNum = unitNumber {
            sourceWords = viewModel.wordsForUnit(unitNum)
        } else {
            sourceWords = viewModel.allWords
        }

        let valid = sourceWords.filter { !$0.synonyms.isEmpty }
        let shuffled = valid.shuffled()

        pairs = Array(shuffled.prefix(min(6, shuffled.count))).map {
            MatchPair(word: $0, synonyms: Array($0.synonyms.prefix(2)))
        }

        matchedPairs.removeAll()
        selectedLeft = nil
        selectedRight = nil
        attempts = 0
        isFinished = false
        wrongRightIDs.removeAll()
    }
}

struct MatchPair: Identifiable {
    let id = UUID()
    let word: Word
    let synonyms: [String]
}
