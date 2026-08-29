"""Loading corpus evidence and preparing isolated working copies.

Both arms — baseline and agent — receive exactly the same inputs and each work
on a private copy of the seeded app, so neither can see or disturb the other's
edits. Fairness of the comparison depends on this being the only place either
arm obtains its material.
"""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from pathlib import Path

from a11y_loop.paths import fixtures_dir, repo_root, results_dir

SCREEN_TO_FILE = {
    "expenseList": "Ledgerly/ExpenseListView.swift",
    "expenseDetail": "Ledgerly/ExpenseDetailView.swift",
    "addExpense": "Ledgerly/AddExpenseView.swift",
    "stats": "Ledgerly/StatsView.swift",
    "settings": "Ledgerly/SettingsView.swift",
}


@dataclass(frozen=True)
class Screen:
    """One screen's evidence: what the audit engine reported, what the
    accessibility tree actually exposes, and the source that produced it."""

    name: str
    file: str
    source: str
    audit_issues: list[dict]
    tree: str

    def issue_summary(self) -> str:
        if not self.audit_issues:
            return "The audit engine reported no issues on this screen."
        lines = [
            f"- [{'/'.join(i['auditTypes'])}] {i['compactDescription']} — element: {i['elementDescription']}"
            for i in self.audit_issues
        ]
        return "\n".join(lines)


def ground_truth() -> dict:
    return json.loads((repo_root() / "eval" / "ground_truth.json").read_text())


def load_screens(fixture_app: str = "LedgerlySeeded", variant: str = "seeded") -> list[Screen]:
    gt = ground_truth()
    source_root = repo_root() / gt["seeded_source"]
    fixtures = fixtures_dir(fixture_app) / variant

    screens = []
    for name, rel in sorted(SCREEN_TO_FILE.items()):
        capture = json.loads((fixtures / f"{name}.json").read_text())
        screens.append(
            Screen(
                name=name,
                file=rel,
                source=(source_root / rel).read_text(),
                audit_issues=capture["issues"],
                tree=capture["tree"],
            )
        )
    return screens


def prepare_workspace(arm: str) -> Path:
    """A fresh copy of the seeded app for one arm to patch."""
    gt = ground_truth()
    src = repo_root() / gt["seeded_source"]
    dest = results_dir() / "workspaces" / arm
    if dest.exists():
        shutil.rmtree(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(src, dest, ignore=shutil.ignore_patterns("DerivedData", "*.xcodeproj", "build"))
    return dest
