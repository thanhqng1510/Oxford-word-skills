import SwiftUI

struct FlashcardView: View {
    @Bindable var viewModel: ContentViewModel
    let unitNumber: Int?
    @State private var words: [Word] = []
    @State private var currentIndex = 0
    @State private var isFlipped = false
    @State private var showExample = false

    private var currentWord: Word? {
        guard currentIndex < words.count else { return nil }
        return words[currentIndex]
    }

    private var progress: Double {
        guard !words.isEmpty else { return 0 }
        return Double(currentIndex + 1) / Double(words.count)
    }

    var body: some View {
        VStack(spacing: 20) {
            header
            if words.isEmpty {
                ContentUnavailableView("No Words", systemImage: "rectangle.stack", description: Text("No vocabulary words available"))
            } else {
                cardArea
                controls
            }
        }
        .padding()
        .onAppear { loadWords() }
    }

    private var header: some View {
        HStack {
            Text(unitNumber != nil ? "Unit \(unitNumber!) — Flashcards" : "All Words — Flashcards")
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

    @State private var dragOffset: CGFloat = 0

    private var cardArea: some View {
        ZStack {
            if let word = currentWord {
                RoundedRectangle(cornerRadius: 20)
                    .fill(.ultraThinMaterial)
                    .shadow(color: .black.opacity(0.1), radius: 10, x: 0, y: 5)

                VStack(spacing: 16) {
                    if isFlipped {
                        // Back: definition + example
                        VStack(spacing: 12) {
                            Text(word.word)
                                .font(.largeTitle)
                                .fontWeight(.bold)

                            if !word.partOfSpeech.isEmpty {
                                Text(word.partOfSpeech)
                                    .font(.caption)
                                    .padding(.horizontal, 8)
                                    .padding(.vertical, 2)
                                    .background(.blue.opacity(0.15), in: Capsule())
                            }

                            Text(word.shortDefinition)
                                .font(.body)
                                .multilineTextAlignment(.center)
                                .frame(maxWidth: 380)

                            if showExample, let example = word.examples.first {
                                Text("\"\(example)\"")
                                    .font(.callout)
                                    .foregroundStyle(.secondary)
                                    .italic()
                                    .padding(.top, 4)
                            }

                            HStack(spacing: 16) {
                                Button {
                                    SpeechService.shared.speak(word.word)
                                } label: {
                                    Label("Listen", systemImage: "speaker.wave.2.fill")
                                }
                                .buttonStyle(.borderedProminent)

                                if !word.examples.isEmpty {
                                    Button {
                                        showExample.toggle()
                                    } label: {
                                        Label(showExample ? "Hide Example" : "Show Example", systemImage: "text.quote")
                                    }
                                    .buttonStyle(.bordered)
                                }
                            }

                            if !word.synonyms.isEmpty {
                                HStack {
                                    Text("Synonyms:")
                                        .font(.caption)
                                        .foregroundStyle(.secondary)
                                    Text(word.synonyms.prefix(4).joined(separator: ", "))
                                        .font(.caption)
                                }
                            }
                        }
                    } else {
                        // Front: word only
                        VStack(spacing: 12) {
                            Text(word.word)
                                .font(.system(size: 44, weight: .bold, design: .rounded))

                            Text("Tap to reveal definition")
                                .font(.callout)
                                .foregroundStyle(.tertiary)
                        }
                    }
                }
                .padding(36)
                .frame(maxWidth: 480, maxHeight: 360)
                .onTapGesture {
                    withAnimation(.spring(duration: 0.6)) {
                        isFlipped.toggle()
                        showExample = false
                    }
                }
                .offset(x: dragOffset)
                .gesture(
                    DragGesture()
                        .onChanged { value in
                            dragOffset = value.translation.width
                        }
                        .onEnded { value in
                            withAnimation(.spring) {
                                if value.translation.width < -80 { nextCard() }
                                else if value.translation.width > 80 { previousCard() }
                                dragOffset = 0
                            }
                        }
                )
            }
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }

    private var controls: some View {
        HStack(spacing: 20) {
            Button {
                withAnimation { previousCard() }
            } label: {
                Image(systemName: "chevron.left")
                    .font(.title2)
            }
            .disabled(currentIndex == 0)

            Button {
                if let word = currentWord {
                    viewModel.toggleLearned(word)
                }
            } label: {
                Label(
                    currentWord.map { viewModel.isLearned($0) ? "Learned" : "Mark Learned" } ?? "Mark Learned",
                    systemImage: currentWord.map { viewModel.isLearned($0) ? "checkmark.circle.fill" : "circle" } ?? "circle"
                )
                .font(.headline)
            }
            .buttonStyle(.borderedProminent)
            .tint(currentWord.map { viewModel.isLearned($0) ? .green : .accentColor } ?? .accentColor)

            Button {
                SpeechService.shared.speak(currentWord?.word ?? "")
            } label: {
                Image(systemName: "speaker.wave.2.fill")
                    .font(.title2)
            }

            Button {
                withAnimation { nextCard() }
            } label: {
                Image(systemName: "chevron.right")
                    .font(.title2)
            }
            .disabled(currentIndex >= words.count - 1)
        }
    }

    private func loadWords() {
        if let unitNum = unitNumber {
            words = viewModel.wordsForUnit(unitNum).shuffled()
        } else {
            words = viewModel.allWords.shuffled()
        }
        currentIndex = 0
        isFlipped = false
    }

    private func nextCard() {
        guard currentIndex < words.count - 1 else { return }
        currentIndex += 1
        isFlipped = false
        showExample = false
    }

    private func previousCard() {
        guard currentIndex > 0 else { return }
        currentIndex -= 1
        isFlipped = false
        showExample = false
    }
}
