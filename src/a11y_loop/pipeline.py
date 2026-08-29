"""The agent arm: audit -> fix -> verify, with a feedback loop.

Three roles, each given only what it needs:

- **Auditor** sees the captured evidence (accessibility tree, audit output, and
  the same screens re-rendered at an accessibility text size) plus the whole
  source tree via tools. It can follow a symptom on one screen to a cause in a
  shared component file, and it can measure a rendered tap target from the tree.
- **Fixer** edits the workspace, consulting a glossary so the same concept is
  named the same way on every screen.
- **Verifier** re-derives evidence after the edits and reports what is still
  wrong. Its findings feed one more Fixer round.

The Verifier never reads ground truth. It re-examines the patched source against
the original evidence, exactly as it would on a real app where no answer key
exists; on macOS the same patches are additionally re-captured in the simulator
by `a11y-loop verify`.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from a11y_loop.agent_runtime import run_agent
from a11y_loop.checks import modifier_chain
from a11y_loop.corpus import Screen, load_screens, prepare_workspace
from a11y_loop.paths import results_dir
from a11y_loop.sweep import render as render_sweep, sweep_workspace

JSON_BLOCK = re.compile(r"```json\s*(.*?)```", re.S)

AUDITOR_SYSTEM = """You audit SwiftUI apps for accessibility defects.

You are given evidence captured from the app while it was running: the
accessibility tree as VoiceOver traverses it, the output of Apple's
accessibility audit, and the same screens re-rendered at an accessibility text
size. You also have the full source tree, which you can read and search.

Work through both of the passes below on every screen. The second pass is what
the runtime evidence buys you, but it does not replace the first: most shipped
accessibility defects are still ordinary ones.

## Pass 1 — read the source for the ordinary defect classes

Check every interactive and informative element for:

- **No accessible name.** An icon-only button, a `Toggle("")`, a `TextField("")`.
- **Missing traits.** Section titles that should carry `.isHeader` so heading
  navigation works.
- **Fragmented elements.** A row whose children are announced separately
  instead of combined into one.
- **Decorative content exposed.** Ornamental glyphs that should be
  `.accessibilityHidden(true)`.
- **Undersized tap targets stated in source**, e.g. a `.frame` below 44pt.
- **Values lost.** A control that carries a measurement needs both a label and
  an `.accessibilityValue`; a merged element announces prose and loses the datum.

## Pass 2 — read the captured evidence for what source cannot show

Judge the app by what the evidence shows, not by what the source intends.
Three things the evidence tells you that source alone cannot:

1. What an element is actually called. An SF Symbol supplies a plausible name
   from the symbol itself, so a control with no label still appears to have one:
   a delete button announces as "Trash", a save button as "Selected". Compare
   what the tree announces against what the control does.
2. How large a tap target actually is. The tree carries rendered frames. A
   control can be far below the 44pt minimum with nothing in the source saying
   so.
3. What happens at accessibility text sizes. Text that fits at the default size
   may clip or truncate when rendered large.

When a screen's defect has no cause in that screen's file, search the source
tree for the shared component responsible. A container's identifier propagates
to its children in the tree dump, so several elements can report the same
identifier: when that happens, find the real element in the source of the
component that renders it and anchor your finding there.

Report a defect once, against the element that must change. Give each finding
exactly one defect: two problems on one element are two findings, or the second
gets lost behind the first.

One caveat specific to tap targets: a small `.frame` in the source does not mean
a small tap target, because a row or a container often expands it. Check the
rendered frame in the tree before reporting a hit-region defect, and if the tree
shows the target is already at least 44pt, it is not a defect. This applies to
tap targets, not to the other classes above.
"""

AUDITOR_PROMPT = """Audit the screen `{screen}` of the app in this workspace.

Its source file is `{file}`, but the cause of a defect may live in another file —
search the workspace when the evidence points outside this screen.

## Apple accessibility audit, default text size

{issues}

## Accessibility tree, default text size

```
{tree}
```

## Apple accessibility audit, accessibility text size (AX XXL)

{issues_large}

## Accessibility tree, accessibility text size (AX XXL)

```
{tree_large}
```

## Elements with no authored name

A static sweep of the source found these elements carrying an identifier but no
`.accessibilityLabel` and no visible title, so whatever VoiceOver announces for
them is derived rather than written:

{unnamed}

Rule on every one of them. Some are legitimate — a decorative image should have
no name, and a container that only groups other elements does not need one. Say
so and move on. But an interactive control in this list is a defect even when
the derived name happens to sound reasonable: `xmark` announces as "Close",
which reads fine for a dismiss button and is still nobody's decision. Judge
whether the name was authored, not whether it sounds plausible.

## Composite elements whose grouping is not stated

These render several pieces of text but say nothing about how they group, so
VoiceOver announces them as separate fragments unless that is intended:

{ungrouped}

Rule on these as well, as a question about grouping — separate from whether they
are named. An element can be correctly unnamed and still wrongly fragmented.

