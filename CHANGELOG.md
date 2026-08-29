# Improvement Changelog

Every meaningful iteration gets an entry, connected to the evidence that guided the next decision.
Primary metric: **verified-fix rate** — % of seeded mechanical violations correctly detected AND patched with a green re-audit, on the fixed eval corpus (same cases for baseline and agent).

| Stage | What we tried and why | Evidence | Decision / learning |
|---|---|---|---|
| Baseline v0 | One direct prompt per screen (claude-opus-5), given the screen source, the audit output and the accessibility tree; single pass, no tools. | verified-fix **15/18 (83%)**, detection 18/20, 6 unmatched findings, $1.70, 120s | Two of the three failures were the same defect: the model rewrote the file and silently dropped `.accessibilityIdentifier` on the elements it fixed, breaking the UI test suite. The instruction, not the workflow, was at fault — so the constraint had to be stated to both arms before any comparison meant anything. |
| Baseline v1 | Re-ran with one added sentence, given to **both** arms: keep every existing `.accessibilityIdentifier`, the test suite depends on them. | verified-fix **18/18 (100%)**, detection 20/20, 6 unmatched findings, $1.76, 147s | Ceiling. A one-shot with the audit output and the accessibility tree already extracted solves the whole corpus. That is a real result, and it says the curation was the hard part: capturing the running app, isolating each screen, and handing over the tree is most of the work, and I had done it for both arms. Redefined the baseline to the status quo it should have modelled — reviewing source without running the app — see Baseline v2. |
| Baseline v2 | Removed the captured evidence from the prompt so the baseline models the actual status quo: reading SwiftUI source without running the app. | verified-fix **18/18 (100%)**, detection 20/20, 3 unmatched findings, $1.41, 134s | Ceiling again — and *cheaper and cleaner* than the curated baseline. The runtime evidence was not just unnecessary, it was adding noise. The corpus is the problem: every seeded defect is plainly visible in source, so it measures reading comprehension, not the capability this project claims. A defect you can see in a diff does not need a running app. Rebuilt the corpus around defects that only exist at runtime — see Corpus v2. |
| Corpus v2 | Added four defects that source inspection cannot settle: a shared `Card` component whose grouping breaks its contents on two screens while the cause sits in a third file, a tap target that collapses only when rendered, and two clipping defects that exist only at accessibility text sizes. Added a second capture pass at AX XXL. | 24 cases, 22 mechanical, 6 files, 5 screens × 2 text sizes | The share button measures **43×46pt** in the clean capture and **15×20pt** in the seeded one, with no frame in the source stating either. That number does not exist until the app runs — which is the project's whole argument in one measurement. |
| Agent v0 | Auditor (tree + audit + AX XXL evidence, repo search) → Fixer (edits, shared glossary) → Verifier (re-derives state, no answer key) → one re-fix round. | verified-fix **18/22 (82%)**, detection 19/24, $10.32, 953s — against baseline v2 on the same corpus at **20/22 (91%)**, $1.43, 141s | Lost to the baseline, and the failures say why. The agent won **H01** — the cross-file cause, the one case the baseline cannot reach — but dropped S06, S11 and S12, all ordinary defects plainly visible in source. I had written an auditor prompt that explained what runtime evidence reveals; it did that and stopped doing the basic review. Telling a model what is special about a task quietly redefines the task. |
| Agent v1 | Restructured the auditor into two explicit passes: pass 1 walks the ordinary defect classes in source, pass 2 reads the runtime evidence. Same tools, same model, same corpus. | verified-fix **20/22 (91%)**, detection 23/24, $9.77, 872s — baseline 20/22 (91%) | Recovered the ordinary cases and drew level. The split underneath the tie is the interesting part: the agent resolved **H01 and H02**, the two cases that need the app running, and the baseline resolved neither. Two arms reached the same score by solving different halves of the corpus. |
| Corpus v3 (**S06 reclassified**) | The agent kept "failing" S06, a button with `.frame(width: 24, height: 24)` seeded as an undersized tap target. Checked the capture before blaming the agent: inside a Form row it renders at **361×54pt**. | The tree entry for `detail.duplicate` in `fixtures/LedgerlySeeded/seeded/expenseDetail.json` | My answer key was wrong. The defect I seeded does not exist in the running app, the agent was right to decline it, and my scorer punished it for being right — while the baseline scored a point for patching code it could not check. Reclassified S06 as a **false-positive trap**: passed by leaving it alone, failed by "fixing" it. Baseline now fails it, agent passes. |
| Agent v2 (**removed**) | Added a general instruction to exercise restraint and not report things the evidence shows are fine. | verified-fix **18/22 (82%)** — down from 91%; newly failed S01, S02, S03, S07, all ordinary label and grouping defects | Removed. The same prompt-shaped failure as v0, in the opposite direction: a caution written for one case became a general reluctance, and the agent under-reported everywhere. Two swings in a row taught the actual lesson — the completeness problem was never going to be solved by better wording. Replaced with a caveat scoped to tap targets only, plus v3's mechanism. |
| Agent v3 | Stopped asking the model to police its own thoroughness. After the Fixer runs, the source region around every reported anchor is diffed against its pre-fix state; anything reported but unchanged, and not explicitly declined, is re-dispatched. Uses only the agent's own findings and its own edits — no answer key. Also made the runtime survive an agent that exhausts its turns instead of discarding a 13-minute evaluation. | verified-fix **21/22 (95%)** vs baseline **19/22 (86%)** — **+9pp**; detection 22/23, traps avoided 1/1, $9.44, 805s | The mechanism held where two rounds of wording did not. The agent resolves **H01** (cross-file cause), **H02** (runtime-only tap target) and declines **S06** (the trap); the baseline fails all three. It still lost **S07**, one icon-button label — the remaining gap is completeness on ordinary cases, not capability on hard ones. |
| Agent v4 | Chased the one case v3 still lost: **S07**, an icon-only Cancel button. The auditor had caught the Save button beside it and walked past Cancel. The reason is the project's own thesis turned on the agent: `checkmark` derives "Selected", which sounds wrong, so it got flagged; `xmark` derives **"Close"**, which sounds perfectly reasonable for a dismiss button, so it passed. Whether a defect is found should not depend on how plausible the accident sounds. Added a static sweep that lists every element with no *authored* name — no label, no visible title — and requires the auditor to rule on each. | S07 detected and verified; overall **21/22 (95%)** — unchanged, because **S03** regressed in the same run | S07 fixed, headline flat. The sweep listed `row.container` as unnamed, the auditor answered the naming question, and stopped short of the grouping defect on the same element. Fixing attention in one place moved it from another. |
| Agent v5 | Split the sweep in two, so grouping is asked as its own question: a second list nominates composite views that render several pieces of text without stating how they group. | **21/22 (95%)**, elements flagged 23/23, $9.65 | S03 still unfixed, and digging into why exposed **two bugs of mine rather than the agent's** — see v6. Also worth stating plainly: across v3, v4 and v5 the score held at 21/22 while the failing case moved (S07, S03, S03). Single-run case-level results are noisy; the aggregate is not. |
| Agent v6 | Two fixes, both mine. **(1)** The completeness ledger honoured the Fixer's skip by element, so a report-only contrast concern on `row.container` silently retired the mechanical grouping defect sitting on the same element. A skip may now only excuse what the auditor marked as a design judgement. **(2)** The secondary detection metric matched findings to cases by element alone, so that same contrast finding counted as "detecting" the grouping defect — which is how v5 reported a 23/23 that was not real. Renamed to *elements flagged* and documented as anchor-level, over-crediting both arms equally. | **20/22 (91%)**, elements flagged 22/23, $9.63 | The honest note: v5's "100% detection" was a measurement artefact, not a result. The primary metric never inherited the flaw, because it is decided by running each case's check against the patched source rather than by trusting what an arm claims. |
| Variance measurement | Stopped tuning and measured instead: three runs of each arm under the final configuration, reported as a mean with a range. | baseline **19.0/22, range 19–19**; agent **20.3/22, range 20–21** | Worth the $33 it cost. The baseline turns out to be perfectly repeatable — same three failures every run — which upgrades "the agent wins these three cases" from a single observation to a structural claim. It also retired my own 95% headline: that was the top of the agent's range, and the honest number is the mean, 92%. |

