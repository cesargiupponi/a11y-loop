import Foundation

struct Expense: Identifiable, Hashable {
    let id: UUID
    let title: String
    let amount: Double
    let category: Category
    let date: Date
    let note: String

    enum Category: String, CaseIterable, Identifiable {
        case food = "Food"
        case transport = "Transport"
        case housing = "Housing"
        case fun = "Fun"
        case health = "Health"

        var id: String { rawValue }

        var symbol: String {
            switch self {
            case .food: "fork.knife"
            case .transport: "bus.fill"
            case .housing: "house.fill"
            case .fun: "party.popper.fill"
            case .health: "cross.case.fill"
            }
        }
    }
}

enum SampleData {
    static let expenses: [Expense] = {
        let cal = Calendar.current
        func day(_ offset: Int) -> Date { cal.date(byAdding: .day, value: -offset, to: cal.startOfDay(for: Date(timeIntervalSince1970: 1_787_000_000)))! }
        return [
            Expense(id: UUID(uuidString: "00000000-0000-0000-0000-000000000001")!, title: "Groceries at Mercado Azul", amount: 62.40, category: .food, date: day(1), note: "Weekly shop"),
            Expense(id: UUID(uuidString: "00000000-0000-0000-0000-000000000002")!, title: "Metro card top-up", amount: 25.00, category: .transport, date: day(1), note: ""),
            Expense(id: UUID(uuidString: "00000000-0000-0000-0000-000000000003")!, title: "Rent", amount: 1450.00, category: .housing, date: day(3), note: "September"),
            Expense(id: UUID(uuidString: "00000000-0000-0000-0000-000000000004")!, title: "Cinema tickets", amount: 34.00, category: .fun, date: day(4), note: "Two seats"),
            Expense(id: UUID(uuidString: "00000000-0000-0000-0000-000000000005")!, title: "Pharmacy", amount: 18.75, category: .health, date: day(5), note: "Allergy meds"),
            Expense(id: UUID(uuidString: "00000000-0000-0000-0000-000000000006")!, title: "Lunch with team", amount: 41.10, category: .food, date: day(6), note: "Split later"),
            Expense(id: UUID(uuidString: "00000000-0000-0000-0000-000000000007")!, title: "Bike repair", amount: 55.00, category: .transport, date: day(8), note: "Brake pads"),
        ]
    }()

    static var totalsByCategory: [(Expense.Category, Double)] {
        Expense.Category.allCases.map { cat in
            (cat, expenses.filter { $0.category == cat }.reduce(0) { $0 + $1.amount })
        }
    }
}
