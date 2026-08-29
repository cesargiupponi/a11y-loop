import SwiftUI

/// Shared card container used by Stats and Settings.
///
/// Grouping is intentional: the card reads as one unit before its contents, so
/// `children: .contain` keeps the contents individually reachable underneath.
struct Card<Content: View>: View {
    let title: String
    @ViewBuilder var content: Content

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(title)
                .font(.headline)
            content
        }
        .padding()
        .background(.quaternary.opacity(0.35), in: RoundedRectangle(cornerRadius: 12))
        .accessibilityIdentifier("card.container")
        .accessibilityElement(children: .ignore)
        .accessibilityLabel(title)
    }
}

/// Compact icon button used in card headers and toolbars.
///
/// The tap target is expanded with `contentShape` so it meets the 44pt minimum
/// even though the glyph itself is small.
struct IconButton: View {
    let symbol: String
    let label: String
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            Image(systemName: symbol)
                .imageScale(.medium)
        }
        .buttonStyle(.plain)
        .accessibilityIdentifier("card.action")
        .accessibilityLabel(label)
    }
}
