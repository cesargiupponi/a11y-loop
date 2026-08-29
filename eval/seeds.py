"""Declarative seeded-violation corpus.

Each Seed is an exact source transformation applied to the clean corpus app.
Because seeding is a recorded transformation rather than a hand edit, ground
truth is exact: we know precisely which accessibility defect exists, where it
lives, and what a correct fix restores.

`fixable=True`  -> mechanical class the Fixer agent is allowed to auto-patch.
`fixable=False` -> report-only class (contrast, Dynamic Type); detection is
                   scored, patching is not attempted, because the correct fix
                   is a design decision a human should make.

The `check` field is the portable (no-Mac) predicate used to decide whether a
patched source actually fixed the defect. On macOS the same case is also
re-verified by re-capturing the app and confirming the audit issue is gone.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any

APP = "Ledgerly"


@dataclass(frozen=True)
class Seed:
    id: str
    screen: str
    file: str
    violation_class: str
    fixable: bool
    anchor: str
    description: str
    find: str
    replace: str
    check: dict[str, Any] = field(default_factory=dict)
    # False when seeding *adds* a defective element rather than degrading an
    # existing one: there is nothing to compare against in the clean app.
    exists_in_clean: bool = True

    def as_case(self) -> dict[str, Any]:
        d = asdict(self)
        d.pop("find")
        d.pop("replace")
        return d


LIST = "Ledgerly/ExpenseListView.swift"
DETAIL = "Ledgerly/ExpenseDetailView.swift"
ADD = "Ledgerly/AddExpenseView.swift"
STATS = "Ledgerly/StatsView.swift"
SETTINGS = "Ledgerly/SettingsView.swift"
COMPONENTS = "Ledgerly/Components.swift"


def modifier_check(anchor: str, modifier: str) -> dict[str, Any]:
    return {"type": "modifier_present", "anchor": anchor, "modifier": modifier}


def name_check(anchor: str) -> dict[str, Any]:
    """A named element passes whether the name comes from an explicit label or
    from the view's own visible title; both are correct fixes."""
    return {"type": "accessible_name", "anchor": anchor}


