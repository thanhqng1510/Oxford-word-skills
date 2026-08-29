import SwiftUI

struct ExerciseContainerView: View {
    @Bindable var viewModel: ContentViewModel
    let exerciseType: ExerciseType
    let unitNumber: Int?

    var body: some View {
        switch exerciseType {
        case .flashcard:
            FlashcardView(viewModel: viewModel, unitNumber: unitNumber)
        case .definitionQuiz:
            QuizView(viewModel: viewModel, quizMode: .wordToDefinition, unitNumber: unitNumber)
        case .reverseQuiz:
            QuizView(viewModel: viewModel, quizMode: .definitionToWord, unitNumber: unitNumber)
        case .spelling:
            FillInBlankView(viewModel: viewModel, unitNumber: unitNumber)
        case .matching:
            MatchingView(viewModel: viewModel, unitNumber: unitNumber)
        case .categorize:
            CategorizationView(viewModel: viewModel, unitNumber: unitNumber)
        }
    }
}
