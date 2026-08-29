import XCTest

/// Captures accessibility evidence per screen:
///  - native `performAccessibilityAudit` issues (Xcode 15+ audit engine)
///  - full element-tree dump (`debugDescription`)
///  - screenshot
/// Everything is attached to the test result; the capture driver extracts it
/// with `xcrun xcresulttool export attachments`.
final class A11yCaptureTests: XCTestCase {

    struct CapturedIssue: Codable {
        let auditTypes: [String]
        let compactDescription: String
        let detailedDescription: String
        let elementDescription: String
    }

    struct ScreenCapture: Codable {
        let app: String
        let screen: String
        let issues: [CapturedIssue]
        let tree: String
    }

    private func auditTypeNames(_ type: XCUIAccessibilityAuditType) -> [String] {
        var names: [String] = []
        if type.contains(.contrast) { names.append("contrast") }
        if type.contains(.elementDetection) { names.append("elementDetection") }
        if type.contains(.hitRegion) { names.append("hitRegion") }
        if type.contains(.sufficientElementDescription) { names.append("sufficientElementDescription") }
        if type.contains(.dynamicType) { names.append("dynamicType") }
        if type.contains(.textClipped) { names.append("textClipped") }
        if type.contains(.trait) { names.append("trait") }
        if names.isEmpty { names.append("other(\(type.rawValue))") }
        return names
    }

    private func captureScreen(app: XCUIApplication, appName: String, screen: String) throws {
        var issues: [CapturedIssue] = []
        try app.performAccessibilityAudit(for: .all) { issue in
            issues.append(
                CapturedIssue(
                    auditTypes: self.auditTypeNames(issue.auditType),
                    compactDescription: issue.compactDescription,
                    detailedDescription: issue.detailedDescription,
                    elementDescription: issue.element.map { "\($0)" } ?? "<none>"
                )
            )
            return true // collected, do not fail the test
        }

        let capture = ScreenCapture(
            app: appName,
            screen: screen,
            issues: issues,
            tree: app.debugDescription
        )

        let encoder = JSONEncoder()
        encoder.outputFormatting = [.prettyPrinted, .sortedKeys]

        let json = XCTAttachment(data: try encoder.encode(capture), uniformTypeIdentifier: "public.json")
        json.name = "\(screen).json"
        json.lifetime = .keepAlways
        add(json)

        let shot = XCTAttachment(screenshot: XCUIScreen.main.screenshot())
        shot.name = "\(screen).png"
        shot.lifetime = .keepAlways
        add(shot)
    }

    func testCaptureAllScreens() throws {
        let app = XCUIApplication()
        app.launch()
        let appName = "Ledgerly"

        // 1. Expense list (default tab)
        XCTAssertTrue(app.navigationBars["Expenses"].waitForExistence(timeout: 10))
        try captureScreen(app: app, appName: appName, screen: "expenseList")

        // 2. Expense detail — target the row by identifier; cells.firstMatch is
        // the section header ("This month"), which is not tappable.
        app.descendants(matching: .any)["expense.row.0"].firstMatch.tap()
        XCTAssertTrue(app.navigationBars["Expense"].waitForExistence(timeout: 5))
        try captureScreen(app: app, appName: appName, screen: "expenseDetail")
        app.navigationBars.buttons.firstMatch.tap() // back

        // 3. Add expense (sheet)
        app.buttons["expenses.add"].tap()
        XCTAssertTrue(app.navigationBars["Add expense"].waitForExistence(timeout: 5))
        try captureScreen(app: app, appName: appName, screen: "addExpense")
        app.buttons["add.cancel"].tap()

        // 4. Stats tab
        app.tabBars.buttons.element(boundBy: 1).tap()
        XCTAssertTrue(app.navigationBars["Stats"].waitForExistence(timeout: 5))
        try captureScreen(app: app, appName: appName, screen: "stats")

        // 5. Settings tab
        app.tabBars.buttons.element(boundBy: 2).tap()
        XCTAssertTrue(app.navigationBars["Settings"].waitForExistence(timeout: 5))
        try captureScreen(app: app, appName: appName, screen: "settings")
    }
}
