import SwiftUI

struct CategorizationView: View {
    @Bindable var viewModel: ContentViewModel
    let unitNumber: Int?
    @State private var categories: [CategoryGroup] = []
    @State private var unsortedWords: [Word] = []
    @State private var draggedWord: Word?
    @State private var correctCount = 0
    @State private var totalAttempts = 0
    @State private var isFinished = false

    struct CategoryGroup: Identifiable {
        let id = UUID()
        let name: String
        let unitNumbers: [Int]
        var words: [Word] = []
        var placedWords: [Word] = []
    }

    var body: some View {
        VStack(spacing: 20) {
            header

            if categories.isEmpty {
                ContentUnavailableView("Not Enough Words", systemImage: "square.grid.2x2", description: Text("Need words from multiple units"))
            } else if isFinished {
                resultScreen
            } else {
                gameArea
            }
        }
        .padding()
        .onAppear { generateGame() }
    }

    private var header: some View {
        HStack {
            Text(unitNumber != nil ? "Unit \(unitNumber!) — Categorize" : "All Words — Categorize")
                .font(.title2)
                .fontWeight(.bold)
            Spacer()
            Text("\(correctCount) correct")
                .font(.callout)
                .foregroundStyle(.secondary)
            if totalAttempts > 0 {
                Text("\(totalAttempts) attempts")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
        }
    }

    private var gameArea: some View {
        VStack(spacing: 24) {
            // Unsorted words pool
            VStack(alignment: .leading, spacing: 8) {
                Text("Drag words to the correct category:")
                    .font(.headline)
                    .foregroundStyle(.secondary)

                FlowLayout(spacing: 8) {
                    ForEach(unsortedWords) { word in
                        WordChip(word: word) {
                            // Tap to select, then tap category
                            draggedWord = word
                        }
                        .opacity(draggedWord?.id == word.id ? 0.5 : 1.0)
                    }
                }
            }
            .padding()
            .background(.ultraThinMaterial, in: RoundedRectangle(cornerRadius: 12))

            // Categories
            LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible())], spacing: 16) {
                ForEach(categories) { category in
                    CategoryDropZone(
                        category: category,
                        isTarget: draggedWord != nil
                    ) {
                        if let word = draggedWord {
                            placeWord(word, in: category)
                        }
                    }
                }
            }

            Button("Check All") {
                checkComplete()
            }
            .buttonStyle(.borderedProminent)
            .disabled(unsortedWords.isEmpty)
        }
    }

    private var resultScreen: some View {
        VStack(spacing: 24) {
            Image(systemName: correctCount == totalAttempts ? "star.fill" : "checkmark.circle.fill")
                .font(.system(size: 60))
                .foregroundStyle(correctCount == totalAttempts ? .yellow : .green)

            Text("Complete!")
                .font(.largeTitle)
                .fontWeight(.bold)

            Text("\(correctCount) / \(totalAttempts) correct")
                .font(.title2)

            HStack {
                Button("Play Again") { generateGame() }
                    .buttonStyle(.bordered)
                Button("Back to Words") {
                    viewModel.selectedNavigation = unitNumber.map { .unit($0) } ?? .allWords
                }
                .buttonStyle(.borderedProminent)
            }
        }
    }

    private func placeWord(_ word: Word, in category: CategoryGroup) {
        guard let catIdx = categories.firstIndex(where: { $0.id == category.id }) else { return }
        guard let wordIdx = unsortedWords.firstIndex(where: { $0.id == word.id }) else { return }

        categories[catIdx].placedWords.append(word)
        unsortedWords.remove(at: wordIdx)
        draggedWord = nil
    }

    private func checkComplete() {
        for catIdx in categories.indices {
            for word in categories[catIdx].placedWords {
                totalAttempts += 1
                if categories[catIdx].unitNumbers.contains(where: word.unitNumbers.contains) {
                    correctCount += 1
                } else {
                    // Wrong placement - put back
                    unsortedWords.append(word)
                }
            }
            categories[catIdx].placedWords.removeAll()
        }

        if unsortedWords.isEmpty {
            isFinished = true
        }
    }

    private func generateGame() {
        let sourceWords: [Word]
        if let unitNum = unitNumber {
            sourceWords = viewModel.wordsForUnit(unitNum)
        } else {
            sourceWords = viewModel.allWords
        }

        // Group words by their first unit number
        var unitGroups: [Int: [Word]] = [:]
        for word in sourceWords {
            if let firstUnit = word.unitNumbers.first {
                unitGroups[firstUnit, default: []].append(word)
            }
        }

        // Pick 2-3 units with enough words
        let validGroups = unitGroups.filter { $0.value.count >= 3 }
        let selectedUnits = Array(validGroups.keys.shuffled().prefix(3))

        categories = selectedUnits.compactMap { unitNum in
            guard let words = unitGroups[unitNum], words.count >= 3 else { return nil }
            // Find module title for this unit
            var moduleName = "Unit \(unitNum)"
            for module in viewModel.modules {
                if let unit = module.units.first(where: { $0.number == unitNum }) {
                    moduleName = "\(module.title) (\(unit.title))"
                    break
                }
            }
            return CategoryGroup(
                name: moduleName,
                unitNumbers: [unitNum],
                words: Array(words.shuffled().prefix(4))
            )
        }

        guard categories.count >= 2 else { categories = []; return }

        // Pick 3 words from each category for the game
        unsortedWords = categories.flatMap { $0.words }.shuffled()
        categories = categories.map { cat in
            var c = cat
            c.placedWords = []
            return c
        }

        correctCount = 0
        totalAttempts = 0
        isFinished = false
        draggedWord = nil
    }
}