SEEDS: list[Seed] = [
    # ---------------------------------------------------------------- expenseList
    Seed(
        id="S01",
        screen="expenseList",
        file=LIST,
        violation_class="missing_label",
        fixable=True,
        anchor="expenses.add",
        description="Icon-only 'plus' toolbar button loses its accessibility label, so VoiceOver announces only 'button'.",
        find='                .accessibilityLabel("Add expense")\n                .accessibilityIdentifier("expenses.add")',
        replace='                .accessibilityIdentifier("expenses.add")',
        check=name_check("expenses.add"),
    ),
    Seed(
        id="S02",
        screen="expenseList",
        file=LIST,
        violation_class="decorative_exposed",
        fixable=True,
        anchor="row.icon",
        description="Decorative category glyph is exposed to VoiceOver, adding a meaningless stop before every row.",
        find='                .accessibilityIdentifier("row.icon")\n                .accessibilityHidden(true)',
        replace='                .accessibilityIdentifier("row.icon")',
        check=modifier_check("row.icon", "accessibilityHidden"),
    ),
    Seed(
        id="S03",
        screen="expenseList",
        file=LIST,
        violation_class="fragmented_element",
        fixable=True,
        anchor="row.container",
        description="Expense row stops combining its children, so each row is read as three disconnected fragments.",
        find='        .accessibilityIdentifier("row.container")\n        .accessibilityElement(children: .combine)',
        replace='        .accessibilityIdentifier("row.container")',
        check=modifier_check("row.container", "accessibilityElement"),
    ),
    # -------------------------------------------------------------- expenseDetail
    Seed(
        id="S04",
        screen="expenseDetail",
        file=DETAIL,
        violation_class="missing_label",
        fixable=True,
        anchor="detail.delete",
        description="Destructive delete action becomes an unlabeled trash glyph — the highest-risk unlabeled control in the app.",
        find='                    Label("Delete expense", systemImage: "trash")',
        replace='                    Image(systemName: "trash")',
        check=name_check("detail.delete"),
    ),
    Seed(
        id="S05",
        screen="expenseDetail",
        file=DETAIL,
        violation_class="missing_label",
        fixable=True,
        anchor="detail.flag",
        description="Review toggle loses its visible title, leaving a switch with no announced purpose.",
        find='                Toggle("Flag for review", isOn: $isFlagged)',
        replace='                Toggle("", isOn: $isFlagged)',
        check=name_check("detail.flag"),
    ),
    Seed(
        id="S06",
        screen="expenseDetail",
        file=DETAIL,
        violation_class="hit_region",
        fixable=True,
        anchor="detail.duplicate",
        description="Duplicate-expense button is rendered at 24pt, below the 44pt minimum touch target.",
        find="            Section {\n                Toggle(",
        replace="""            Section {
                Button {
                    // duplicate this expense
                } label: {
                    Image(systemName: "plus.square.on.square")
                }
                .frame(width: 24, height: 24)
                .accessibilityLabel("Duplicate expense")
                .accessibilityIdentifier("detail.duplicate")
                Toggle(""",
        check={"type": "min_touch_target", "anchor": "detail.duplicate", "minimum": 44},
        exists_in_clean=False,
    ),
    # ----------------------------------------------------------------- addExpense
    Seed(
        id="S07",
        screen="addExpense",
        file=ADD,
        violation_class="missing_label",
        fixable=True,
        anchor="add.cancel",
        description="Cancel becomes an unlabeled 'xmark' glyph in the navigation bar.",
        find='                Button("Cancel") { dismiss() }',
        replace='                Button { dismiss() } label: { Image(systemName: "xmark") }',
        check=name_check("add.cancel"),
    ),
    Seed(
        id="S08",
        screen="addExpense",
        file=ADD,
        violation_class="missing_label",
        fixable=True,
        anchor="add.save",
        description="Save becomes an unlabeled 'checkmark' glyph — the primary action of the screen is unannounced.",
        find='                Button("Save") { dismiss() }',
        replace='                Button { dismiss() } label: { Image(systemName: "checkmark") }',
        check=name_check("add.save"),
    ),
    Seed(
        id="S09",
        screen="addExpense",
        file=ADD,
        violation_class="missing_label",
        fixable=True,
        anchor="add.title",
        description="Title field loses its placeholder, so the text field has no accessible name.",
        find='                TextField("Title", text: $title)',
        replace='                TextField("", text: $title)',
        check=name_check("add.title"),
    ),
    Seed(
        id="S10",
        screen="addExpense",
        file=ADD,
        violation_class="missing_label",
        fixable=True,
        anchor="add.amount",
        description="Amount field loses its placeholder — an unnamed numeric field in a money form.",
        find='                TextField("Amount", text: $amount)',
        replace='                TextField("", text: $amount)',
        check=name_check("add.amount"),
    ),
    Seed(
        id="R01",
        screen="addExpense",
        file=ADD,
        violation_class="dynamic_type",
        fixable=False,
        anchor="add.date",
        description="Date row pinned to a fixed 13pt system font, so it ignores Dynamic Type.",
        find='                DatePicker("Date", selection: $date, displayedComponents: .date)\n                    .accessibilityIdentifier("add.date")',
        replace='                DatePicker("Date", selection: $date, displayedComponents: .date)\n                    .font(.system(size: 13))\n                    .accessibilityIdentifier("add.date")',
        check={"type": "report_only"},
    ),
    # ---------------------------------------------------------------------- stats
    Seed(
        id="S11",
        screen="stats",
        file=STATS,
        violation_class="missing_trait",
        fixable=True,
        anchor="stats.header.categories",
        description="Section title loses its header trait, breaking VoiceOver heading navigation.",
        find='                    .accessibilityIdentifier("stats.header.categories")\n                    .accessibilityAddTraits(.isHeader)',
        replace='                    .accessibilityIdentifier("stats.header.categories")',
        check=modifier_check("stats.header.categories", "accessibilityAddTraits"),
    ),
    Seed(
        id="S12",
        screen="stats",
        file=STATS,
        violation_class="missing_trait",
        fixable=True,
        anchor="stats.header.largest",
        description="Second section title loses its header trait.",
        find='                    .accessibilityIdentifier("stats.header.largest")\n                    .accessibilityAddTraits(.isHeader)',
        replace='                    .accessibilityIdentifier("stats.header.largest")',
        check=modifier_check("stats.header.largest", "accessibilityAddTraits"),
    ),
    Seed(
        id="S13",
        screen="stats",
        file=STATS,
        violation_class="fragmented_element",
        fixable=True,
        anchor="stats.largest.row",
        description="Largest-expense rows stop combining, splitting each entry from its amount.",
        find='                    .accessibilityIdentifier("stats.largest.row")\n                    .accessibilityElement(children: .combine)',
        replace='                    .accessibilityIdentifier("stats.largest.row")',
        check=modifier_check("stats.largest.row", "accessibilityElement"),
    ),
    Seed(
        # THE HARD CASE. The naive fix (.combine) produces a plausible-sounding
        # announcement and silences the obvious symptom, but a chart bar carries
        # a measurement: the category is the label and the amount is the value.
        # Only an explicit label + value split is correct here, and a merged
        # element also re-exposes the sub-44pt bars as hit-region issues.
        id="S14",
        screen="stats",
        file=STATS,
        violation_class="semantic_value_loss",
        fixable=True,
        anchor="stats.bar",
        description=(
            "HARD CASE: chart bars collapse into a merged element. Children are combined "
            "instead of ignored, so each bar announces concatenated text ('Health, $18.75') "
            "with no accessibility value — the measurement is lost even though the bar "
            "plausibly 'has a label'."
        ),
        find="""                .accessibilityIdentifier("stats.bar")
                .accessibilityElement(children: .ignore)
                .accessibilityLabel(category.rawValue)
                .accessibilityValue(Text(total, format: .currency(code: "USD")))""",
        replace="""                .accessibilityIdentifier("stats.bar")
                .accessibilityElement(children: .combine)""",
        check={
            "type": "all",
            "checks": [
                modifier_check("stats.bar", "accessibilityLabel"),
                modifier_check("stats.bar", "accessibilityValue"),
            ],
        },
    ),
    # ------------------------------------------------------------------- settings
    Seed(
        id="S15",
        screen="settings",
        file=SETTINGS,
        violation_class="missing_label",
        fixable=True,
        anchor="settings.notifications",
        description="Notifications toggle loses its title, leaving an unnamed switch.",
        find='                Toggle("Monthly summary notifications", isOn: $notifications)',
        replace='                Toggle("", isOn: $notifications)',
        check=name_check("settings.notifications"),
    ),
    Seed(
        id="S16",
        screen="settings",
        file=SETTINGS,
        violation_class="missing_label",
        fixable=True,
        anchor="settings.roundup",
        description="Round-up toggle loses its title.",
        find='                Toggle("Round up amounts", isOn: $roundUp)',
        replace='                Toggle("", isOn: $roundUp)',
        check=name_check("settings.roundup"),
    ),
    Seed(
        id="S17",
        screen="settings",
        file=SETTINGS,
        violation_class="missing_label",
        fixable=True,
        anchor="settings.privacy",
        description="Privacy policy link becomes an unlabeled glyph, so the only legal link in the app is unreachable by name.",
        find="                    Text(\"Privacy policy\")",
        replace='                    Image(systemName: "hand.raised")',
        check=name_check("settings.privacy"),
    ),
    Seed(
        id="S18",
        screen="settings",
        file=SETTINGS,
        violation_class="fragmented_element",
        fixable=True,
        anchor="settings.version",
        description="Version row stops combining its children, so 'Version' and '1.0.0' are announced as two separate elements.",
        find='                    .accessibilityIdentifier("settings.version")\n                    .accessibilityElement(children: .combine)',
        replace='                    .accessibilityIdentifier("settings.version")',
        check=modifier_check("settings.version", "accessibilityElement"),
    ),
    Seed(
        id="R02",
        screen="settings",
        file=SETTINGS,
        violation_class="contrast",
        fixable=False,
        anchor="settings.currency",
        description="Currency picker is tinted light gray on white, below the 4.5:1 contrast minimum.",
        find='                .accessibilityIdentifier("settings.currency")',
        replace='                .foregroundStyle(Color(white: 0.72))\n                .accessibilityIdentifier("settings.currency")',
        check={"type": "report_only"},
    ),
    # ---------------------------------------------------------------- Corpus v2
    # Runtime-only defects. Corpus v1 measured reading comprehension: every
    # defect was plain in the source, and a one-shot prompt fixed all of them
    # without running anything. These are the cases where source inspection is
    # structurally insufficient — the symptom exists only once the app renders,
    # or it surfaces on a screen whose file does not contain the cause.
    Seed(
        id="H01",
        screen="stats",
        file=COMPONENTS,
        violation_class="ancestor_swallow",
        fixable=True,
        anchor="card.container",
        description=(
            "RUNTIME-ONLY, CROSS-FILE: the shared Card container switches from "
            "children: .contain to children: .ignore, so everything inside every card "
            "disappears from the accessibility tree. The symptom appears on Stats and "
            "Settings; the cause is in Components.swift, which neither screen's source "
            "contains. Reading either screen shows nothing wrong."
        ),
        find='        .accessibilityElement(children: .contain)',
        replace='        .accessibilityElement(children: .ignore)',
        check={
            "type": "modifier_argument_excludes",
            "anchor": "card.container",
            "modifier": "accessibilityElement",
            "forbidden": [".ignore"],
        },
    ),
    Seed(
        id="H02",
        screen="stats",
        file=COMPONENTS,
        violation_class="hit_region",
        fixable=True,
        anchor="card.action",
        description=(
            "RUNTIME-ONLY: the share button loses the padding and contentShape that gave "
            "it a 44pt target. No literal frame in the source states a size — the target "
            "collapses to the rendered glyph, which is only measurable on a running app."
        ),
        find="""            Image(systemName: symbol)
                .imageScale(.medium)
                .padding(12)
                .contentShape(Rectangle())""",
        replace="""            Image(systemName: symbol)
                .imageScale(.medium)""",
        check=modifier_check("card.action", "contentShape"),
    ),
    Seed(
        id="H03",
        screen="stats",
        file=STATS,
        violation_class="dynamic_type_clipping",
        fixable=True,
        anchor="stats.total",
        description=(
            "RUNTIME-ONLY: the month total is pinned to a single line at a fixed size, so "
            "it truncates at accessibility text sizes. At the default size it renders "
            "perfectly; the defect exists only in the accessibility-size capture."
        ),
        find="""                            .font(.title3.monospacedDigit())
                            .lineLimit(1)
                            .accessibilityIdentifier("stats.total")""",
        replace="""                            .font(.system(size: 22, weight: .semibold).monospacedDigit())
                            .lineLimit(1)
                            .fixedSize(horizontal: true, vertical: false)
                            .accessibilityIdentifier("stats.total")""",
        check={"type": "no_modifier", "anchor": "stats.total", "modifier": "fixedSize"},
    ),
    Seed(
        id="H04",
        screen="settings",
        file=SETTINGS,
        violation_class="dynamic_type_clipping",
        fixable=True,
        anchor="settings.limit.title",
        description=(
            "RUNTIME-ONLY: the budget row clips its label against its value at "
            "accessibility text sizes, because both are held on one line in a fixed HStack."
        ),
        find="""                        Text("Monthly limit")
                            .lineLimit(1)
                            .accessibilityIdentifier("settings.limit.title")""",
        replace="""                        Text("Monthly limit")
                            .lineLimit(1)
                            .fixedSize(horizontal: true, vertical: false)
                            .accessibilityIdentifier("settings.limit.title")""",
        check={"type": "no_modifier", "anchor": "settings.limit.title", "modifier": "fixedSize"},
    ),
]


def mechanical() -> list[Seed]:
    return [s for s in SEEDS if s.fixable]


def report_only() -> list[Seed]:
    return [s for s in SEEDS if not s.fixable]