## Final comparison

Same corpus, same model (`claude-opus-5`), same constraints. **Three runs of each
arm**, because a single run is not a result on this corpus: reproduce with
`a11y-loop eval --repeat 3`, then `a11y-loop report`.

| Metric | Simple baseline | Agent solution | Change |
|---|---|---|---|
| **Verified-fix rate (primary), mean of 3** | 86% (19.0/22) | **92% (20.3/22)** | **+6pp** |
| Range across runs | 19–19 | 20–21 | — |
| False-positive traps avoided | 0/1 every run | **1/1 every run** | +1 |
| Elements flagged (anchor-level) | 21/23 | 22–23/23 | +1 to +2 |
| Unmatched findings | 5–6 | 4–5 | −1 |
| Cost per run | $1.47 | $9.71 | +$8.24 |
| Wall clock | 148s | 798s | +650s |
| Human time per screen | unchanged — both produce a diff for review | | |

### The variance is the interesting part

| | Cases failed, per run |
|---|---|
| Baseline | `H01, H02, S06` · `H01, H02, S06` · `H01, H02, S06` |
| Agent | `S03` · `S03, S14` · `S03, S14` |

**The baseline has zero variance.** Three runs, the same three failures, every
time. Those are not unlucky draws — they are the cases source-only review cannot
reach, and it misses them with perfect reliability: a cause in a file the screen
does not contain, a tap target that only exists once rendered, and a defect that
looks real in source and is not. **The agent resolves all three in all three
runs.**

