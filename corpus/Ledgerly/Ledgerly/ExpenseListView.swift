import SwiftUI

struct ExpenseListView: View {
    @State private var showingAdd = false

    var body: some View {
        List {
            Section("This month") {
                ForEach(Array(SampleData.expenses.enumerated()), id: \.element.id) { index, expense in
                    NavigationLink(value: expense) {
                        ExpenseRow(expense: expense)
                    }
                    .accessibilityIdentifier("expense.row.\(index)")
                }
            }
        }
        .navigationTitle("Expenses")
        .navigationDestination(for: Expense.self) { expense in
            ExpenseDetailView(expense: expense)
        }
        .toolbar {
            ToolbarItem(placement: .primaryAction) {
                Button {
                    showingAdd = true
                } label: {
                    Image(systemName: "plus")
                }
                .accessibilityLabel("Add expense")
                .accessibilityIdentifier("expenses.add")
            }
        }
        .sheet(isPresented: $showingAdd) {
            NavigationStack { AddExpenseView() }
        }
        .accessibilityIdentifier("screen.expenseList")
    }
}

struct ExpenseRow: View {
    let expense: Expense

    var body: some View {
        HStack(spacing: 12) {
            Image(systemName: expense.category.symbol)
                .foregroundStyle(.tint)
                .frame(width: 28)
                .accessibilityHidden(true)
            VStack(alignment: .leading) {
                Text(expense.title)
                Text(expense.category.rawValue)
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
            Spacer()
            Text(expense.amount, format: .currency(code: "USD"))
                .monospacedDigit()
        }
        .accessibilityElement(children: .combine)
    }
}