Read whatever source you need, then report every accessibility defect you can
support with this evidence.

Reply with one JSON block and nothing else:

```json
{{"findings": [
  {{"anchor": "<accessibilityIdentifier of the element>",
    "file": "<path of the file that must change>",
    "issue": "<what is wrong>",
    "evidence": "<the specific thing in the tree or audit that shows it>",
    "fix": "<the change you would make>",
    "mechanical": true}}
]}}
```

Set `"mechanical": false` for defects whose correct remedy is a design decision
a person should make — colour contrast, or choosing new type sizes. Report those
too; they are simply not yours to patch.
"""

FIXER_SYSTEM = """You repair accessibility defects in SwiftUI source.

Rules that matter more than the fix itself:

- Keep every existing `.accessibilityIdentifier(...)` exactly where it is. The
  UI test suite depends on them.
- Name controls after what they do in this app's own words, never after their
  icon. "Delete expense", not "Trash".
- Use the glossary so the same concept is named identically on every screen. Add
  to it whenever you name something new.
- Change only what the finding calls for. Do not restyle, refactor, or "improve"
  code you were not asked to touch.
- Do not patch findings marked `mechanical: false`. Those are for a human.

Every mechanical finding must end up in `applied` or in `skipped` with a reason.
A finding you neither applied nor skipped is the one that reaches users. When a
finding bundles a mechanical defect with a design concern, apply the mechanical
part and note the rest.
"""

FIXER_PROMPT = """Apply fixes to the workspace for these audited findings.

## Findings

```json
{findings}
```

## Glossary (shared naming across screens)

```
{glossary}
```

Edit the files directly. When you have finished, reply with one JSON block:

```json
{{"applied": [{{"anchor": "...", "file": "...", "change": "..."}}],
  "skipped": [{{"anchor": "...", "why": "..."}}],
  "glossary_additions": {{"<concept>": "<agreed wording>"}}}}
```
"""

VERIFIER_SYSTEM = """You check whether accessibility repairs actually hold.

You have no answer key. Re-derive the state of the code from the patched source
and the evidence captured before the repairs, and report honestly — including
repairs that were claimed but are not present, and anything the repairs broke.
"""

VERIFIER_PROMPT = """Repairs were just applied to this workspace for screen `{screen}`.

## What the auditor found

```json
{findings}
```

## What the fixer claims it changed

```json
{applied}
```

## The accessibility tree captured before the repairs

```
{tree}
```

Read the patched source and decide, for each finding, whether the defect is
genuinely resolved in the code as it now stands. Also flag anything the repairs
broke: a removed identifier, a changed behaviour, a control that lost its
meaning.

Reply with one JSON block:

