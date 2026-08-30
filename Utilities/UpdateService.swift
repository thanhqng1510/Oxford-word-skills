import AppKit
import Foundation

// MARK: - UpdateInfo

struct UpdateInfo: Identifiable {
    let id = UUID()
    let tag: String          // "v1.2.3"
    let version: String      // "1.2.3"  (v stripped)
    let releasePageURL: URL
    let downloadURL: URL     // browser_download_url of the *-macOS.zip asset
}

// MARK: - UpdateService

@Observable
@MainActor
final class UpdateService {

    // MARK: Phase

    enum Phase: Equatable {
        case idle
        case checking
        case downloadAvailable
        case downloading
        case extracting
        case relaunching
        case failed(String)
        case alreadyLatest
    }

    // MARK: State (read by views)

    private(set) var phase: Phase = .idle
    private(set) var downloadProgress: Double = 0   // 0.0 – 1.0
    private(set) var latestRelease: UpdateInfo?

    /// True while the sheet should be visible
    var showingUpdateSheet = false

    /// True to trigger the "already up to date" alert
    var showingAlreadyLatestAlert = false

    var isChecking: Bool { phase == .checking }

    // MARK: Constants

    private let repoSlug = "thanhqng1510/Oxford-word-skills"

    // MARK: - Public API

    /// Called automatically 2 s after launch. Silently does nothing on error.
    func checkOnLaunch() async {
        guard phase == .idle else { return }
        await performCheck(showAlreadyLatest: false)
    }

    /// Called from the "Check for Updates…" menu item.
    func checkManually() async {
        guard !isChecking else { return }
        await performCheck(showAlreadyLatest: true)
    }

    /// Starts download + extract + relaunch. Called by "Update Now" button.
    func startUpdate() async {
        guard let info = latestRelease else { return }
        phase = .downloading
        downloadProgress = 0

        do {
            let zipURL = try await download(info.downloadURL)

            // Hold on 100% download progress briefly so the user sees completion
            downloadProgress = 1.0
            try? await Task.sleep(for: .milliseconds(500))

            phase = .extracting
            let newAppURL = try await extract(zipURL)

            // Hold on extraction/installing state briefly for smooth transition
            try? await Task.sleep(for: .milliseconds(500))

            phase = .relaunching
            try await relaunch(with: newAppURL)
        } catch {
            phase = .failed(error.localizedDescription)
        }
    }

    /// "Later" button — dismiss without updating.
    func dismissUpdate() {
        showingUpdateSheet = false
        phase = .idle
    }

    /// Dismiss error state after a failed update.
    func dismissError() {
        phase = .idle
        showingUpdateSheet = false
    }

    // MARK: - Private: Check

    private func performCheck(showAlreadyLatest: Bool) async {
        phase = .checking

        do {
            if let info = try await fetchLatestRelease() {
                latestRelease = info
                phase = .downloadAvailable
                showingUpdateSheet = true
            } else {
                phase = .alreadyLatest
                if showAlreadyLatest {
                    showingAlreadyLatestAlert = true
                }
                // Brief display of .alreadyLatest then reset
                try? await Task.sleep(for: .milliseconds(200))
                if case .alreadyLatest = phase { phase = .idle }
            }
        } catch {
            // Silent on launch; surface error on manual check
            if showAlreadyLatest {
                phase = .failed(error.localizedDescription)
                showingUpdateSheet = true
            } else {
                phase = .idle
            }
        }
    }

    private func fetchLatestRelease() async throws -> UpdateInfo? {
        guard let url = URL(
            string: "https://api.github.com/repos/\(repoSlug)/releases/latest"
        ) else { throw UpdateError.invalidURL }

        var request = URLRequest(url: url, timeoutInterval: 10)
        request.setValue("application/vnd.github+json", forHTTPHeaderField: "Accept")
        request.setValue("2022-11-28", forHTTPHeaderField: "X-GitHub-Api-Version")

        let (data, response) = try await URLSession.shared.data(for: request)

        guard let http = response as? HTTPURLResponse else {
            throw UpdateError.badResponse
        }
        // 404 = no releases published yet
        if http.statusCode == 404 { return nil }
        guard http.statusCode == 200 else { throw UpdateError.badResponse }

        let info = try Self.parseGitHubRelease(data)

        guard Self.isNewerVersion(info.version, than: currentVersion()) else {
            return nil
        }
        return info
    }

