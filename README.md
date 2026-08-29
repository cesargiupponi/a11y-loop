# a11y-loop

An agentic accessibility audit-and-fix loop for SwiftUI apps. It finds
accessibility defects on the **running** app, patches the mechanical ones in
source, and proves each repair rather than asserting it.

> micro1 Agentic Workflows Hackathon entry, August 2026. Everything here was
> built during the hackathon window. The corpus app under `corpus/Ledgerly/` was
> written for this project (MIT); no third-party app code, no private data.
>
> Reproduce the headline result on any OS: **[REPRODUCING.md](REPRODUCING.md)**.
> The iteration story, including the two experiments I removed and the point
> where the evidence proved my own answer key wrong: **[CHANGELOG.md](CHANGELOG.md)**.

## Who has this problem

iOS teams shipping SwiftUI under the European Accessibility Act, which became
enforceable in June 2025 — and, before them, every blind or low-vision user who
reaches a button the app never bothered to name.

## What bottleneck makes it worth solving

Accessibility review is manual, needs scarce expertise, and is the first thing
cut when a release is late. The tooling that is supposed to help has a specific
blind spot, and this project is built around it:

**Apple's own accessibility audit caught 6 of the 20 defects I deliberately
seeded.** Not because the misses were exotic, but because SwiftUI fills the gap
with something plausible. Strip the label off a button and an SF Symbol supplies
one from the icon name. Measured on the same elements, clean build versus seeded
build:

| Control | Announces before | Announces after |
|---|---|---|
| Delete expense | "Delete expense" | **"Trash"** |
| Save | "Save" | **"Selected"** |
| Privacy policy | "Privacy policy" | **"Block"** |

The audit engine sees a description and passes. A sighted reviewer sees a
correct-looking screen. A screen-reader user hears a destructive action called
"Trash", the primary action of a form called "Selected", and the app's only legal
link called "Block". A missing label is detectable; a confidently wrong one is
invisible to tooling and to QA, which is exactly why it ships.

## What the agent does

```
capture (macOS, once)     accessibility tree + Apple audit + screenshots,
                          at the default text size and at AX XXL
        │                 committed as fixtures
        ▼
Auditor    reads the evidence and the whole source tree; follows a symptom on
           one screen to a cause in a shared component file; measures rendered
           tap targets from the tree
        ▼
Fixer      patches the mechanical classes on a copy of the app, naming controls
           from a shared glossary so wording stays consistent across screens
        ▼
Verifier   re-derives what is still wrong, with no answer key; a deterministic
           ledger re-dispatches anything reported but left unchanged
        ▼
verify     on macOS: rebuild, re-run the UI tests, re-capture, and diff the
           audit against the pre-repair capture
```

Contrast and type-size decisions are reported, never auto-patched: the right
remedy is a design judgement, so it goes to a person. The Fixer works on a copy
and produces a diff a human merges.

## Does it work

Measured against a one-shot prompt with the same model on the same 24-case
corpus, over **three runs of each arm** — model runs are not deterministic, and
one run is not a result. Reproduce with `a11y-loop eval --repeat 3`.

| Verified-fix rate | Mean of 3 | Range |
|---|---|---|
| Simple baseline | 86% (19.0/22) | 19–19 |
| **Agent** | **92% (20.3/22)** | 20–21 |

Six points, and the composition matters more than the rate. **The baseline fails
the same three cases in every single run** — zero variance:

| Case | What it is | Baseline | Agent |
|---|---|---|---|
| H01 | Shared `Card` breaks grouping; symptom on two screens, cause in a third file | fail ×3 | **pass ×3** |
| H02 | Tap target renders at 15×20pt with no frame in source stating it | fail ×3 | **pass ×3** |
| S06 | Trap: source looks defective, app renders it at 361×54pt — correct action is none | fail ×3 | **pass ×3** |

Those three are not unlucky draws. They are what source-only review cannot
reach, and it misses them with perfect reliability. The agent resolves all three
in all three runs.

Its own gap is honest too: `S03` fails every run, a real limitation, and `S14`
fails two runs in three, which is noise. The best single run scored 95%; the
mean is 92%, and the mean is what this README reports.

## What verification on the real app says

The portable checks decide the headline metric. `a11y-loop verify` makes the
stronger claim available on macOS: rebuild each arm's patched app, re-run its UI
tests, re-capture it, and diff the audit against the pre-repair capture. Both
arms build and pass their tests. Then:

| | Baseline | Agent |
|---|---|---|
| Audit issues resolved | 14 | 11 |
| **New issues introduced** | 11 | **0** |
| Pre-existing issues resurfaced¹ | 0 | 3 |

¹ Issues the *clean* app also has, which reappear when correct grouping puts
elements back in the tree. Not damage the repair did, so they are counted
separately rather than held against either arm.

The baseline clears more raw audit issues and introduces eleven new ones doing
it — four Dynamic Type failures, seven contrast. It is editing code it cannot
check, and the audit only says so afterwards. The agent clears fewer and
introduces none.

This reverses what an earlier configuration measured: at the point the agent was
still carrying the ledger bug, it introduced eight issues of its own, including
writing a second accessibility identifier onto an element that already had one
(`settings.version-settings.version`). That defect was invisible to the portable
checks and surfaced only because the app was rebuilt and re-read — which is the
argument for verification, and for the output being a diff a person merges.

## The trap, and the main failure mode

One case in the corpus is a button carrying `.frame(width: 24, height: 24)`.
It reads as a touch target below the 44pt minimum, and I seeded it as a genuine
defect. It is not one: inside a `Form` row it renders at **361×54pt**.

I found that out because the agent kept "failing" the case. The capture proved
the agent right and my answer key wrong. So the case became a trap — passed by
leaving the code alone, failed by patching it. The baseline patches it every
time, because from source there is no way to tell.

That inverts the usual framing of the main failure mode. The risk in this system
is not that it misses defects; the baseline and the agent both find nearly all of
them. The risk is **confident repair of code that was never broken**, and the
only thing standing between an agent and that failure is evidence from the
running app.

## Hot take

Wording the prompt is not engineering the agent. Over three iterations, every
instruction I added to correct one failure mode manufactured its opposite. I
explained what runtime evidence reveals, and the auditor stopped doing the
ordinary source review it had been doing for free. I added a line about
restraint, and it under-reported everywhere — four ordinary defects it had
resolved the run before. Each fix was locally reasonable and globally a swing.

What ended it was giving up on asking the model to police itself. The Fixer's
thoroughness is now checked by diffing the source around every anchor it
reported: anything reported but unchanged, and not explicitly declined, gets
re-dispatched. No wording involved, nothing to drift. The reliable parts of this
system are the parts that do not depend on how I phrased something — and the
useful rule I would take to the next build is that a behaviour you can only get
by asking for it in the prompt is a behaviour you have not built yet.

## Layout

| Path | |
|---|---|
| `src/a11y_loop/` | pipeline, baseline, scoring, checks, capture, verification |
| `corpus/Ledgerly/` | the clean app; `LedgerlySeeded/` is generated, never hand-edited |
| `eval/seeds.py` | every seeded defect as an exact, inspectable transformation |
| `eval/ground_truth.json` | generated answer key — 24 cases, 22 scored |
| `fixtures/` | captured runtime evidence, committed so the eval runs anywhere |
| `trajectories/` | every agent run: instructions, tool calls, tool results, output |
| `results/` | scored runs and the patched app each arm produced |
