import SwiftUI

struct StatsView: View {
    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 24) {
                Text("Spending by category")
                    .font(.title2.bold())
                    .accessibilityAddTraits(.isHeader)

                CategoryBarChart(totals: SampleData.totalsByCategory)

                Text("Largest expenses")
                    .font(.title2.bold())
                    .accessibilityAddTraits(.isHeader)

                ForEach(SampleData.expenses.sorted { $0.amount > $1.amount }.prefix(3)) { expense in
                    HStack {
                        Text(expense.title)
                        Spacer()
                        Text(expense.amount, format: .currency(code: "USD"))
                            .monospacedDigit()
                    }
                    .padding(.vertical, 4)
                    .accessibilityElement(children: .combine)
                }
            }
            .padding()
        }
        .navigationTitle("Stats")
        .accessibilityIdentifier("screen.stats")
    }
}

/// Custom bar chart built from plain shapes. Each bar is one accessibility
/// element combining the category name and its total, exposed as a value.
struct CategoryBarChart: View {
    let totals: [(Expense.Category, Double)]

    private var maxTotal: Double { max(totals.map(\.1).max() ?? 1, 1) }

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            ForEach(totals, id: \.0) { category, total in
                HStack(spacing: 8) {
                    Text(category.rawValue)
                        .font(.caption)
                        .frame(width: 72, alignment: .leading)
                    GeometryReader { proxy in
                        RoundedRectangle(cornerRadius: 4)
                            .fill(.tint)
                            .frame(width: max(proxy.size.width * total / maxTotal, 2))
                    }
                    .frame(height: 18)
                    Text(total, format: .currency(code: "USD"))
                        .font(.caption.monospacedDigit())
                }
                .accessibilityElement(children: .ignore)
                .accessibilityLabel(category.rawValue)
                .accessibilityValue(Text(total, format: .currency(code: "USD")))
            }
        }
        .accessibilityIdentifier("stats.chart")
    }
}
