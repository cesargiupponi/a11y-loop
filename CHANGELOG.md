# Improvement Changelog

Every meaningful iteration gets an entry, connected to the evidence that guided the next decision.
Primary metric: **verified-fix rate** — % of seeded mechanical violations correctly detected AND patched with a green re-audit, on the fixed eval corpus (same cases for baseline and agent).

| Stage | What we tried and why | Evidence | Decision / learning |
|---|---|---|---|
| Baseline | One direct prompt (claude-opus-5): full screen source + audit JSON in, patch out. Single pass, no tools. | _pending_ | _pending_ |

<!-- Add one row per experiment. Include experiments later removed and what they taught. -->

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
- **Capture must not depend on process environment.** `TEST_RUNNER_A11Y_OUT`
  did not reach the runner, so captures landed in the simulator sandbox and the
  fixture directory came back empty while the test reported success. Switched to
  `XCTAttachment` + `xcresulttool export attachments`, which is inspectable and
  independent of sandbox paths — a silent empty fixture set would have poisoned
  every downstream metric.