struct WordChip: View {
    let word: Word
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            Text(word.word)
                .font(.callout)
                .padding(.horizontal, 12)
                .padding(.vertical, 6)
        }
        .buttonStyle(.bordered)
    }
}

struct CategoryDropZone: View {
    let category: CategorizationView.CategoryGroup
    let isTarget: Bool
    let onDrop: () -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(category.name)
                .font(.headline)
                .lineLimit(2)

            if !category.placedWords.isEmpty {
                FlowLayout(spacing: 6) {
                    ForEach(category.placedWords) { word in
                        Text(word.word)
                            .font(.caption)
                            .padding(.horizontal, 8)
                            .padding(.vertical, 4)
                            .background(.green.opacity(0.2), in: Capsule())
                    }
                }
            }

            Spacer(minLength: 30)
        }
        .frame(maxWidth: .infinity, minHeight: 100, alignment: .topLeading)
        .padding()
        .background(isTarget ? Color.accentColor.opacity(0.1) : Color.clear, in: RoundedRectangle(cornerRadius: 12))
        .overlay(
            RoundedRectangle(cornerRadius: 12)
                .strokeBorder(isTarget ? Color.accentColor : Color.secondary.opacity(0.3), style: StrokeStyle(lineWidth: isTarget ? 2 : 1, dash: [5]))
        )
        .onTapGesture { onDrop() }
    }
}

struct FlowLayout: Layout {
    var spacing: CGFloat = 8

    func sizeThatFits(proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) -> CGSize {
        let result = layout(proposal: proposal, subviews: subviews)
        return result.size
    }

    func placeSubviews(in bounds: CGRect, proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) {
        let result = layout(proposal: proposal, subviews: subviews)
        for (index, position) in result.positions.enumerated() {
            subviews[index].place(at: CGPoint(x: bounds.minX + position.x, y: bounds.minY + position.y), proposal: .unspecified)
        }
    }

    private func layout(proposal: ProposedViewSize, subviews: Subviews) -> (size: CGSize, positions: [CGPoint]) {
        let maxWidth = proposal.width ?? .infinity
        var positions: [CGPoint] = []
        var x: CGFloat = 0
        var y: CGFloat = 0
        var rowHeight: CGFloat = 0
        var totalHeight: CGFloat = 0

        for subview in subviews {
            let size = subview.sizeThatFits(.unspecified)
            if x + size.width > maxWidth && x > 0 {
                x = 0
                y += rowHeight + spacing
                rowHeight = 0
            }
            positions.append(CGPoint(x: x, y: y))
            rowHeight = max(rowHeight, size.height)
            x += size.width + spacing
            totalHeight = y + rowHeight
        }

        return (CGSize(width: maxWidth, height: totalHeight), positions)
    }
}
