import SwiftUI

struct SidebarView: View {
    @Bindable var viewModel: ContentViewModel
    @State private var expandedModules: Set<String> = []

    var body: some View {
        VStack(spacing: 0) {
            List {
                Section {
                    Button {
                        viewModel.selectedUnitNumber = nil
                        viewModel.selectedNavigation = .allWords
                    } label: {
                        Label("All Words (\(viewModel.totalWordCount))", systemImage: "text.book.closed")
                    }
                    .buttonStyle(.plain)

                    Button {
                        viewModel.selectedUnitNumber = nil
                        viewModel.selectedNavigation = .progress
                    } label: {
                        Label("Progress", systemImage: "chart.pie")
                    }
                    .buttonStyle(.plain)
                }

                Section("Modules") {
                    ForEach(Array(viewModel.modules.enumerated()), id: \.element.id) { index, module in
                        ModuleSection(
                            module: module,
                            index: index,
                            viewModel: viewModel
                        )
                    }
                }
            }
            .listStyle(.sidebar)

            SidebarFooter(viewModel: viewModel)
        }
    }
}

struct ModuleSection: View {
    let module: Module
    let index: Int
    @Bindable var viewModel: ContentViewModel
    @State private var isExpanded = false

    var body: some View {
        DisclosureGroup(isExpanded: $isExpanded) {
            ForEach(module.units) { unit in
                UnitRow(unit: unit, viewModel: viewModel)
            }
        } label: {
            HStack {
                VStack(alignment: .leading, spacing: 2) {
                    Text(module.title)
                        .font(.headline)
                    Text("\(module.wordCount) words")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
                Spacer()
                if module.wordCount > 0 {
                    ProgressView(value: module.progress)
                        .frame(width: 40)
                        .controlSize(.small)
                }
            }
            .contentShape(Rectangle())
        }
        .onAppear {
            if index == 0 { isExpanded = true }
        }
    }
}

struct UnitRow: View {
    let unit: Unit
    @Bindable var viewModel: ContentViewModel

    var body: some View {
        Button {
            viewModel.selectedUnitNumber = unit.number
            viewModel.selectedNavigation = .unit(unit.number)
        } label: {
            HStack {
                Text("\(unit.number).")
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .frame(width: 24, alignment: .trailing)
                VStack(alignment: .leading, spacing: 1) {
                    Text(unit.title)
                        .font(.callout)
                    Text("\(unit.words.count) words")
                        .font(.caption2)
                        .foregroundStyle(.secondary)
                }
                Spacer()
                if unit.words.count > 0 {
                    ProgressView(value: unit.progress)
                        .frame(width: 30)
                        .controlSize(.mini)
                }
            }
            .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
    }
}

struct SidebarFooter: View {
    @Bindable var viewModel: ContentViewModel

    var body: some View {
        VStack(spacing: 8) {
            Divider()
            HStack {
                Text("\(viewModel.totalLearnedCount) / \(viewModel.totalWordCount) learned")
                    .font(.caption)
                    .foregroundStyle(.secondary)
                Spacer()
                ProgressView(value: viewModel.overallProgress)
                    .frame(width: 60)
                    .controlSize(.small)
            }
            .padding(.horizontal)
            .padding(.bottom, 8)
        }
        .background(.bar)
    }
}
