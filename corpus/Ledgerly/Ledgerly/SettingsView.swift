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
                .accessibilityIdentifier("settings.currency")
                Toggle("Monthly summary notifications", isOn: $notifications)
                    .accessibilityIdentifier("settings.notifications")
                Toggle("Round up amounts", isOn: $roundUp)
                    .accessibilityIdentifier("settings.roundup")
            }
            Section("About") {
                LabeledContent("Version", value: "1.0.0")
                Link(destination: URL(string: "https://example.com/privacy")!) {
                    Text("Privacy policy")
                }
                .accessibilityIdentifier("settings.privacy")
            }
        }
        .navigationTitle("Settings")
        .accessibilityIdentifier("screen.settings")
    }
}
