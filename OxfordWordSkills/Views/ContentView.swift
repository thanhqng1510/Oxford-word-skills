import SwiftUI

struct ContentView: View {
    @State private var viewModel = ContentViewModel()
    @State private var columnVisibility = NavigationSplitViewVisibility.automatic

    var body: some View {
        NavigationSplitView(columnVisibility: $columnVisibility) {
            SidebarView(viewModel: viewModel)
        } detail: {
            DetailView(viewModel: viewModel)
        }
        .navigationTitle("Oxford Word Skills")
        .frame(minWidth: 900, minHeight: 600)
    }
}

struct DetailView: View {
    @Bindable var viewModel: ContentViewModel

    var body: some View {
        Group {
            switch viewModel.selectedNavigation {
            case .allWords:
                VocabularyListView(viewModel: viewModel)
            case .unit(let unitNumber):
                UnitDetailView(viewModel: viewModel, unitNumber: unitNumber)
            case .exercise(let type, let unitNumber):
                ExerciseContainerView(viewModel: viewModel, exerciseType: type, unitNumber: unitNumber)
            case .progress:
                ProgressDashboardView(viewModel: viewModel)
            }
        }
        .searchable(text: $viewModel.searchText, prompt: "Search words or definitions...")
    }
}