    // MARK: - Pure / testable functions (static so test file can mirror them)

    /// Returns true when `remote` is a higher semver than `local`.
    /// Pads shorter component arrays with zeros: "2.0" vs "1.9.9" → 2 > 1 → true.
    static func isNewerVersion(_ remote: String, than local: String) -> Bool {
        let r = remote.split(separator: ".").compactMap { Int($0) }
        let l = local.split(separator: ".").compactMap { Int($0) }
        let count = max(r.count, l.count)
        for i in 0..<count {
            let rv = i < r.count ? r[i] : 0
            let lv = i < l.count ? l[i] : 0
            if rv > lv { return true }
            if rv < lv { return false }
        }
        return false  // equal
    }

    /// Parses the GitHub Releases API JSON response into an `UpdateInfo`.
    /// Throws `UpdateError` on malformed or incomplete data.
    static func parseGitHubRelease(_ data: Data) throws -> UpdateInfo {
        guard let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any] else {
            throw UpdateError.invalidJSON
        }
        guard let tagName = json["tag_name"] as? String,
              let htmlStr = json["html_url"] as? String,
              let htmlURL = URL(string: htmlStr),
              let assets = json["assets"] as? [[String: Any]] else {
            throw UpdateError.missingFields
        }

        // Pick the first asset whose name ends in .zip AND contains "macOS"
        let macAsset = assets.first { asset in
            guard let name = asset["name"] as? String else { return false }
            return name.hasSuffix(".zip") && name.contains("macOS")
        }
        guard let macAsset,
              let dlStr = macAsset["browser_download_url"] as? String,
              let dlURL = URL(string: dlStr) else {
            throw UpdateError.noMacAsset
        }

        let version = tagName.hasPrefix("v") ? String(tagName.dropFirst()) : tagName
        return UpdateInfo(
            tag: tagName,
            version: version,
            releasePageURL: htmlURL,
            downloadURL: dlURL
        )
    }

    func currentVersion() -> String {
        Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String ?? "0.0.0"
    }

    // MARK: - Private: Download

    private func download(_ url: URL) async throws -> URL {
        let delegate = DownloadDelegate { [weak self] progress in
            Task { @MainActor [weak self] in
                self?.downloadProgress = progress
            }
        }
        return try await delegate.startDownload(from: url)
    }

    // MARK: - Private: Extract (off main thread — ditto blocks)

    private func extract(_ zipURL: URL) async throws -> URL {
        let zipPath = zipURL.path
        return try await Task.detached(priority: .userInitiated) {
            let extractDir = FileManager.default.temporaryDirectory
                .appendingPathComponent("OxfordWordSkillsUpdate-\(UUID().uuidString)")
            try FileManager.default.createDirectory(
                at: extractDir, withIntermediateDirectories: true
            )

            let process = Process()
            process.executableURL = URL(fileURLWithPath: "/usr/bin/ditto")
            process.arguments = ["-x", "-k", zipPath, extractDir.path]
            let errPipe = Pipe()
            process.standardError = errPipe
            try process.run()
            process.waitUntilExit()

            guard process.terminationStatus == 0 else {
                let msg = String(
                    data: errPipe.fileHandleForReading.readDataToEndOfFile(),
                    encoding: .utf8
                ) ?? "unknown error"
                throw UpdateError.extractionFailed(msg)
            }

            let contents = try FileManager.default.contentsOfDirectory(
                at: extractDir, includingPropertiesForKeys: [.isDirectoryKey]
            )
            guard let appURL = contents.first(where: { $0.pathExtension == "app" }) else {
                throw UpdateError.appNotFound
            }
            return appURL
        }.value
    }

    // MARK: - Private: Relaunch (detached shell script)

    private func relaunch(with newAppURL: URL) async throws {
        // Capture paths and PID on @MainActor before leaving isolation
        let currentPath = Bundle.main.bundleURL.path
        let newPath = newAppURL.path
        let currentPID = ProcessInfo.processInfo.processIdentifier

        try await Task.detached(priority: .userInitiated) {
            let scriptPath = FileManager.default.temporaryDirectory
                .appendingPathComponent("oxford-update-\(UUID().uuidString).sh").path

            // The script runs after the app quits:
            // 1. Wait for the old process to fully terminate
            // 2. Clear quarantine so Gatekeeper won't block the new copy
            // 3. Replace the old .app with the new one
            // 4. Relaunch from the same path
            let script = """
            #!/bin/bash
            # Wait for previous app instance to terminate
            while kill -0 \(currentPID) 2>/dev/null; do
                sleep 0.1
            done

            xattr -rc "\(newPath)" 2>/dev/null || true
            rm -rf "\(currentPath)"
            mv "\(newPath)" "\(currentPath)"
            open "\(currentPath)"
            rm -- "$0"
            """

            try script.write(toFile: scriptPath, atomically: true, encoding: .utf8)

            let chmod = Process()
            chmod.executableURL = URL(fileURLWithPath: "/bin/chmod")
            chmod.arguments = ["+x", scriptPath]
            try chmod.run()
            chmod.waitUntilExit()

            // Launch script detached — intentionally do NOT call waitUntilExit
            let bash = Process()
            bash.executableURL = URL(fileURLWithPath: "/bin/bash")
            bash.arguments = [scriptPath]
            bash.standardInput = FileHandle.nullDevice
            bash.standardOutput = FileHandle.nullDevice
            bash.standardError = FileHandle.nullDevice
            try bash.run()
        }.value

        // Allow UI to render the relaunch state briefly, then cleanly terminate the process
        try? await Task.sleep(for: .milliseconds(800))
        exit(0)
    }
}

