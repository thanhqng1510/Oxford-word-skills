import SwiftUI

struct FillInBlankView: View {
    @Bindable var viewModel: ContentViewModel
    let unitNumber: Int?
    @State private var words: [Word] = []
    @State private var currentIndex = 0
    @State private var userAnswer = ""
    @State private var showResult = false
    @State private var correctCount = 0
    @State private var isFinished = false
    @State private var revealed = false
    @State private var hintIndex = 0

    private var currentWord: Word? {
        guard currentIndex < words.count else { return nil }
        return words[currentIndex]
    }

    private var progress: Double {
        guard !words.isEmpty else { return 0 }
        return Double(currentIndex + 1) / Double(words.count)
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

            if words.isEmpty {
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
            Text("\(currentIndex + 1) / \(words.count)")
                .font(.callout)
                .foregroundStyle(.secondary)
            ProgressView(value: progress)
                .frame(width: 100)
        }
    }

    private var questionCard: some View {
        Group {
            if let word = currentWord {
                VStack(spacing: 16) {
                    Text("Listen and type the word:")
                        .font(.headline)
                        .foregroundStyle(.secondary)

                    Button {
                        SpeechService.shared.speak(word.speechText)
                    } label: {
                        Label("Play Again", systemImage: "speaker.wave.2.fill")
                            .font(.title2)
                    }
                    .buttonStyle(.borderedProminent)
                    .controlSize(.large)

                    if !word.shortDefinition.isEmpty && revealed {
                        VStack(spacing: 6) {
                            Text(word.shortDefinition)
                                .font(.body)
                                .multilineTextAlignment(.center)
                        }
                        .padding()
                        .background(.green.opacity(0.1), in: RoundedRectangle(cornerRadius: 12))
                    }

                    if showResult {
                        HStack {
                            Image(systemName: isCorrect ? "checkmark.circle.fill" : "xmark.circle.fill")
                                .foregroundStyle(isCorrect ? .green : .red)
                                .font(.title2)
                            if !isCorrect {
                                if let gloss = word.parentheticalGloss {
                                    Text("Answer: **\(word.cleanWord)** \(gloss)")
                                        .font(.headline)
                                } else {
                                    Text("Answer: **\(word.word)**")
                                        .font(.headline)
                                }
                            } else {
                                Text("Correct!")
                                    .font(.headline)
                                    .foregroundStyle(.green)
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
                    Label(currentIndex < words.count - 1 ? "Next Word" : "See Results", systemImage: "arrow.right")
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
            Image(systemName: correctCount == words.count ? "star.fill" : "checkmark.circle.fill")
                .font(.system(size: 60))
                .foregroundStyle(correctCount == words.count ? .yellow : .green)

            Text("Complete!")
                .font(.largeTitle)
                .fontWeight(.bold)

            Text("\(correctCount) / \(words.count) correct")
                .font(.title2)

            ProgressView(value: Double(correctCount), total: Double(words.count))
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
        let target = word.cleanWord
        hintIndex = min(hintIndex + 1, target.count)
        let hint = String(target.prefix(hintIndex))
        userAnswer = hint
    }

    private func checkAnswer() {
        showResult = true
        revealed = true
        if isCorrect {
            correctCount += 1
        }
    }

    private func loadWords() {
        if let unitNum = unitNumber {
            words = viewModel.wordsForUnit(unitNum).shuffled()
        } else {
            words = viewModel.allWords.shuffled()
        }
        currentIndex = 0
        userAnswer = ""
        showResult = false
        correctCount = 0
        isFinished = false
        revealed = false
        hintIndex = 0

        DispatchQueue.main.asyncAfter(deadline: .now() + 0.5) {
            if let word = words.first {
                SpeechService.shared.speak(word.speechText)
            }
        }
    }

    private func nextWord() {
        if currentIndex < words.count - 1 {
            currentIndex += 1
            userAnswer = ""
            showResult = false
            revealed = false
            hintIndex = 0
            // Auto-play next word
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.3) {
                if let word = words[safe: currentIndex] {
                    SpeechService.shared.speak(word.speechText)
                }
            }
        } else {
            isFinished = true
        }
    }
}

extension Collection {
    subscript(safe index: Index) -> Element? {
        indices.contains(index) ? self[index] : nil
    }
}
