import SwiftUI

struct UpdateAvailableView: View {
    var service: UpdateService

    var body: some View {
        Group {
            switch service.phase {
            case .downloadAvailable:
                if let release = service.latestRelease {
                    availableContent(release: release)
                }
            case .downloading:
                downloadingContent
            case .extracting:
                extractingContent
            case .relaunching:
                relaunchingContent
            case .failed(let message):
                failedContent(message: message)
            default:
                EmptyView()
            }
        }
        .padding(36)
        .frame(width: 400)
        .fixedSize()
        // Prevent accidental dismissal mid-download
        .interactiveDismissDisabled(isDismissDisabled)
        .animation(.smooth, value: animationKey)
    }

    // MARK: - Phase content

    private func availableContent(release: UpdateInfo) -> some View {
        VStack(spacing: 24) {
            Image(systemName: "arrow.down.circle.fill")
                .font(.system(size: 52))
                .foregroundStyle(.blue)
                .symbolEffect(.bounce, value: release.id)

            VStack(spacing: 6) {
                Text("Update Available")
                    .font(.title2.bold())
                Text("Oxford Word Skills \(release.version) is ready")
                    .foregroundStyle(.secondary)
                Text("You're running \(service.currentVersion())")
                    .font(.caption)
                    .foregroundStyle(.tertiary)
            }

            HStack(spacing: 12) {
                Button("Later") {
                    service.dismissUpdate()
                }
                .keyboardShortcut(.cancelAction)

                Button("Update Now") {
                    Task { await service.startUpdate() }
                }
                .keyboardShortcut(.defaultAction)
                .buttonStyle(.borderedProminent)
            }
        }
    }

    private var downloadingContent: some View {
        VStack(spacing: 24) {
            Image(systemName: "arrow.down.circle")
                .font(.system(size: 52))
                .foregroundStyle(.blue)
                .symbolEffect(.pulse)

            Text("Downloading…")
                .font(.title2.bold())

            VStack(spacing: 8) {
                ProgressView(value: service.downloadProgress)
                    .progressViewStyle(.linear)
                    .frame(width: 300)

                Text("\(Int(service.downloadProgress * 100))%")
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .monospacedDigit()
                    .contentTransition(.numericText())
            }
        }
    }

    private var extractingContent: some View {
        VStack(spacing: 24) {
            Image(systemName: "archivebox.circle.fill")
                .font(.system(size: 52))
                .foregroundStyle(.orange)
                .symbolEffect(.pulse)

            Text("Installing…")
                .font(.title2.bold())

            ProgressView()
                .controlSize(.small)

            Text("The app will relaunch automatically.")
                .font(.callout)
                .foregroundStyle(.secondary)
        }
    }

    private var relaunchingContent: some View {
        VStack(spacing: 24) {
            Image(systemName: "checkmark.circle.fill")
                .font(.system(size: 52))
                .foregroundStyle(.green)
                .symbolEffect(.bounce)

            Text("Relaunching…")
                .font(.title2.bold())
        }
    }

    private func failedContent(message: String) -> some View {
        VStack(spacing: 24) {
            Image(systemName: "exclamationmark.triangle.fill")
                .font(.system(size: 52))
                .foregroundStyle(.red)

            VStack(spacing: 8) {
                Text("Update Failed")
                    .font(.title2.bold())
                Text(message)
                    .font(.callout)
                    .foregroundStyle(.secondary)
                    .multilineTextAlignment(.center)
                    .frame(maxWidth: 300)
            }

            Button("Dismiss") {
                service.dismissError()
            }
            .keyboardShortcut(.defaultAction)
        }
    }

    // MARK: - Helpers

    private var isDismissDisabled: Bool {
        switch service.phase {
        case .downloading, .extracting, .relaunching: return true
        default: return false
        }
    }

    /// Drives the `.animation` value — must change when the phase changes.
    private var animationKey: String {
        switch service.phase {
        case .idle:              return "idle"
        case .checking:          return "checking"
        case .downloadAvailable: return "available"
        case .downloading:       return "downloading"
        case .extracting:        return "extracting"
        case .relaunching:       return "relaunching"
        case .failed:            return "failed"
        case .alreadyLatest:     return "latest"
        }
    }
}
