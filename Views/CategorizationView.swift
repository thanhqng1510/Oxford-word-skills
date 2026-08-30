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

    private var headerTitle: String {
        if let unitNum = unitNumber {
            return "Unit \(unitNum) — Categorize"
        } else {
            return "All Words — Categorize"
        }
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
            .background(Color(nsColor: .controlBackgroundColor), in: RoundedRectangle(cornerRadius: 12))
            .overlay(
                RoundedRectangle(cornerRadius: 12)
                    .strokeBorder(Color(nsColor: .separatorColor).opacity(0.6), lineWidth: 1)
            )
            .shadow(color: .black.opacity(0.04), radius: 6, x: 0, y: 2)

            // Categories
            LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible())], spacing: 16) {
                ForEach(categories) { category in
                    CategoryDropZone(
                        category: category,
                        isTarget: draggedWord != nil,
                        onDrop: {
                            if let word = draggedWord {
                                placeWord(word, in: category)
                            }
                        },
                        onRemoveWord: { word in
                            removePlacedWord(word, from: category)
                        }
                    )
                }
            }

            Button("Check All") {
                checkComplete()
            }
            .buttonStyle(.borderedProminent)
            .disabled(unsortedWords.isEmpty && categories.allSatisfy { $0.placedWords.isEmpty })
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
                Button(unitNumber != nil ? "Back to Unit" : "Back to Words") {
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

    private func removePlacedWord(_ word: Word, from category: CategoryGroup) {
        guard let catIdx = categories.firstIndex(where: { $0.id == category.id }) else { return }
        if let placedIdx = categories[catIdx].placedWords.firstIndex(where: { $0.id == word.id }) {
            categories[catIdx].placedWords.remove(at: placedIdx)
            unsortedWords.append(word)
        }
    }

    private func checkComplete() {
        for catIdx in categories.indices {
            var remainingPlaced: [Word] = []
            for word in categories[catIdx].placedWords {
                totalAttempts += 1
                if categories[catIdx].unitNumbers.contains(where: word.unitNumbers.contains) {
                    correctCount += 1
                    remainingPlaced.append(word)
                } else {
                    // Wrong placement - return to unsorted pool
                    unsortedWords.append(word)
                }
            }
            categories[catIdx].placedWords = remainingPlaced
        }

        if unsortedWords.isEmpty {
            isFinished = true
        }
    }

    private func generateGame() {
        let targetCategories: [CategoryGroup]

        if let unitNum = unitNumber {
            // Single-Unit Mode: Intra-module sibling unit comparison
            var moduleUnits: [Unit] = []
            for module in viewModel.modules {
                if module.units.contains(where: { $0.number == unitNum }) {
                    moduleUnits = module.units
                    break
                }
            }

            // Find sibling units in the same module with >= 3 words
            let validSiblingUnits = moduleUnits.filter { unit in
                unit.number != unitNum && viewModel.wordsForUnit(unit.number).count >= 3
            }

            var selectedUnits: [Int] = [unitNum]
            if !validSiblingUnits.isEmpty {
                let siblings = validSiblingUnits.shuffled().prefix(2).map { $0.number }
                selectedUnits.append(contentsOf: siblings)
            } else {
                // Fallback to any other units in curriculum
                let otherUnits = viewModel.modules.flatMap { $0.units }
                    .filter { $0.number != unitNum && $0.words.count >= 3 }
                    .shuffled()
                    .prefix(2)
                    .map { $0.number }
                selectedUnits.append(contentsOf: otherUnits)
            }

            targetCategories = selectedUnits.compactMap { uNum in
                let words = viewModel.wordsForUnit(uNum)
                guard words.count >= 3 else { return nil }

                var catName = "Unit \(uNum)"
                for module in viewModel.modules {
                    if let unit = module.units.first(where: { $0.number == uNum }) {
                        catName = "Unit \(uNum): \(unit.title)"
                        break
                    }
                }

                return CategoryGroup(
                    name: catName,
                    unitNumbers: [uNum],
                    words: Array(words.shuffled().prefix(4))
                )
            }
        } else {
            // Multi-Unit / All Words Mode
            var unitGroups: [Int: [Word]] = [:]
            for word in viewModel.allWords {
                if let firstUnit = word.unitNumbers.first {
                    unitGroups[firstUnit, default: []].append(word)
                }
            }

            let validGroups = unitGroups.filter { $0.value.count >= 3 }
            let selectedUnits = Array(validGroups.keys.shuffled().prefix(3))

            targetCategories = selectedUnits.compactMap { uNum in
                guard let words = unitGroups[uNum], words.count >= 3 else { return nil }
                var catName = "Unit \(uNum)"
                for module in viewModel.modules {
                    if let unit = module.units.first(where: { $0.number == uNum }) {
                        catName = "\(unit.title) (Unit \(uNum))"
                        break
                    }
                }
                return CategoryGroup(
                    name: catName,
                    unitNumbers: [uNum],
                    words: Array(words.shuffled().prefix(4))
                )
            }
        }

        guard targetCategories.count >= 2 else {
            categories = []
            return
        }

        categories = targetCategories.map { cat in
            var c = cat
            c.placedWords = []
            return c
        }

        unsortedWords = categories.flatMap { $0.words }.shuffled()
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
    var onRemoveWord: ((Word) -> Void)? = nil

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(category.name)
                .font(.headline)
                .lineLimit(2)

            if !category.placedWords.isEmpty {
                FlowLayout(spacing: 6) {
                    ForEach(category.placedWords) { word in
                        Button {
                            onRemoveWord?(word)
                        } label: {
                            Text(word.word)
                                .font(.caption)
                                .padding(.horizontal, 8)
                                .padding(.vertical, 4)
                                .background(.green.opacity(0.2), in: Capsule())
                        }
                        .buttonStyle(.plain)
                        .help("Click to return word to unsorted pool")
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
