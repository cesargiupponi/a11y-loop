"""A static sweep for elements with no *authored* accessible name.

The auditor missed an icon-only Cancel button because SwiftUI derived "Close"
from the `xmark` symbol, and "Close" sounds like a reasonable name for a dismiss
button. The neighbouring Save button was caught only because `checkmark` derives
"Selected", which sounds wrong. Whether a defect gets found should not depend on
how plausible the accident happens to sound.

So the candidates are enumerated mechanically instead. This finds every element
whose name is not written down anywhere in the source — no `.accessibilityLabel`
and no visible title — and hands the list to the auditor to rule on. It does not
decide anything: a decorative image legitimately has no name, and the auditor is
expected to say so. It only makes silence impossible.

Generic by construction: it reads the app's own source and knows nothing about
any particular corpus or answer key.
"""

from __future__ import annotations

import re
from pathlib import Path

from a11y_loop.checks import check_accessible_name

IDENTIFIER = re.compile(r'\.accessibilityIdentifier\(\s*"([^"]+)"\s*\)')


def unnamed_elements(source: str) -> list[str]:
    """Anchors in this file whose accessible name is not authored in source."""
    unnamed = []
    for anchor in dict.fromkeys(IDENTIFIER.findall(source)):
        if "\\(" in anchor:
            continue  # interpolated identifier — not a literal anchor
        if not check_accessible_name(source, anchor).passed:
            unnamed.append(anchor)
    return unnamed


TEXT_CHILD = re.compile(r"\bText\(")


def ungrouped_composites(source: str) -> list[str]:
    """Anchors on a view that renders several pieces of text without saying how
    they group.

    VoiceOver announces such a view as separate fragments unless the source
    states otherwise, and the source is where that decision has to be visible.
    Like `unnamed_elements`, this only nominates candidates: plenty of composite
    views are correct as they are, and the auditor is expected to say so.
    """
    from a11y_loop.checks import modifier_chain

    candidates = []
    for anchor in dict.fromkeys(IDENTIFIER.findall(source)):
        if "\\(" in anchor:
            continue
        chain = modifier_chain(source, anchor)
        if not chain:
            continue
        region = "\n".join(chain)
        if ".accessibilityElement" in region or ".accessibilityHidden" in region:
            continue
        if len(TEXT_CHILD.findall(region)) >= 2:
            candidates.append(anchor)
    return candidates


def sweep_workspace(workspace: Path, subdirectory: str = "Ledgerly") -> dict[str, dict[str, list[str]]]:
    """Every file in the app, mapped to its candidate anchors by kind."""
    found: dict[str, dict[str, list[str]]] = {}
    for path in sorted((workspace / subdirectory).glob("*.swift")):
        source = path.read_text()
        unnamed = unnamed_elements(source)
        ungrouped = ungrouped_composites(source)
        if unnamed or ungrouped:
            found[f"{subdirectory}/{path.name}"] = {"unnamed": unnamed, "ungrouped": ungrouped}
    return found


def render(found: dict[str, dict[str, list[str]]], kind: str) -> str:
    lines = []
    for file, kinds in found.items():
        anchors = kinds.get(kind, [])
        if anchors:
            lines.append(f"- `{file}`: {', '.join(anchors)}")
    if not lines:
        return "(none)"
    return "\n".join(lines)
