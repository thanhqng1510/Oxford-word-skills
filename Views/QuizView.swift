import SwiftUI

struct QuizView: View {
    @Bindable var viewModel: ContentViewModel
    let quizMode: QuizMode
    let unitNumber: Int?
    @State private var questions: [QuizQuestion] = []
    @State private var currentIndex = 0
    @State private var selectedAnswer: String?
    @State private var showResult = false
    @State private var correctCount = 0
    @State private var isFinished = false

    enum QuizMode {
        case wordToDefinition
        case definitionToWord
    }

    private var currentQuestion: QuizQuestion? {
        guard currentIndex < questions.count else { return nil }
        return questions[currentIndex]
    }

    private var progress: Double {
        guard !questions.isEmpty else { return 0 }
        return Double(currentIndex + 1) / Double(questions.count)
    }

    private var title: String {
        let prefix: String
        if let unitNum = unitNumber {
            prefix = "Unit \(unitNum)"
        } else {
            prefix = "All Words"
        }
        switch quizMode {
        case .wordToDefinition: return "\(prefix) — Word → Definition"
        case .definitionToWord: return "\(prefix) — Definition → Word"
        }
    }

    var body: some View {
        VStack(spacing: 20) {
            header

            if questions.isEmpty {
                ContentUnavailableView(
                    "No Words with Definitions",
                    systemImage: "text.book.closed",
                    description: Text("Need words with definitions loaded")
                )
            } else if isFinished {
                resultScreen
            } else {
                questionCard
                optionsGrid
                nextButton
            }
        }
        .padding()
        .onAppear { generateQuestions() }
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

            Text(title)
                .font(.title2)
                .fontWeight(.bold)
            Spacer()
            Text("\(currentIndex + 1) / \(questions.count)")
                .font(.callout)
                .foregroundStyle(.secondary)
            ProgressView(value: progress)
                .frame(width: 100)
        }
    }

    private var questionCard: some View {
        Group {
            if let q = currentQuestion {
                VStack(spacing: 16) {
                    switch quizMode {
                    case .wordToDefinition:
                        Text(q.word.word)
                            .font(.system(size: 32, weight: .bold, design: .rounded))
                        Button {
                            SpeechService.shared.speak(q.word.speechText)
                        } label: {
                            Label("Listen", systemImage: "speaker.wave.2.fill")
                        }
                        .buttonStyle(.bordered)
                        Text("Choose the correct definition:")
                            .font(.headline)
                            .foregroundStyle(.secondary)

                    case .definitionToWord:
                        Text(q.correctDefinition)
                            .font(.body)
                            .multilineTextAlignment(.center)
                            .frame(maxWidth: 400)
                            .padding()
                            .background {
                                RoundedRectangle(cornerRadius: 12)
                                    .glassEffect()
                            }
                        Text("Choose the correct word:")
                            .font(.headline)
                            .foregroundStyle(.secondary)
                    }
                }
                .padding(24)
                .frame(maxWidth: .infinity)
                .background {
                    RoundedRectangle(cornerRadius: 16)
                        .glassEffect()
                }
            }
        }
    }

    private var optionsGrid: some View {
        LazyVGrid(columns: [GridItem(.flexible())], spacing: 10) {
            ForEach(currentQuestion?.options ?? [], id: \.self) { option in
                Button {
                    if !showResult {
                        selectedAnswer = option
                        showResult = true
                        if option == currentQuestion?.correctAnswer {
                            correctCount += 1
                        }
                    }
                } label: {
                    Text(option)
                        .font(quizMode == .wordToDefinition ? .body : .system(.body, design: .rounded))
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .padding(.horizontal, 16)
                        .padding(.vertical, 12)
                }
                .buttonStyle(.bordered)
                .tint(optionTintColor(option))
                .disabled(showResult)
            }
        }
        .frame(maxWidth: 500)
    }

    private var nextButton: some View {
        Group {
            if showResult {
                Button {
                    nextQuestion()
                } label: {
                    Label(currentIndex < questions.count - 1 ? "Next" : "See Results", systemImage: "arrow.right")
                        .font(.headline)
                }
                .buttonStyle(.borderedProminent)
            }
        }
    }

    private var resultScreen: some View {
        VStack(spacing: 24) {
            Image(systemName: correctCount == questions.count ? "star.fill" : "checkmark.circle.fill")
                .font(.system(size: 60))
                .foregroundStyle(correctCount == questions.count ? .yellow : .green)

            Text("Quiz Complete!")
                .font(.largeTitle)
                .fontWeight(.bold)

            Text("\(correctCount) / \(questions.count) correct")
                .font(.title2)

            ProgressView(value: Double(correctCount), total: Double(questions.count))
                .frame(width: 200)

            HStack {
                Button("Try Again") { generateQuestions() }
                    .buttonStyle(.bordered)
                Button(unitNumber != nil ? "Back to Unit" : "Back to Words") {
                    viewModel.selectedNavigation = unitNumber.map { .unit($0) } ?? .allWords
                }
                .buttonStyle(.borderedProminent)
            }
        }
    }

    private func optionTintColor(_ option: String) -> Color {
        guard showResult, let q = currentQuestion else { return .accentColor }
        if option == q.correctAnswer { return .green }
        if option == selectedAnswer { return .red }
        return .accentColor
    }

    private func nextQuestion() {
        if currentIndex < questions.count - 1 {
            currentIndex += 1
            selectedAnswer = nil
            showResult = false
        } else {
            isFinished = true
        }
    }

    private func generateQuestions() {
        let sourceWords: [Word]
        if let unitNum = unitNumber {
            sourceWords = viewModel.wordsForUnit(unitNum)
        } else {
            sourceWords = viewModel.allWords
        }

        // Filter valid words with meaningful definitions
        let validSourceWords = sourceWords.filter {
            !$0.definitions.isEmpty &&
            $0.shortDefinition != "No definition available" &&
            !$0.shortDefinition.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
        }

        guard !validSourceWords.isEmpty else {
            questions = []
            return
        }

        let fallbackWords = viewModel.allWords.filter {
            !$0.definitions.isEmpty &&
            $0.shortDefinition != "No definition available" &&
            !$0.shortDefinition.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
        }

        let shuffled = validSourceWords.shuffled()
        let questionWords = Array(shuffled.prefix(min(15, shuffled.count)))

        questions = questionWords.compactMap { word in
            switch quizMode {
            case .wordToDefinition:
                let correctDef = word.shortDefinition.trimmingCharacters(in: .whitespacesAndNewlines)
                var chosenDefs: [String] = []
                var seenDefs = Set<String>([correctDef.lowercased()])

                // 1. First-pass distractors: sample from current unit
                let unitCandidates = validSourceWords.filter { $0.id != word.id }.shuffled()
                for candidate in unitCandidates {
                    let def = candidate.shortDefinition.trimmingCharacters(in: .whitespacesAndNewlines)
                    let defKey = def.lowercased()
                    if !def.isEmpty && !seenDefs.contains(defKey) {
                        seenDefs.insert(defKey)
                        chosenDefs.append(def)
                        if chosenDefs.count == 3 { break }
                    }
                }

                // 2. Second-pass distractors: sample from global pool if unit has < 3 distinct distractors
                if chosenDefs.count < 3 {
                    let globalCandidates = fallbackWords.filter { $0.id != word.id }.shuffled()
                    for candidate in globalCandidates {
                        let def = candidate.shortDefinition.trimmingCharacters(in: .whitespacesAndNewlines)
                        let defKey = def.lowercased()
                        if !def.isEmpty && !seenDefs.contains(defKey) {
                            seenDefs.insert(defKey)
                            chosenDefs.append(def)
                            if chosenDefs.count == 3 { break }
                        }
                    }
                }

                let options = ([correctDef] + chosenDefs).shuffled()
                return QuizQuestion(word: word, options: options, correctAnswer: correctDef, correctDefinition: correctDef)

            case .definitionToWord:
                let correctWord = word.word.trimmingCharacters(in: .whitespacesAndNewlines)
                let correctDef = word.shortDefinition.trimmingCharacters(in: .whitespacesAndNewlines)
                var chosenWords: [String] = []
                var seenWords = Set<String>([correctWord.lowercased()])

                // 1. First-pass distractors: sample from current unit
                let unitCandidates = validSourceWords.filter { $0.id != word.id }.shuffled()
                for candidate in unitCandidates {
                    let candidateWord = candidate.word.trimmingCharacters(in: .whitespacesAndNewlines)
                    let wordKey = candidateWord.lowercased()
                    if !candidateWord.isEmpty && !seenWords.contains(wordKey) {
                        seenWords.insert(wordKey)
                        chosenWords.append(candidateWord)
                        if chosenWords.count == 3 { break }
                    }
                }

                // 2. Second-pass distractors: sample from global pool if unit has < 3 distinct distractors
                if chosenWords.count < 3 {
                    let globalCandidates = fallbackWords.filter { $0.id != word.id }.shuffled()
                    for candidate in globalCandidates {
                        let candidateWord = candidate.word.trimmingCharacters(in: .whitespacesAndNewlines)
                        let wordKey = candidateWord.lowercased()
                        if !candidateWord.isEmpty && !seenWords.contains(wordKey) {
                            seenWords.insert(wordKey)
                            chosenWords.append(candidateWord)
                            if chosenWords.count == 3 { break }
                        }
                    }
                }

                let options = ([correctWord] + chosenWords).shuffled()
                return QuizQuestion(word: word, options: options, correctAnswer: correctWord, correctDefinition: correctDef)
            }
        }

        currentIndex = 0
        selectedAnswer = nil
        showResult = false
        correctCount = 0
        isFinished = false
    }
}

struct QuizQuestion: Identifiable {
    let id = UUID()
    let word: Word
    let options: [String]
    let correctAnswer: String
    let correctDefinition: String
}
