"""The baseline arm: one direct prompt with basic instructions.

Two modes, both single-pass and tool-free, differing only in what evidence the
prompt carries:

- `source_only` (default) models the status quo: an engineer or a review bot
  reading SwiftUI source without running the app. This is how accessibility is
  actually checked on most teams, and it is the baseline the headline number is
  measured against.
- `curated` additionally hands over the audit output and the accessibility tree
  that `capture` extracted. Kept because measuring it is what revealed how much
  of this job is evidence collection rather than reasoning — see the changelog.

The resource difference between `source_only` and the agent is deliberate and
declared: collecting runtime evidence is the capability under test, so an arm
that is handed that evidence is not measuring it. Both arms are given the same
task, the same model, the same corpus and the same constraints.
"""

from __future__ import annotations

import re
from pathlib import Path

from a11y_loop.agent_runtime import run_agent
from a11y_loop.corpus import Screen, load_screens, prepare_workspace

EVIDENCE = """
## Accessibility audit output for this screen

{issues}

## Accessibility tree as VoiceOver sees it

```
{tree}
```
"""

PROMPT = """You are fixing accessibility problems in a SwiftUI app.

Here is one screen of the app.

## Source: {file}

```swift
{source}
```
{evidence}
Find the accessibility problems on this screen and fix them.

Keep every existing `.accessibilityIdentifier(...)` exactly where it is — the UI
test suite depends on them.

Reply with exactly two blocks and nothing else:

1. A JSON block listing what you found:

```json
{{"findings": [{{"anchor": "<the accessibilityIdentifier of the element>", "issue": "<short description>"}}]}}
```

2. The complete corrected file:

```swift
<the entire file, with your fixes applied>
```
"""

JSON_BLOCK = re.compile(r"```json\s*(.*?)```", re.S)
SWIFT_BLOCK = re.compile(r"```swift\s*(.*?)```", re.S)


def _extract(text: str) -> tuple[list[dict], str | None]:
    import json

    findings: list[dict] = []
    match = JSON_BLOCK.search(text)
    if match:
        try:
            payload = json.loads(match.group(1))
            findings = payload.get("findings", [])
        except json.JSONDecodeError:
            findings = []

    swift = SWIFT_BLOCK.findall(text)
    patched = swift[-1].strip() + "\n" if swift else None
    return findings, patched


async def run_baseline(screen: Screen, workspace: Path, mode: str) -> tuple[list[dict], float, float]:
    evidence = (
        EVIDENCE.format(issues=screen.issue_summary(), tree=screen.tree)
        if mode == "curated"
        else ""
    )
    result = await run_agent(
        name=f"baseline-{mode}-{screen.name}",
        prompt=PROMPT.format(file=screen.file, source=screen.source, evidence=evidence),
        allowed_tools=[],
        max_turns=1,
    )

    findings, patched = _extract(result.text)
    if patched:
        (workspace / screen.file).write_text(patched)

    return findings, result.cost_usd, result.duration_seconds


async def run_baseline_arm(mode: str = "source_only") -> dict:
    workspace = prepare_workspace(f"baseline-{mode}")
    screens = load_screens()

    all_findings: list[dict] = []
    cost = 0.0
    duration = 0.0

    for screen in screens:
        findings, screen_cost, screen_duration = await run_baseline(screen, workspace, mode)
        for finding in findings:
            finding["screen"] = screen.name
        all_findings.extend(findings)
        cost += screen_cost
        duration += screen_duration
        print(f"  baseline/{screen.name:14} {len(findings):2} findings  ${screen_cost:.2f}  {screen_duration:.0f}s")

    return {
        "workspace": workspace,
        "findings": all_findings,
        "cost_usd": cost,
        "duration_seconds": duration,
    }