// MARK: - UpdateError

enum UpdateError: LocalizedError {
    case invalidURL
    case badResponse
    case invalidJSON
    case missingFields
    case noMacAsset
    case extractionFailed(String)
    case appNotFound

    var errorDescription: String? {
        switch self {
        case .invalidURL:              return "Invalid update server URL."
        case .badResponse:             return "Server returned an unexpected response."
        case .invalidJSON:             return "Could not parse the update information."
        case .missingFields:           return "Update data is missing required fields."
        case .noMacAsset:              return "No macOS download found in this release."
        case .extractionFailed(let m): return "Could not unzip the update: \(m)"
        case .appNotFound:             return "App bundle not found in the downloaded archive."
        }
    }
}

// MARK: - DownloadDelegate (URLSession progress tracking)

/// Wraps URLSessionDownloadTask in an async/await interface with per-byte progress callbacks.
private final class DownloadDelegate: NSObject, URLSessionDownloadDelegate, @unchecked Sendable {
    private let progressCallback: @Sendable (Double) -> Void
    private var continuation: CheckedContinuation<URL, Error>?
    private let lock = NSLock()

    init(progressCallback: @escaping @Sendable (Double) -> Void) {
        self.progressCallback = progressCallback
    }

    func startDownload(from url: URL) async throws -> URL {
        try await withCheckedThrowingContinuation { [weak self] cont in
            guard let self else { return }
            lock.withLock { self.continuation = cont }
            let session = URLSession(configuration: .default, delegate: self, delegateQueue: nil)
            session.downloadTask(with: url).resume()
        }
    }

    func urlSession(
        _ session: URLSession,
        downloadTask: URLSessionDownloadTask,
        didWriteData _: Int64,
        totalBytesWritten: Int64,
        totalBytesExpectedToWrite: Int64
    ) {
        guard totalBytesExpectedToWrite > 0 else { return }
        progressCallback(Double(totalBytesWritten) / Double(totalBytesExpectedToWrite))
    }

    func urlSession(
        _ session: URLSession,
        downloadTask: URLSessionDownloadTask,
        didFinishDownloadingTo location: URL
    ) {
        let dest = FileManager.default.temporaryDirectory
            .appendingPathComponent("OxfordWordSkills-\(UUID().uuidString).zip")
        do {
            try FileManager.default.moveItem(at: location, to: dest)
            resume(with: .success(dest))
        } catch {
            resume(with: .failure(error))
        }
    }

    func urlSession(_ session: URLSession, task: URLSessionTask, didCompleteWithError error: Error?) {
        if let error { resume(with: .failure(error)) }
    }

    private func resume(with result: Result<URL, Error>) {
        let cont = lock.withLock {
            let c = continuation
            continuation = nil
            return c
        }
        cont?.resume(with: result)
    }
}
