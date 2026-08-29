import SwiftUI

@main
struct LedgerlyApp: App {
    var body: some Scene {
        WindowGroup {
            RootView()
        }
    }
}

struct RootView: View {
    var body: some View {
        TabView {
            NavigationStack { ExpenseListView() }
                .tabItem { Label("Expenses", systemImage: "list.bullet") }
                .accessibilityIdentifier("tab.expenses")
            NavigationStack { StatsView() }
                .tabItem { Label("Stats", systemImage: "chart.bar.fill") }
                .accessibilityIdentifier("tab.stats")
            NavigationStack { SettingsView() }
                .tabItem { Label("Settings", systemImage: "gearshape.fill") }
                .accessibilityIdentifier("tab.settings")
        }
    }
}
