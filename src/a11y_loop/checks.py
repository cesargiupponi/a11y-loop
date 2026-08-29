"""Portable fix verification.

Every ground-truth case carries a `check` describing what a correct fix looks
like in source. These run on any OS, which is what makes the headline result
reproducible without a Mac. On macOS the same cases are additionally re-captured
in the simulator; see `verify.py`.

The checks are deliberately structural rather than textual: a fix counts only if
the required accessibility modifier is attached to the *same view expression* as
the anchor identifier, with a non-empty argument. Adding the modifier somewhere
else in the file does not pass.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# A SwiftUI view expression plus its modifier chain: the anchor line, the lines
# of the chain it belongs to, and the statement it hangs off.
MODIFIER_RE = re.compile(r"^\s*\.(\w+)\s*\(")


@dataclass(frozen=True)
class CheckResult:
    passed: bool
    reason: str


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip())


def _unbalanced(lines: list[str]) -> bool:
    """True while the region closes more brackets than it opens, i.e. it starts
    in the middle of a multi-line view expression."""
    text = "\n".join(lines)
    return text.count("}") > text.count("{") or text.count(")") > text.count("(")


def modifier_chain(source: str, anchor: str) -> list[str]:
    """Return the source region belonging to the view carrying `anchor`.

    Expands from the `.accessibilityIdentifier("<anchor>")` line across the
    contiguous modifier lines at the same indentation, then walks upward until
    brackets balance so that multi-line view expressions — `Button { … } label:
    { … }`, `Link(destination:) { … }` — are captured whole rather than from
    their closing brace. Returns [] when the anchor is absent.
    """
    lines = source.splitlines()
    anchor_pattern = f'.accessibilityIdentifier("{anchor}")'
    index = next((i for i, l in enumerate(lines) if anchor_pattern in l), None)
    if index is None:
        return []

    depth = _indent(lines[index])

    start = index
    while start - 1 >= 0 and MODIFIER_RE.match(lines[start - 1]) and _indent(lines[start - 1]) == depth:
        start -= 1

    end = index
    while end + 1 < len(lines) and MODIFIER_RE.match(lines[end + 1]) and _indent(lines[end + 1]) == depth:
        end += 1

    # Include the view expression the chain hangs off, spanning as many lines as
    # it takes for brackets to balance.
    start = max(start - 1, 0)
    while start > 0 and _unbalanced(lines[start : end + 1]):
        start -= 1

    return lines[start : end + 1]


def _modifier_argument(chain: list[str], modifier: str) -> str | None:
    """Text passed to `.modifier(...)` within the chain, if present."""
    for line in chain:
        match = re.search(rf"\.{modifier}\s*\((.*)", line)
        if match:
            return match.group(1).rstrip().rstrip(")")
    return None


def check_modifier_present(source: str, anchor: str, modifier: str) -> CheckResult:
    chain = modifier_chain(source, anchor)
    if not chain:
        return CheckResult(False, f"anchor {anchor!r} not found in source")

    argument = _modifier_argument(chain, modifier)
    if argument is None:
        return CheckResult(False, f".{modifier} not attached to {anchor!r}")
    if argument.strip() in {"", '""'}:
        return CheckResult(False, f".{modifier} on {anchor!r} has an empty argument")
    return CheckResult(True, f".{modifier}({argument.strip()}) attached to {anchor!r}")


# String literals that are never an accessible name, so they must not be
# mistaken for one: icon names, URLs, currency codes, the identifier itself.
NON_NAME_LITERALS = [
    re.compile(r'accessibilityIdentifier\(\s*"[^"]*"\s*\)'),
    re.compile(r'systemName:\s*"[^"]*"'),
    re.compile(r'systemImage:\s*"[^"]*"'),
    re.compile(r'URL\(string:\s*"[^"]*"\)'),
    re.compile(r'code:\s*"[^"]*"'),
]

STRING_LITERAL = re.compile(r'"([^"]+)"')


def check_accessible_name(source: str, anchor: str) -> CheckResult:
    """The element must expose a meaningful name to VoiceOver.

    SwiftUI derives that name either from an explicit `.accessibilityLabel` or
    from the view's own visible title (`Button("Cancel")`, `Toggle("Round up
    amounts", …)`). Both are correct fixes — restoring the visible title is
    usually the better one — so this checks the property rather than one
    syntax. Icon names are excluded deliberately: an SF Symbol supplies a
    plausible label that is not the element's meaning, which is the failure
    mode this project exists to catch.
    """
    chain = modifier_chain(source, anchor)
    if not chain:
        return CheckResult(False, f"anchor {anchor!r} not found in source")

    explicit = _modifier_argument(chain, "accessibilityLabel")
    if explicit is not None and explicit.strip() not in {"", '""'}:
        return CheckResult(True, f"explicit accessibilityLabel({explicit.strip()}) on {anchor!r}")

    text = "\n".join(chain)
    for pattern in NON_NAME_LITERALS:
        text = pattern.sub("", text)
    titles = [t for t in STRING_LITERAL.findall(text) if t.strip()]
    if titles:
        return CheckResult(True, f"visible title {titles[0]!r} names {anchor!r}")

    return CheckResult(False, f"{anchor!r} exposes no accessible name (no label, no visible title)")


def check_min_touch_target(source: str, anchor: str, minimum: int) -> CheckResult:
    """Frame on the anchored view must not pin it below the minimum target."""
    chain = modifier_chain(source, anchor)
    if not chain:
        return CheckResult(False, f"anchor {anchor!r} not found in source")

    frame = _modifier_argument(chain, "frame")
    if frame is None:
        return CheckResult(True, f"no explicit frame constrains {anchor!r}")

    sizes = [float(v) for v in re.findall(r"(?:width|height):\s*([0-9.]+)", frame)]
    if not sizes:
        return CheckResult(True, f"frame on {anchor!r} sets no fixed width or height")
    smallest = min(sizes)
    if smallest < minimum:
        return CheckResult(False, f"{anchor!r} constrained to {smallest:g}pt, below {minimum}pt")
    return CheckResult(True, f"{anchor!r} frame is {smallest:g}pt, at or above {minimum}pt")


def run_check(check: dict, source: str) -> CheckResult:
    kind = check.get("type")

    if kind == "modifier_present":
        return check_modifier_present(source, check["anchor"], check["modifier"])
    if kind == "accessible_name":
        return check_accessible_name(source, check["anchor"])
    if kind == "modifier_argument_excludes":
        chain = modifier_chain(source, check["anchor"])
        if not chain:
            return CheckResult(False, f"anchor {check['anchor']!r} not found in source")
        argument = _modifier_argument(chain, check["modifier"])
        if argument is None:
            return CheckResult(False, f".{check['modifier']} not attached to {check['anchor']!r}")
        for forbidden in check["forbidden"]:
            if forbidden in argument:
                return CheckResult(
                    False,
                    f".{check['modifier']}({argument.strip()}) on {check['anchor']!r} still uses {forbidden}",
                )
        return CheckResult(True, f".{check['modifier']}({argument.strip()}) on {check['anchor']!r}")
    if kind == "unchanged":
        chain = modifier_chain(source, check["anchor"])
        if not chain:
            return CheckResult(False, f"anchor {check['anchor']!r} not found in source")
        text = "\n".join(chain)
        needle = check["must_still_contain"]
        if needle.replace(" ", "") not in text.replace(" ", ""):
            return CheckResult(
                False,
                f"{check['anchor']!r} was modified ({needle} is gone); the running app showed "
                "nothing needed fixing here",
            )
        return CheckResult(True, f"{check['anchor']!r} correctly left unchanged")
    if kind == "no_modifier":
        chain = modifier_chain(source, check["anchor"])
        if not chain:
            return CheckResult(False, f"anchor {check['anchor']!r} not found in source")
        if _modifier_argument(chain, check["modifier"]) is not None:
            return CheckResult(
                False, f".{check['modifier']} still constrains {check['anchor']!r}"
            )
        return CheckResult(True, f"no .{check['modifier']} on {check['anchor']!r}")
    if kind == "min_touch_target":
        return check_min_touch_target(source, check["anchor"], check["minimum"])
    if kind == "all":
        results = [run_check(sub, source) for sub in check["checks"]]
        failed = [r for r in results if not r.passed]
        if failed:
            return CheckResult(False, "; ".join(r.reason for r in failed))
        return CheckResult(True, "; ".join(r.reason for r in results))
    if kind == "report_only":
        return CheckResult(False, "report-only case: detection is scored, fixing is not attempted")

    raise ValueError(f"unknown check type {kind!r}")