```json
{{"unresolved": [{{"anchor": "...", "file": "...", "why": "...", "fix": "..."}}],
  "regressions": [{{"anchor": "...", "file": "...", "what_broke": "..."}}],
  "confirmed": ["<anchor>", "..."]}}
```
"""


def unaddressed_findings(
    findings: list[dict], applied: dict, before: dict[str, str], workspace: Path
) -> list[dict]:
    """Findings the Fixer neither changed nor consciously declined.

    Determined by comparing the source region around each finding's anchor
    before and after the Fixer ran — not by asking the model whether it was
    thorough. Self-assessment moved with the wording of the prompt; a diff does
    not. No ground truth is involved: this compares the agent's own findings
    against its own edits.
    """
    pending = []

    for finding in findings:
        anchor = finding.get("anchor")
        # A skip does not excuse a mechanical finding. Two defects can share an
        # element — a row can be both fragmented and low-contrast — and honouring
        # a skip by anchor let a report-only concern silently retire the
        # mechanical one next to it. Only what the auditor marked as a design
        # judgement may be declined.
        if not anchor or finding.get("mechanical") is False:
            continue

        path = finding.get("file") or ""
        candidates = [workspace / path] if path else []
        candidates += [workspace / f for f in before if anchor in before[f]]

        for candidate in candidates:
            key = str(candidate)
            if key not in before or not candidate.exists():
                continue
            was = "\n".join(modifier_chain(before[key], anchor))
            now = "\n".join(modifier_chain(candidate.read_text(), anchor))
            if was and was == now:
                pending.append({**finding, "why": "reported but the source is unchanged"})
            break

    return pending


def _parse(text: str, key: str, default):
    match = JSON_BLOCK.search(text)
    if not match:
        return default
    try:
        return json.loads(match.group(1)).get(key, default)
    except json.JSONDecodeError:
        return default


def _parse_all(text: str) -> dict:
    match = JSON_BLOCK.search(text)
    if not match:
        return {}
    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError:
        return {}


class Glossary:
    """Shared naming memory. Carrying agreed wording between screens is what
    keeps 'Delete expense' from becoming 'Remove item' two screens later."""

    def __init__(self, path: Path):
        self.path = path
        self.terms: dict[str, str] = {}
        path.parent.mkdir(parents=True, exist_ok=True)
        self._write()

    def add(self, terms: dict[str, str]) -> None:
        for concept, wording in (terms or {}).items():
            self.terms.setdefault(concept, wording)
        self._write()

    def render(self) -> str:
        if not self.terms:
            return "(empty — you are naming the first controls)"
        return "\n".join(f"{concept}: {wording}" for concept, wording in sorted(self.terms.items()))

    def _write(self) -> None:
        self.path.write_text(json.dumps(self.terms, indent=2) + "\n")


async def audit_screen(screen: Screen, large: Screen | None, workspace: Path) -> tuple[list[dict], float, float]:
    sweep = sweep_workspace(workspace)
    result = await run_agent(
        name=f"agent-audit-{screen.name}",
        system_prompt=AUDITOR_SYSTEM,
        prompt=AUDITOR_PROMPT.format(
            screen=screen.name,
            file=screen.file,
            issues=screen.issue_summary(),
            tree=screen.tree,
            issues_large=large.issue_summary() if large else "(not captured)",
            tree_large=large.tree if large else "(not captured)",
            unnamed=render_sweep(sweep, "unnamed"),
            ungrouped=render_sweep(sweep, "ungrouped"),
        ),
        allowed_tools=["Read", "Grep", "Glob"],
        cwd=workspace,
        max_turns=25,
    )
    return _parse(result.text, "findings", []), result.cost_usd, result.duration_seconds


async def fix_screen(
    screen: Screen, findings: list[dict], glossary: Glossary, workspace: Path, round_label: str = ""
) -> tuple[dict, float, float]:
    result = await run_agent(
        name=f"agent-fix{round_label}-{screen.name}",
        system_prompt=FIXER_SYSTEM,
        prompt=FIXER_PROMPT.format(
            findings=json.dumps(findings, indent=2), glossary=glossary.render()
        ),
        allowed_tools=["Read", "Edit", "Write", "Grep", "Glob"],
        cwd=workspace,
        max_turns=30,
        permission_mode="acceptEdits",
    )
    payload = _parse_all(result.text)
    glossary.add(payload.get("glossary_additions", {}))
    return payload, result.cost_usd, result.duration_seconds


async def verify_screen(
    screen: Screen, findings: list[dict], applied: dict, workspace: Path
) -> tuple[dict, float, float]:
    result = await run_agent(
        name=f"agent-verify-{screen.name}",
        system_prompt=VERIFIER_SYSTEM,
        prompt=VERIFIER_PROMPT.format(
            screen=screen.name,
            findings=json.dumps(findings, indent=2),
            applied=json.dumps(applied, indent=2),
            tree=screen.tree,
        ),
        allowed_tools=["Read", "Grep", "Glob"],
        cwd=workspace,
        max_turns=25,
    )
    return _parse_all(result.text), result.cost_usd, result.duration_seconds


async def run_agent_arm() -> dict:
    workspace = prepare_workspace("agent")
    screens = load_screens()
    by_name = {s.name: s for s in screens}
    glossary = Glossary(results_dir() / "workspaces" / "agent-glossary.json")

    all_findings: list[dict] = []
    verification: dict[str, dict] = {}
    cost = 0.0
    duration = 0.0

    for screen in screens:
        if screen.name.endswith("@axxl"):
            continue
        large = by_name.get(f"{screen.name}@axxl")

        findings, c, d = await audit_screen(screen, large, workspace)
        cost += c
        duration += d
        for finding in findings:
            finding["screen"] = screen.name
        all_findings.extend(findings)

        before = {
            str(path): path.read_text()
            for path in (workspace / "Ledgerly").glob("*.swift")
        }
        applied, c, d = await fix_screen(screen, findings, glossary, workspace)
        cost += c
        duration += d

        checked, c, d = await verify_screen(screen, findings, applied, workspace)
        cost += c
        duration += d
        verification[screen.name] = checked

        unresolved = (
            unaddressed_findings(findings, applied, before, workspace)
            + checked.get("unresolved", [])
            + [{**r, "issue": r.get("what_broke", "regression")} for r in checked.get("regressions", [])]
        )
        seen: set[str] = set()
        unresolved = [
            u for u in unresolved
            if u.get("anchor") and not (u["anchor"] in seen or seen.add(u["anchor"]))
        ]
        retried = 0
        if unresolved:
            _, c, d = await fix_screen(screen, unresolved, glossary, workspace, round_label="-retry")
            cost += c
            duration += d
            retried = len(unresolved)

        print(
            f"  agent/{screen.name:14} {len(findings):2} findings  "
            f"{len(checked.get('confirmed', [])):2} confirmed  {retried:2} re-fixed  "
            f"${c:.2f} running ${cost:.2f}"
        )

    (results_dir() / "agent-verification.json").write_text(json.dumps(verification, indent=2) + "\n")

    return {
        "workspace": workspace,
        "findings": all_findings,
        "cost_usd": cost,
        "duration_seconds": duration,
        "verification": verification,
    }
