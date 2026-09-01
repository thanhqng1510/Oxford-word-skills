import SwiftUI

struct FillInBlankView: View {
    @Bindable var viewModel: ContentViewModel
    let unitNumber: Int?
    @State private var items: [SpellingExerciseItem] = []
    @State private var currentIndex = 0
    @State private var userAnswer = ""
    @State private var showResult = false
    @State private var correctCount = 0
    @State private var isFinished = false
    @State private var revealed = false
    @State private var hintLevel = 0

    private var currentItem: SpellingExerciseItem? {
        guard currentIndex < items.count else { return nil }
        return items[currentIndex]
    }

    private var currentWord: Word? {
        currentItem?.word
    }

    private var progress: Double {
        guard !items.isEmpty else { return 0 }
        return Double(currentIndex + 1) / Double(items.count)
    }

    private var headerTitle: String {
        if let unitNum = unitNumber {
            return "Unit \(unitNum) — Listening & Spelling"
        } else {
            return "All Words — Listening & Spelling"
        }
    }

    var body: some View {
        VStack(spacing: 20) {
            header

            if items.isEmpty {
                ContentUnavailableView("No Words", systemImage: "waveform", description: Text("No vocabulary words available"))
            } else if isFinished {
                resultScreen
            } else {
                questionCard
                answerArea
                buttons
            }
        }
        .padding()
        .onAppear { loadWords() }
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
            Text("\(currentIndex + 1) / \(items.count)")
                .font(.callout)
                .foregroundStyle(.secondary)
            ProgressView(value: progress)
                .frame(width: 100)
        }
    }

    private var questionCard: some View {
        Group {
            if let item = currentItem {
                VStack(spacing: 16) {
                    Text("Listen and type the word:")
                        .font(.headline)
                        .foregroundStyle(.secondary)

                    Button {
                        SpeechService.shared.speak(item.word.speechText)
                    } label: {
                        Label("Play Again", systemImage: "speaker.wave.2.fill")
                            .font(.title2)
                    }
                    .buttonStyle(.borderedProminent)
                    .controlSize(.large)

                    if let def = item.targetDefinition, (revealed || hintLevel > 0) {
                        VStack(spacing: 6) {
                            HStack(spacing: 6) {
                                if !def.partOfSpeech.isEmpty {
                                    Text(def.partOfSpeech)
                                        .font(.caption)
                                        .fontWeight(.semibold)
                                        .padding(.horizontal, 6)
                                        .padding(.vertical, 2)
                                        .background(.blue.opacity(0.15), in: Capsule())
                                }
                                Text(def.definition)
                                    .font(.body)
                            }
                            .multilineTextAlignment(.center)

                            if hintLevel >= 2 && !def.example.isEmpty && !showResult {
                                Text("Example: “\(maskedExample(def.example, word: item.word))”")
                                    .font(.caption)
                                    .foregroundStyle(.secondary)
                                    .italic()
                                    .padding(.top, 2)
                            }
                        }
                        .padding()
                        .background(.green.opacity(0.1), in: RoundedRectangle(cornerRadius: 12))
                    }

                    if showResult {
                        VStack(spacing: 6) {
                            HStack {
                                Image(systemName: isCorrect ? "checkmark.circle.fill" : "xmark.circle.fill")
                                    .foregroundStyle(isCorrect ? .green : .red)
                                    .font(.title2)
                                if !isCorrect {
                                    if let gloss = item.word.parentheticalGloss {
                                        Text("Answer: **\(item.word.cleanWord)** \(gloss)")
                                            .font(.headline)
                                    } else {
                                        Text("Answer: **\(item.word.word)**")
                                            .font(.headline)
                                    }
                                } else {
                                    Text("Correct! **\(item.word.word)**")
                                        .font(.headline)
                                        .foregroundStyle(.green)
                                }
                            }

                            if !item.word.ipa.isEmpty {
                                Text(item.word.ipa)
                                    .font(.subheadline)
                                    .foregroundStyle(.secondary)
                            }
                        }
                        .padding(.top, 8)
                    }
                }
                .padding(28)
                .frame(maxWidth: 600)
                .background(Color(nsColor: .controlBackgroundColor), in: RoundedRectangle(cornerRadius: 16))
                .overlay(
                    RoundedRectangle(cornerRadius: 16)
                        .strokeBorder(Color(nsColor: .separatorColor).opacity(0.6), lineWidth: 1)
                )
                .shadow(color: .black.opacity(0.04), radius: 8, x: 0, y: 2)
            }
        }
    }

    private var isCorrect: Bool {
        guard let word = currentWord else { return false }
        let input = userAnswer.trimmingCharacters(in: .whitespaces).lowercased()
        return word.acceptedSpellings.contains(input)
    }

    private var answerArea: some View {
        Group {
            if !showResult {
                HStack {
                    TextField("Type the word you hear...", text: $userAnswer)
                        .textFieldStyle(.roundedBorder)
                        .font(.system(.body, design: .monospaced))
                        .onSubmit { checkAnswer() }

                    Button("Hint") {
                        giveHint()
                    }
                    .buttonStyle(.bordered)
                    .controlSize(.small)
                }
                .frame(maxWidth: 400)
            }
        }
    }

    private var buttons: some View {
        Group {
            if showResult {
                Button {
                    nextWord()
                } label: {
                    Label(currentIndex < items.count - 1 ? "Next Word" : "See Results", systemImage: "arrow.right")
                        .font(.headline)
                }
                .buttonStyle(.borderedProminent)
            } else {
                HStack {
                    Button("Skip") {
                        nextWord()
                    }
                    .buttonStyle(.bordered)

                    Button("Check") {
                        checkAnswer()
                    }
                    .buttonStyle(.borderedProminent)
                    .disabled(userAnswer.trimmingCharacters(in: .whitespaces).isEmpty)
                }
            }
        }
    }

    private var resultScreen: some View {
        VStack(spacing: 24) {
            Image(systemName: correctCount == items.count ? "star.fill" : "checkmark.circle.fill")
                .font(.system(size: 60))
                .foregroundStyle(correctCount == items.count ? .yellow : .green)

            Text("Complete!")
                .font(.largeTitle)
                .fontWeight(.bold)

            Text("\(correctCount) / \(items.count) correct")
                .font(.title2)

            ProgressView(value: Double(correctCount), total: Double(items.count))
                .frame(width: 200)

            HStack {
                Button("Try Again") { loadWords() }
                    .buttonStyle(.bordered)
                Button(unitNumber != nil ? "Back to Unit" : "Back to Words") {
                    viewModel.selectedNavigation = unitNumber.map { .unit($0) } ?? .allWords
                }
                .buttonStyle(.borderedProminent)
            }
        }
    }

    private func giveHint() {
        guard let word = currentWord else { return }
        hintLevel += 1
        let target = word.cleanWord
        let prefixLen = min(hintLevel, target.count)
        userAnswer = String(target.prefix(prefixLen))
    }

    private func maskedExample(_ example: String, word: Word) -> String {
        let pattern = word.cleanWord
        guard !pattern.isEmpty else { return example }
        return example.replacingOccurrences(of: pattern, with: "______", options: .caseInsensitive)
    }

    private func checkAnswer() {
        showResult = true
        revealed = true
        if isCorrect {
            correctCount += 1
        }
    }

    private func loadWords() {
        let rawWords: [Word]
        if let unitNum = unitNumber {
            rawWords = viewModel.wordsForUnit(unitNum).shuffled()
        } else {
            rawWords = viewModel.allWords.shuffled()
        }

        items = rawWords.map { word in
            let targetDef = word.definitions.first(where: { !$0.definition.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty })
            return SpellingExerciseItem(word: word, targetDefinition: targetDef)
        }

        currentIndex = 0
        userAnswer = ""
        showResult = false
        correctCount = 0
        isFinished = false
        revealed = false
        hintLevel = 0

        DispatchQueue.main.asyncAfter(deadline: .now() + 0.5) {
            if let firstItem = items.first {
                SpeechService.shared.speak(firstItem.word.speechText)
            }
        }
    }

    private func nextWord() {
        if currentIndex < items.count - 1 {
            currentIndex += 1
            userAnswer = ""
            showResult = false
            revealed = false
            hintLevel = 0
            // Auto-play next word
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.3) {
                if let item = items[safe: currentIndex] {
                    SpeechService.shared.speak(item.word.speechText)
                }
            }
        } else {
            isFinished = true
        }
    }
}

struct SpellingExerciseItem: Identifiable {
    let id = UUID()
    let word: Word
    let targetDefinition: WordDefinition?
}

extension Collection {
    subscript(safe index: Index) -> Element? {
        indices.contains(index) ? self[index] : nil
    }
}
