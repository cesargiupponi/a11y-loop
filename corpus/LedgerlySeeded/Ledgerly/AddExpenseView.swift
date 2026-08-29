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
                TextField("", text: $title)
                    .accessibilityIdentifier("add.title")
                TextField("", text: $amount)
                    .keyboardType(.decimalPad)
                    .accessibilityIdentifier("add.amount")
                Picker("Category", selection: $category) {
                    ForEach(Expense.Category.allCases) { cat in
                        Text(cat.rawValue).tag(cat)
                    }
                }
                .accessibilityIdentifier("add.category")
                DatePicker("Date", selection: $date, displayedComponents: .date)
                    .font(.system(size: 13))
                    .accessibilityIdentifier("add.date")
            }
        }
        .navigationTitle("Add expense")
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItem(placement: .cancellationAction) {
                Button { dismiss() } label: { Image(systemName: "xmark") }
                    .accessibilityIdentifier("add.cancel")
            }
            ToolbarItem(placement: .confirmationAction) {
                Button { dismiss() } label: { Image(systemName: "checkmark") }
                    .disabled(title.isEmpty || Double(amount) == nil)
                    .accessibilityIdentifier("add.save")
            }
        }
        .accessibilityIdentifier("screen.addExpense")
    }
}