Its own remaining gap splits in two: `S03` fails every run, so that is a real
limitation, while `S14` fails two runs in three, which is noise. Reporting the
best run as a 95% headline would have been reporting the noise.
| Builds + UI tests after repair (macOS) | pass | pass | — |
| Audit issues resolved on the rebuilt app | 14 | 11 | −3 |
| **New issues introduced** | 11 | **0** | **−11 for the agent** |

The rate is the headline, but the composition is the finding. Of the three cases
that separate the arms, all three turn on evidence from the running app:

| Case | What it is | Baseline | Agent |
|---|---|---|---|
| H01 | Shared `Card` component breaks grouping; symptom on two screens, cause in a third file | fail | **pass** |
| H02 | Tap target renders at 15×20pt with no frame in source stating it | fail | **pass** |
| S06 | Trap: source looks defective, app renders it at 361×54pt — correct action is none | fail (patches it) | **pass** |
| S07 | Icon-only Cancel button needs a label | pass | fail |

The agent costs about 7× the baseline and takes about 6× as long. For a
pre-release accessibility pass on a release candidate, at roughly $2 per screen,
that is the wrong axis to optimise; for a per-commit check it would be the
deciding one.

<!-- Add one row per experiment. Include experiments later removed and what they taught. -->

## Main failure mode

Not missed defects — both arms find nearly all of them. The failure mode is
**confident repair of code that was never broken**, and its cost is visible in
two places above: the baseline patches the trap in all three runs because from
source there is no way to know the target already renders at 361×54pt, and it
introduces eleven new audit issues while repairing — four Dynamic Type, seven
contrast — because it is editing code it cannot check. The final agent
configuration introduces none, but an earlier one introduced eight, including a
duplicated accessibility identifier that the portable checks could not see.
The mitigation is not a better prompt. It is that the output is a diff a
qualified human merges, and that the app is rebuilt and re-read before anyone
believes the repair.

## Lessons in flight

Observations that shaped design decisions; the strongest one becomes the hot take.

- **The accessibility tree is not the visual layout — and that gap is the whole
  problem.** Building the capture harness, `app.cells.firstMatch` selected the
  section header ("This month"), not the first expense row, so navigation
  silently went nowhere. The screenshot showed a list of expenses; the
  accessibility tree showed a header cell first. A human reading the screen and
  a screen reader traversing the tree disagreed on what "the first item" was —
  which is exactly the class of defect this project hunts, hit here by the
  harness itself before a single agent ran. Evidence:
  `fixtures/Ledgerly/clean/expenseList.json` (tree) vs `expenseList.png`.
- **"Has a label" is not "has the right label" — and the audit engine only
  checks the first.** Seeding 20 known defects and re-capturing showed Apple's
  `performAccessibilityAudit` catching just 6 of them. The misses are not
  obscure: SF Symbols silently supply a plausible-sounding label from the symbol
  name, so the audit sees a description and passes. Measured on the same
  element, clean vs seeded: delete `Delete expense` → **`Trash`**, save `Save` →
  **`Selected`**, privacy policy `Privacy policy` → **`Block`**. A screen reader
  now announces a destructive action as "Trash", the primary form action as
  "Selected", and a legal link as "Block". A missing label is detectable by
  tooling; a confidently wrong one is invisible to tooling *and* to sighted QA,
  which is precisely why these ship. Evidence: `fixtures/Ledgerly/clean/` vs
  `fixtures/LedgerlySeeded/seeded/` element trees.
  This is why the agent reads the accessibility tree and the source together
  instead of consuming audit output alone.
- **Capture must not depend on process environment.** `TEST_RUNNER_A11Y_OUT`
  did not reach the runner, so captures landed in the simulator sandbox and the
  fixture directory came back empty while the test reported success. Switched to
  `XCTAttachment` + `xcresulttool export attachments`, which is inspectable and
  independent of sandbox paths — a silent empty fixture set would have poisoned
  every downstream metric.
