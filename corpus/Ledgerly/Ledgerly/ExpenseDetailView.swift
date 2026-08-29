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
                Toggle("Flag for review", isOn: $isFlagged)
                    .accessibilityIdentifier("detail.flag")
                Button(role: .destructive) {
                    // sample data is immutable; button demonstrates a destructive action
                } label: {
                    Label("Delete expense", systemImage: "trash")
                }
                .accessibilityIdentifier("detail.delete")
            }
        }
        .navigationTitle("Expense")
        .navigationBarTitleDisplayMode(.inline)
        .accessibilityIdentifier("screen.expenseDetail")
    }
}
