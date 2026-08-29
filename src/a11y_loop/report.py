"""report — render the comparison the judges read.

Reads whatever arm results exist in `results/` and prints the baseline-vs-agent
table plus the per-case detail behind it. Every number here traces to a scored
run on the same corpus, and the per-case table is included so a disagreement can
be taken up with a specific case rather than the headline.
"""

from __future__ import annotations

import json
import sys

from a11y_loop.corpus import ground_truth
from a11y_loop.paths import repo_root, results_dir


def _load(name: str) -> dict | None:
    path = results_dir() / f"{name}.json"
    return json.loads(path.read_text()) if path.exists() else None


def _delta(baseline: float, agent: float, suffix: str = "") -> str:
    diff = agent - baseline
    sign = "+" if diff > 0 else ""
    return f"{sign}{diff:.0f}{suffix}" if abs(diff) >= 1 else f"{sign}{diff:.2f}{suffix}"


def run_report() -> int:
    baseline = _load("baseline-source_only")
    agent = _load("agent")

    if not baseline and not agent:
        print("report: no results yet. Run `a11y-loop eval`.", file=sys.stderr)
        return 1

    gt = ground_truth()
    print(f"\nCorpus: {gt['totals']['cases']} seeded violations "
          f"({gt['totals']['mechanical']} mechanical, {gt['totals']['report_only']} report-only) "
          f"across {gt['totals']['screens']} screens\n")

    if baseline and agent:
        rows = [
            (
                "Verified-fix rate (primary)",
                f"{baseline['verified_fix_rate']:.0%}",
                f"{agent['verified_fix_rate']:.0%}",
                _delta(baseline["verified_fix_rate"] * 100, agent["verified_fix_rate"] * 100, "pp"),
            ),
            (
                "Violations detected",
                f"{baseline['detected']}/{baseline['cases_total']}",
                f"{agent['detected']}/{agent['cases_total']}",
                _delta(baseline["detected"], agent["detected"]),
            ),
            (
                "Unmatched findings",
                str(baseline["false_positives"]),
                str(agent["false_positives"]),
                _delta(baseline["false_positives"], agent["false_positives"]),
            ),
            (
                "Cost per run",
                f"${baseline['cost_usd']:.2f}",
                f"${agent['cost_usd']:.2f}",
                _delta(baseline["cost_usd"], agent["cost_usd"]),
            ),
            (
                "Wall clock",
                f"{baseline['duration_seconds']:.0f}s",
                f"{agent['duration_seconds']:.0f}s",
                _delta(baseline["duration_seconds"], agent["duration_seconds"], "s"),
            ),
        ]
        width = max(len(r[0]) for r in rows)
        print(f"{'Metric':{width}}  {'Baseline':>10}  {'Agent':>10}  {'Change':>9}")
        print("-" * (width + 35))
        for label, b, a, d in rows:
            print(f"{label:{width}}  {b:>10}  {a:>10}  {d:>9}")

        print("\nPer-case outcomes (mechanical only):")
        bo = {o["id"]: o for o in baseline["outcomes"]}
        ao = {o["id"]: o for o in agent["outcomes"]}
        print(f"{'case':6} {'class':24} {'baseline':>9} {'agent':>7}")
        for case_id in sorted(bo):
            if not bo[case_id]["fixable"]:
                continue
            b = "pass" if bo[case_id]["fix_verified"] else "FAIL"
            a = "pass" if ao[case_id]["fix_verified"] else "FAIL"
            marker = "" if b == a else "   <-- differs"
            print(f"{case_id:6} {bo[case_id]['violation_class']:24} {b:>9} {a:>7}{marker}")
    else:
        only = baseline or agent
        print(f"Only one arm has results: {only['arm']}")
        print(f"  verified-fix {only['fixes_verified']}/{only['mechanical_total']} "
              f"({only['verified_fix_rate']:.0%})")

    for arm in ("baseline-source_only", "agent"):
        verify_path = results_dir() / f"verify-{arm.replace('baseline-source_only', 'baseline-source_only')}.json"
        if verify_path.exists():
            data = json.loads(verify_path.read_text())
            sim = data.get("simulator")
            if sim and sim.get("builds"):
                print(
                    f"\nSimulator verification ({arm}): builds={sim['builds']} "
                    f"ui_tests_pass={sim.get('ui_tests_pass')} "
                    f"audit issues resolved={sim.get('audit_issues_resolved')} "
                    f"introduced={sim.get('audit_issues_introduced')}"
                )

    print(f"\nRaw results: {results_dir().relative_to(repo_root())}/")
    return 0
