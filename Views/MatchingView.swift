import SwiftUI

struct MatchingView: View {
    @Bindable var viewModel: ContentViewModel
    let unitNumber: Int?
    @State private var pairs: [MatchPair] = []
    @State private var rightOptions: [RightOption] = []
    @State private var selectedLeft: UUID?
    @State private var selectedRight: UUID?
    @State private var matchedPairs: Set<UUID> = []
    @State private var attempts = 0
    @State private var isFinished = false
    @State private var wrongRightIDs: Set<UUID> = []
    @State private var wrongLeftIDs: Set<UUID> = []

    private var progress: Double {
        guard !pairs.isEmpty else { return 0 }
        return Double(matchedPairs.count) / Double(pairs.count)
    }

    private var headerTitle: String {
        if let unitNum = unitNumber {
            return "Unit \(unitNum) — Synonym Match"
        } else {
            return "All Words — Synonym Match"
        }
    }

    var body: some View {
        VStack(spacing: 20) {
            header

            if pairs.isEmpty {
                ContentUnavailableView(
                    "No Words with Synonyms",
                    systemImage: "arrow.triangle.branch",
                    description: Text("Need words with synonym data")
                )
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
        HStack(spacing: 12) {
            Button {
                if let unitNum = unitNumber {
                    viewModel.selectedNavigation = .unit(unitNum)
                } else {
                    viewModel.selectedNavigation = .allWords
                }
            } label: {
                HStack(spacing: 4) {
                    Image(systemName: "chevron.left")
                        .fontWeight(.semibold)
                    Text(unitNumber != nil ? "Unit \(unitNumber!)" : "Words")
                }
            }
            .buttonStyle(.bordered)
            .help("Back to vocabulary list")

            Text(headerTitle)
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
                        text: pair.word.word,
                        isSelected: selectedLeft == pair.id,
                        isMatched: matchedPairs.contains(pair.id),
                        isWrong: wrongLeftIDs.contains(pair.id)
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

            // Right column: synonyms (stable shuffled @State)
            VStack(spacing: 8) {
                Text("Synonyms")
                    .font(.headline)
                    .foregroundStyle(.secondary)
                ForEach(rightOptions) { option in
                    matchButton(
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

    private func matchButton(
        text: String,
        isSelected: Bool,
        isMatched: Bool,
        isWrong: Bool = false,
        action: @escaping () -> Void
    ) -> some View {
        Button(action: action) {
            Text(text)
                .font(.body)
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
        selectedLeft = (selectedLeft == id) ? nil : id
        checkMatch()
    }

    private func selectRight(_ option: RightOption) {
        guard !matchedPairs.contains(option.pairID) else { return }
        selectedRight = (selectedRight == option.id) ? nil : option.id
        checkMatch()
    }

    private func checkMatch() {
        guard let leftID = selectedLeft, let rightID = selectedRight else { return }
        attempts += 1

        guard let matchedOption = rightOptions.first(where: { $0.id == rightID }) else {
            selectedLeft = nil
            selectedRight = nil
            return
        }

        if matchedOption.pairID == leftID {
            matchedPairs.insert(leftID)
            wrongRightIDs.remove(rightID)
            wrongLeftIDs.remove(leftID)
        } else {
            wrongRightIDs.insert(rightID)
            wrongLeftIDs.insert(leftID)
            let capturedRight = rightID
            let capturedLeft = leftID
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.5) {
                wrongRightIDs.remove(capturedRight)
                wrongLeftIDs.remove(capturedLeft)
            }
        }

        selectedLeft = nil
        selectedRight = nil

        if matchedPairs.count == pairs.count {
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.5) {
                withAnimation(.smooth) {
                    isFinished = true
                }
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
                Button(unitNumber != nil ? "Back to Unit" : "Back to Words") {
                    viewModel.selectedNavigation = unitNumber.map { .unit($0) } ?? .allWords
                }
                .buttonStyle(.borderedProminent)
            }
        }
    }

    private func isCleanSynonym(_ syn: String, for word: String) -> Bool {
        let trimmed = syn.trimmingCharacters(in: .whitespacesAndNewlines)
        return !trimmed.isEmpty &&
               trimmed.count > 1 &&
               trimmed.caseInsensitiveCompare(word) != .orderedSame &&
               !trimmed.localizedCaseInsensitiveContains("equivalent") &&
               !trimmed.localizedCaseInsensitiveContains("placeholder")
    }

    private func generatePairs() {
        let sourceWords: [Word]
        if let unitNum = unitNumber {
            sourceWords = viewModel.wordsForUnit(unitNum)
        } else {
            sourceWords = viewModel.allWords
        }

        // Filter words that have at least one clean synonym distinct from the word itself
        let validWords = sourceWords.filter { word in
            !word.synonyms.isEmpty &&
            word.synonyms.contains { isCleanSynonym($0, for: word.word) }
        }

        let shuffled = validWords.shuffled()
        var selectedPairs: [MatchPair] = []
        var usedSynonyms = Set<String>()

        for word in shuffled {
            let availableSynonyms = word.synonyms
                .map { $0.trimmingCharacters(in: .whitespacesAndNewlines) }
                .filter { syn in
                    isCleanSynonym(syn, for: word.word) &&
                    !usedSynonyms.contains(syn.lowercased())
                }

            if let chosenSyn = availableSynonyms.first {
                let pairID = UUID()
                selectedPairs.append(MatchPair(id: pairID, word: word, synonym: chosenSyn))
                usedSynonyms.insert(chosenSyn.lowercased())

                if selectedPairs.count == 6 {
                    break
                }
            }
        }

        // Fallback: If strict deduplication yielded fewer than 2 pairs, allow secondary clean synonyms
        if selectedPairs.count < 2 && !shuffled.isEmpty {
            selectedPairs.removeAll()
            for word in shuffled.prefix(6) {
                if let syn = word.synonyms.first(where: { isCleanSynonym($0, for: word.word) }) {
                    let pairID = UUID()
                    selectedPairs.append(MatchPair(id: pairID, word: word, synonym: syn.trimmingCharacters(in: .whitespacesAndNewlines)))
                }
            }
        }

        pairs = selectedPairs
        rightOptions = selectedPairs.map { RightOption(id: UUID(), pairID: $0.id, synonym: $0.synonym) }.shuffled()

        matchedPairs.removeAll()
        selectedLeft = nil
        selectedRight = nil
        attempts = 0
        isFinished = false
        wrongRightIDs.removeAll()
        wrongLeftIDs.removeAll()
    }
}

struct MatchPair: Identifiable, Equatable {
    let id: UUID
    let word: Word
    let synonym: String

    init(id: UUID = UUID(), word: Word, synonym: String) {
        self.id = id
        self.word = word
        self.synonym = synonym
    }

    static func == (lhs: MatchPair, rhs: MatchPair) -> Bool {
        lhs.id == rhs.id
    }
}

struct RightOption: Identifiable, Equatable {
    let id: UUID
    let pairID: UUID
    let synonym: String

    init(id: UUID = UUID(), pairID: UUID, synonym: String) {
        self.id = id
        self.pairID = pairID
        self.synonym = synonym
    }

    static func == (lhs: RightOption, rhs: RightOption) -> Bool {
        lhs.id == rhs.id
    }
}
