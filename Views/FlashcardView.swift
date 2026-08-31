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
                VStack(spacing: 16) {
                    if isFlipped {
                        // Back: definition + example + pronunciation
                        VStack(spacing: 10) {
                            Text(word.word)
                                .font(.largeTitle)
                                .fontWeight(.bold)
                                .multilineTextAlignment(.center)

                            HStack(spacing: 8) {
                                if !word.ipa.isEmpty {
                                    Text(word.ipa)
                                        .font(.headline)
                                        .foregroundStyle(.secondary)
                                }

                                if !word.partOfSpeech.isEmpty {
                                    Text(word.partOfSpeech)
                                        .font(.caption)
                                        .padding(.horizontal, 8)
                                        .padding(.vertical, 2)
                                        .background(.blue.opacity(0.15), in: Capsule())
                                }
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
                                    SpeechService.shared.speak(word.speechText)
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
                        // Front: word + pronunciation
                        VStack(spacing: 8) {
                            Text(word.word)
                                .font(.system(size: 40, weight: .bold, design: .rounded))
                                .multilineTextAlignment(.center)

                            if !word.ipa.isEmpty {
                                Text(word.ipa)
                                    .font(.title3)
                                    .foregroundStyle(.secondary)
                            }

                            Text("Tap to reveal definition")
                                .font(.callout)
                                .foregroundStyle(.tertiary)
                                .padding(.top, 4)
                        }
                    }
                }
                .padding(36)
                .frame(maxWidth: 480, minHeight: 280, maxHeight: 360)
                .background(Color(nsColor: .controlBackgroundColor), in: RoundedRectangle(cornerRadius: 20))
                .overlay(
                    RoundedRectangle(cornerRadius: 20)
                        .strokeBorder(Color(nsColor: .separatorColor).opacity(0.6), lineWidth: 1)
                )
                .shadow(color: .black.opacity(0.06), radius: 12, x: 0, y: 4)
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
                SpeechService.shared.speak(currentWord?.speechText ?? "")
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
