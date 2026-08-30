import SwiftUI

@main
struct OxfordWordSkillsApp: App {
    @State private var updateService = UpdateService()

    var body: some Scene {
        WindowGroup {
            ContentView(updateService: updateService)
        }
        .defaultSize(width: 1200, height: 800)
        .commands {
            CommandGroup(after: .appInfo) {
                Divider()
                Button("Check for Updates…") {
                    Task { await updateService.checkManually() }
                }
                .disabled(!updateService.canCheckForUpdates)
            }
        }
    }
}
