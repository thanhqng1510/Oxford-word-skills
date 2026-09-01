import SwiftUI

struct ContentView: View {
    @State private var viewModel = ContentViewModel()
    @State private var columnVisibility = NavigationSplitViewVisibility.automatic
    var updateService: UpdateService

    var body: some View {
        NavigationSplitView(columnVisibility: $columnVisibility) {
            SidebarView(viewModel: viewModel)
        } detail: {
            DetailView(viewModel: viewModel)
        }
        .navigationTitle("Oxford Word Skills")
        .frame(minWidth: 900, minHeight: 600)
        .toolbar {
            ToolbarItem(placement: .primaryAction) {
                Picker("Voice Accent", selection: $viewModel.selectedVoice) {
                    ForEach(VoiceOption.supportedVoices) { option in
                        Text(option.shortLabel).tag(option)
                    }
                }
                .pickerStyle(.segmented)
                .help("Select Pronunciation Accent")
            }
        }
        // ── Auto-update ──────────────────────────────────────────────────────
        // Check for a newer release 2 s after launch (avoids blocking startup)
        .task {
            try? await Task.sleep(for: .seconds(2))
            await updateService.checkOnLaunch()
        }
        // Present the update sheet when a newer version is found
        .sheet(isPresented: Bindable(updateService).showingUpdateSheet) {
            UpdateAvailableView(service: updateService)
        }
        // "Already up to date" alert for manual checks
        .alert(
            "You're Up to Date",
            isPresented: Bindable(updateService).showingAlreadyLatestAlert
        ) {
            Button("OK") { }
        } message: {
            Text("Oxford Word Skills is already on the latest version.")
        }
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
