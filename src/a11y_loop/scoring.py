"""Scoring one arm's patched workspace against ground truth.

Primary metric: **verified-fix rate** — of the mechanical seeded violations, the
share whose check passes after the arm's patches are applied. Detection alone
does not count; the patch has to hold up.

Elements flagged is scored separately and includes report-only cases, where the
correct remedy is a human design decision and only the finding is expected.

That secondary number is deliberately named for what it measures. A finding is
matched to a case by the element it names, not by the defect it describes, so an
arm that reports *any* problem on an element is credited with flagging it. When
two defects share one element — a row that is both fragmented and low-contrast —
this over-credits both arms equally. The primary metric does not inherit the
weakness: it is decided by running each case's check against the patched source,
so a case only counts once the defect is actually gone.

Findings that match no seeded case are not automatically wrong: the clean app
carries genuine pre-existing issues. Those are reported as `pre_existing`;
only findings that match neither ground truth nor the clean capture count as
false positives.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from pathlib import Path

from a11y_loop.checks import run_check
from a11y_loop.corpus import ground_truth


@dataclass
class CaseOutcome:
    id: str
    screen: str
    violation_class: str
    fixable: bool
    detected: bool
    fix_verified: bool
    reason: str


@dataclass
class ArmScore:
    arm: str
    verified_fix_rate: float
    fixes_verified: int
    mechanical_total: int
    detection_rate: float
    detected: int
    cases_total: int
    false_positives: int
    pre_existing_reported: int
    duration_seconds: float
    cost_usd: float
    outcomes: list[CaseOutcome]
    traps_avoided: int = 0
    traps_total: int = 0

    def to_json(self) -> dict:
        d = asdict(self)
        d["outcomes"] = [asdict(o) if not isinstance(o, dict) else o for o in self.outcomes]
        return d

    def summary_line(self) -> str:
        return (
            f"{self.arm:9} verified-fix {self.fixes_verified}/{self.mechanical_total} "
            f"({self.verified_fix_rate:.0%})   elements flagged {self.detected}/{self.cases_total} "
            f"({self.detection_rate:.0%})   traps avoided {self.traps_avoided}/{self.traps_total}   "
            f"unmatched {self.false_positives}   "
            f"{self.duration_seconds:.0f}s   ${self.cost_usd:.2f}"
        )


def score_arm(
    arm: str,
    workspace: Path,
    findings: list[dict],
    duration_seconds: float = 0.0,
    cost_usd: float = 0.0,
) -> ArmScore:
    """Score one arm.

    `findings` are the arm's reported violations, each carrying at least an
    `anchor` (the element identifier it claims is defective).
    """
    gt = ground_truth()
    cases = gt["cases"]
    claimed = {f.get("anchor") for f in findings}

    outcomes: list[CaseOutcome] = []
    for case in cases:
        source = (workspace / case["file"]).read_text()
        detected = case["anchor"] in claimed
        if case["fixable"]:
            result = run_check(case["check"], source)
            verified, reason = result.passed, result.reason
        else:
            verified, reason = False, "report-only: no fix expected"
        outcomes.append(
            CaseOutcome(
                id=case["id"],
                screen=case["screen"],
                violation_class=case["violation_class"],
                fixable=case["fixable"],
                detected=detected,
                fix_verified=verified,
                reason=reason,
            )
        )

    mechanical = [o for o in outcomes if o.fixable]
    verified = [o for o in mechanical if o.fix_verified]
    # Traps are passed by NOT reporting and NOT patching, so they are excluded
    # from the detection rate and reported on their own line.
    traps = [o for o in outcomes if o.violation_class == "false_positive_trap"]
    detectable = [o for o in outcomes if o.violation_class != "false_positive_trap"]
    detected = [o for o in detectable if o.detected]

    seeded_anchors = {c["anchor"] for c in cases}
    unmatched = [f for f in findings if f.get("anchor") not in seeded_anchors]
    pre_existing = [f for f in unmatched if f.get("pre_existing")]
    false_positives = [f for f in unmatched if not f.get("pre_existing")]

    return ArmScore(
        arm=arm,
        verified_fix_rate=len(verified) / len(mechanical) if mechanical else 0.0,
        fixes_verified=len(verified),
        mechanical_total=len(mechanical),
        detection_rate=len(detected) / len(detectable) if detectable else 0.0,
        detected=len(detected),
        cases_total=len(detectable),
        traps_avoided=sum(1 for t in traps if t.fix_verified),
        traps_total=len(traps),
        false_positives=len(false_positives),
        pre_existing_reported=len(pre_existing),
        duration_seconds=duration_seconds,
        cost_usd=cost_usd,
        outcomes=outcomes,
    )


def save_score(score: ArmScore, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(score.to_json(), indent=2) + "\n")
