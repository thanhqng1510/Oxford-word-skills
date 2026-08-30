import SwiftUI

struct ProgressDashboardView: View {
    @Bindable var viewModel: ContentViewModel

    var body: some View {
        ScrollView {
            VStack(spacing: 24) {
                header
                overallStats
                moduleGrid
            }
            .padding()
        }
    }

    private var header: some View {
        HStack {
            VStack(alignment: .leading) {
                Text("Progress Dashboard")
                    .font(.title)
                    .fontWeight(.bold)
                Text("Track your vocabulary learning")
                    .foregroundStyle(.secondary)
            }
            Spacer()
            Button("Reset All Progress", role: .destructive) {
                viewModel.resetAllProgress()
            }
            .buttonStyle(.bordered)
        }
    }

    private var overallStats: some View {
        HStack(spacing: 16) {
            StatCard(title: "Total Words", value: "\(viewModel.totalWordCount)", icon: "text.book.closed", color: .blue)
            StatCard(title: "Learned", value: "\(viewModel.totalLearnedCount)", icon: "checkmark.circle.fill", color: .green)
            StatCard(title: "Remaining", value: "\(viewModel.totalWordCount - viewModel.totalLearnedCount)", icon: "circle", color: .orange)
            StatCard(title: "Progress", value: "\(Int(viewModel.overallProgress * 100))%", icon: "chart.pie.fill", color: .purple)
        }
    }

    private var moduleGrid: some View {
        LazyVGrid(columns: [GridItem(.adaptive(minimum: 280))], spacing: 16) {
            ForEach(viewModel.modules) { module in
                ModuleProgressCard(module: module)
            }
        }
    }
}

struct StatCard: View {
    let title: String
    let value: String
    let icon: String
    let color: Color

    var body: some View {
        VStack(spacing: 8) {
            Image(systemName: icon)
                .font(.title2)
                .foregroundStyle(color)
            Text(value)
                .font(.title)
                .fontWeight(.bold)
            Text(title)
                .font(.caption)
                .foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity, minHeight: 100)
        .padding()
        .background(Color(nsColor: .controlBackgroundColor), in: RoundedRectangle(cornerRadius: 12))
        .overlay(
            RoundedRectangle(cornerRadius: 12)
                .strokeBorder(Color(nsColor: .separatorColor).opacity(0.6), lineWidth: 1)
        )
        .shadow(color: .black.opacity(0.04), radius: 6, x: 0, y: 2)
    }
}

struct ModuleProgressCard: View {
    let module: Module

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                Text(module.title)
                    .font(.headline)
                Spacer()
                Text("\(module.learnedCount)/\(module.wordCount)")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }

            ProgressView(value: module.progress)
                .tint(module.progress >= 1.0 ? .green : .accentColor)

            ForEach(module.units) { unit in
                HStack {
                    Text("\(unit.number).")
                        .font(.caption2)
                        .foregroundStyle(.secondary)
                        .frame(width: 20, alignment: .trailing)
                    Text(unit.title)
                        .font(.caption)
                        .lineLimit(1)
                    Spacer()
                    Text("\(unit.learnedCount)/\(unit.words.count)")
                        .font(.caption2)
                        .foregroundStyle(.secondary)
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
    }
}
