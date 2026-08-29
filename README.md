# a11y-loop

Agentic accessibility audit-and-fix loop for SwiftUI apps. Finds accessibility
violations on the **running** app, patches the safe classes in source, and
proves every fix with a re-audit.

> micro1 Agentic Workflows Hackathon entry (Aug 2026). Everything in this repo
> was built during the hackathon window unless marked otherwise; corpus apps
> under `corpus/` declare their own provenance and license.

## Who has this problem?

iOS teams shipping SwiftUI apps under the EU Accessibility Act (enforced since
June 2025) — and every blind or low-vision user who hits an unlabeled button
before the team does.

## What bottleneck makes it worth solving?

Manual VoiceOver audits are slow, need scarce expertise, and get skipped under
deadline pressure. Static linters can't see rendered reality: effective touch
targets, merged accessibility elements, rendered contrast. So violations ship.

## Does the agent solve it well?

The loop closes end-to-end: **capture** (native `performAccessibilityAudit` +
accessibility-tree dump on the simulator) → **audit** (agent localizes each
violation to file:line) → **fix** (agent patches mechanical classes on a git
branch; a human merges) → **verify** (deterministic re-check; on macOS, full
re-capture). Output is a PR-ready diff plus an audit report an engineer would
sign.

Measured on a seeded corpus with exact ground truth, against a fair baseline
(one direct prompt to the same model with the same inputs). Primary metric:
**verified-fix rate**. See `CHANGELOG.md` for the iteration story and
`eval/` for the corpus.

## Can another person reproduce the result?

Yes, without a Mac: fixtures are committed, and the judge path is

```
pip install -e .
a11y-loop eval
a11y-loop report
```

Full steps, versions, runtime and cost: `REPRODUCING.md` (lands with Phase 6).
The macOS capture path (`a11y-loop capture`) is optional and documented there too.

## Status

Phase 0 scaffold. Pipeline stages land per the phase plan; this README grows
with them.

<!-- TODO Phase 6: main failure mode + hot take -->
