import SwiftUI

struct ExpenseDetailView: View {
    let expense: Expense
    @State private var isFlagged = false

    var body: some View {
        Form {
            Section("Details") {
                LabeledContent("Title", value: expense.title)
                LabeledContent("Amount", value: expense.amount, format: .currency(code: "USD"))
                LabeledContent("Category", value: expense.category.rawValue)
                LabeledContent("Date", value: expense.date, format: .dateTime.day().month().year())
                if !expense.note.isEmpty {
                    LabeledContent("Note", value: expense.note)
                }
            }
            Section {
                Button {
                    // duplicate this expense
                } label: {
                    Image(systemName: "plus.square.on.square")
                }
                .frame(width: 24, height: 24)
                .accessibilityLabel("Duplicate expense")
                .accessibilityIdentifier("detail.duplicate")
                Toggle("", isOn: $isFlagged)
                    .accessibilityIdentifier("detail.flag")
                Button(role: .destructive) {
                    // sample data is immutable; button demonstrates a destructive action
                } label: {
                    Image(systemName: "trash")
                }
                .accessibilityIdentifier("detail.delete")
            }
        }
        .navigationTitle("Expense")
        .navigationBarTitleDisplayMode(.inline)
        .accessibilityIdentifier("screen.expenseDetail")
    }
}
