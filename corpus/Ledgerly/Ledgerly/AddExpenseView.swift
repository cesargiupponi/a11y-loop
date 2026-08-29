import SwiftUI

struct AddExpenseView: View {
    @Environment(\.dismiss) private var dismiss
    @State private var title = ""
    @State private var amount = ""
    @State private var category: Expense.Category = .food
    @State private var date = Date()

    var body: some View {
        Form {
            Section("New expense") {
                TextField("Title", text: $title)
                    .accessibilityIdentifier("add.title")
                TextField("Amount", text: $amount)
                    .keyboardType(.decimalPad)
                    .accessibilityIdentifier("add.amount")
                Picker("Category", selection: $category) {
                    ForEach(Expense.Category.allCases) { cat in
                        Text(cat.rawValue).tag(cat)
                    }
                }
                .accessibilityIdentifier("add.category")
                DatePicker("Date", selection: $date, displayedComponents: .date)
                    .accessibilityIdentifier("add.date")
            }
        }
        .navigationTitle("Add expense")
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItem(placement: .cancellationAction) {
                Button("Cancel") { dismiss() }
                    .accessibilityIdentifier("add.cancel")
            }
            ToolbarItem(placement: .confirmationAction) {
                Button("Save") { dismiss() }
                    .disabled(title.isEmpty || Double(amount) == nil)
                    .accessibilityIdentifier("add.save")
            }
        }
        .accessibilityIdentifier("screen.addExpense")
    }
}
