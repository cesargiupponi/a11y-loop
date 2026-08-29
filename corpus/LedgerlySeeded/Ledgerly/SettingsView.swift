import SwiftUI

struct SettingsView: View {
    @State private var currency = "USD"
    @State private var notifications = true
    @State private var roundUp = false

    var body: some View {
        Form {
            Section("General") {
                Picker("Currency", selection: $currency) {
                    ForEach(["USD", "EUR", "BRL"], id: \.self) { Text($0) }
                }
                .foregroundStyle(Color(white: 0.72))
                .accessibilityIdentifier("settings.currency")
                Toggle("", isOn: $notifications)
                    .accessibilityIdentifier("settings.notifications")
                Toggle("", isOn: $roundUp)
                    .accessibilityIdentifier("settings.roundup")
            }
            Section("About") {
                HStack { Text("Version"); Spacer(); Text("1.0.0") }
                    .accessibilityIdentifier("settings.version")
                Link(destination: URL(string: "https://example.com/privacy")!) {
                    Image(systemName: "hand.raised")
                }
                .accessibilityIdentifier("settings.privacy")
            }
        }
        .navigationTitle("Settings")
        .accessibilityIdentifier("screen.settings")
    }
}
