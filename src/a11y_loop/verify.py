"""verify — prove the repairs on the running app.

The portable checks decide the headline metric so judges can reproduce it
anywhere. This is the stronger claim available on macOS: rebuild the patched
workspace, re-capture it in the simulator, and compare the result against the
capture taken before the repairs.

It answers the question the checks cannot: did the app actually get better, and
did anything else get worse?
"""

from __future__ import annotations

import json
import platform
import shutil
import sys
from pathlib import Path

from a11y_loop.capture import _export_attachments, _latest_xcresult, _run, SIMULATOR, _scheme_name
from a11y_loop.checks import run_check
from a11y_loop.corpus import ground_truth
from a11y_loop.paths import fixtures_dir, repo_root, results_dir


def _issue_key(issue: dict) -> tuple:
    return ("/".join(issue["auditTypes"]), issue["compactDescription"], issue["elementDescription"])


def _load_capture(directory: Path) -> dict[str, dict]:
    return {p.stem: json.loads(p.read_text()) for p in directory.glob("*.json") if p.stem != "manifest"}


def portable_verify(arm: str) -> dict:
    """Re-run every ground-truth check against an arm's patched workspace."""
    workspace = results_dir() / "workspaces" / arm
    gt = ground_truth()
    results = []
    for case in gt["cases"]:
        source = (workspace / case["file"]).read_text()
        outcome = run_check(case["check"], source)
        results.append(
            {"id": case["id"], "passed": outcome.passed, "reason": outcome.reason}
        )
    return {"arm": arm, "checks": results, "passed": sum(r["passed"] for r in results)}


def simulator_verify(arm: str) -> dict:
    """Build and re-capture the patched workspace, then diff against the
    pre-repair capture of the same app."""
    workspace = results_dir() / "workspaces" / arm
    scheme = _scheme_name(workspace)

    generated = _run(["xcodegen", "generate"], cwd=workspace)
    if generated.returncode != 0:
        return {"arm": arm, "builds": False, "error": generated.stderr[-2000:]}

    built = _run(
        [
            "xcodebuild", "build",
            "-project", str(workspace / f"{scheme}.xcodeproj"),
            "-scheme", scheme,
            "-destination", f"platform=iOS Simulator,name={SIMULATOR}",
            "-derivedDataPath", str(workspace / "DerivedData"),
        ],
        cwd=workspace,
    )
    if "** BUILD SUCCEEDED **" not in built.stdout:
        errors = [l for l in built.stdout.splitlines() if "error:" in l]
        return {"arm": arm, "builds": False, "errors": errors[:20]}

    tested = _run(
        [
            "xcodebuild", "test",
            "-project", str(workspace / f"{scheme}.xcodeproj"),
            "-scheme", scheme,
            "-destination", f"platform=iOS Simulator,name={SIMULATOR}",
            "-derivedDataPath", str(workspace / "DerivedData"),
        ],
        cwd=workspace,
    )
    ui_tests_pass = "** TEST SUCCEEDED **" in tested.stdout
    if not ui_tests_pass:
        return {"arm": arm, "builds": True, "ui_tests_pass": False}

    after_dir = fixtures_dir(f"verify-{arm}") / "patched"
    _export_attachments(_latest_xcresult(workspace), after_dir)

    before = _load_capture(repo_root() / "fixtures" / "LedgerlySeeded" / "seeded")
    after = _load_capture(after_dir)

    per_screen = {}
    resolved = introduced = 0
    for screen, before_capture in sorted(before.items()):
        after_capture = after.get(screen)
        if not after_capture:
            continue
        before_issues = {_issue_key(i) for i in before_capture["issues"]}
        after_issues = {_issue_key(i) for i in after_capture["issues"]}
        gone = before_issues - after_issues
        new = after_issues - before_issues
        resolved += len(gone)
        introduced += len(new)
        per_screen[screen] = {
            "issues_before": len(before_issues),
            "issues_after": len(after_issues),
            "resolved": sorted(g[1] for g in gone),
            "introduced": sorted(n[1] for n in new),
        }

    return {
        "arm": arm,
        "builds": True,
        "ui_tests_pass": True,
        "audit_issues_resolved": resolved,
        "audit_issues_introduced": introduced,
        "per_screen": per_screen,
    }


def run_verify(app: str = "agent") -> int:
    """`app` names the arm whose workspace should be verified."""
    arm = app
    workspace = results_dir() / "workspaces" / arm
    if not workspace.exists():
        print(f"verify: no workspace for arm {arm!r}. Run `a11y-loop eval` first.", file=sys.stderr)
        return 1

    report = portable_verify(arm)
    print(f"verify: {report['passed']}/{len(report['checks'])} ground-truth checks pass in {arm}")

    if platform.system() == "Darwin" and shutil.which("xcodebuild"):
        print("verify: rebuilding and re-capturing the patched app in the simulator…")
        simulator = simulator_verify(arm)
        report["simulator"] = simulator
        if not simulator.get("builds"):
            print("verify: patched workspace does NOT build", file=sys.stderr)
        elif not simulator.get("ui_tests_pass"):
            print("verify: patched app builds but its UI tests fail", file=sys.stderr)
        else:
            print(
                f"verify: audit issues resolved {simulator['audit_issues_resolved']}, "
                f"introduced {simulator['audit_issues_introduced']}"
            )
    else:
        print("verify: not macOS — portable checks only (this is the judge path).")

    out = results_dir() / f"verify-{arm}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n")
    print(f"verify: report -> {out.relative_to(repo_root())}")
    return 0
