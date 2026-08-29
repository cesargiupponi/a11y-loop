"""The unnamed-element sweep decides what the auditor is forced to rule on, so
its job is completeness: it must not stay silent about a control whose name was
never written down, however reasonable the derived name sounds."""

from __future__ import annotations

from a11y_loop.sweep import unnamed_elements

ICON_ONLY_BUTTON = '''
struct Bar: View {
    var body: some View {
        Button { dismiss() } label: { Image(systemName: "xmark") }
            .accessibilityIdentifier("bar.cancel")
    }
}
'''

LABELLED_BUTTON = '''
struct Bar: View {
    var body: some View {
        Button { dismiss() } label: { Image(systemName: "xmark") }
            .accessibilityLabel("Cancel")
            .accessibilityIdentifier("bar.cancel")
    }
}
'''

TITLED_BUTTON = '''
struct Bar: View {
    var body: some View {
        Button("Cancel") { dismiss() }
            .accessibilityIdentifier("bar.cancel")
    }
}
'''

INTERPOLATED = '''
struct Bar: View {
    var body: some View {
        ForEach(rows) { row in
            Text(row.title)
                .accessibilityIdentifier("row.\\(row.id)")
        }
    }
}
'''


def test_icon_only_control_is_listed():
    """`xmark` announces as "Close", which sounds fine and is still unauthored."""
    assert unnamed_elements(ICON_ONLY_BUTTON) == ["bar.cancel"]


def test_explicit_label_is_not_listed():
    assert unnamed_elements(LABELLED_BUTTON) == []


def test_visible_title_is_not_listed():
    """A visible title names the control; it needs no separate label."""
    assert unnamed_elements(TITLED_BUTTON) == []


def test_interpolated_identifiers_are_skipped():
    """`row.\\(row.id)` is not an anchor anything can be checked against."""
    assert unnamed_elements(INTERPOLATED) == []


COMPOSITE_ROW = '''
struct Row: View {
    var body: some View {
        HStack {
            Text(expense.title)
            Spacer()
            Text(expense.amount, format: .currency(code: "USD"))
        }
        .accessibilityIdentifier("row.container")
    }
}
'''

GROUPED_ROW = COMPOSITE_ROW.replace(
    '.accessibilityIdentifier("row.container")',
    '.accessibilityIdentifier("row.container")\n        .accessibilityElement(children: .combine)',
)


def test_composite_without_stated_grouping_is_listed():
    from a11y_loop.sweep import ungrouped_composites

    assert ungrouped_composites(COMPOSITE_ROW) == ["row.container"]


def test_composite_with_stated_grouping_is_not_listed():
    from a11y_loop.sweep import ungrouped_composites

    assert ungrouped_composites(GROUPED_ROW) == []
