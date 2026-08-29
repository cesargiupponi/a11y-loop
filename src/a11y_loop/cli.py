"""a11y-loop CLI.

Judge path (any OS):      a11y-loop eval / a11y-loop report
Mac-only capture path:    a11y-loop capture
Agent pipeline:           a11y-loop audit / fix / verify
"""

from __future__ import annotations

import argparse
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="a11y-loop",
        description=(
            "Agentic accessibility audit-and-fix loop for SwiftUI apps. "
            "Violations are captured from the running app (macOS, once), "
            "committed as fixtures; audit/fix/verify/eval run anywhere."
        ),
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_capture = sub.add_parser(
        "capture", help="[macOS] Build app, run accessibility audit UI tests, dump fixtures."
    )
    p_capture.add_argument("--app", required=True, help="Corpus app name (directory under corpus/).")
    p_capture.add_argument("--variant", default="seeded", choices=["clean", "seeded", "patched"], help="Which build variant to capture.")

    p_audit = sub.add_parser("audit", help="Auditor agent: fixtures + source -> violations.json.")
    p_audit.add_argument("--app", required=True)

    p_fix = sub.add_parser("fix", help="Fixer agent: patch mechanical violations on a git branch.")
    p_fix.add_argument("--app", required=True)

    p_verify = sub.add_parser("verify", help="Verifier: structural re-check of patches against fixtures.")
    p_verify.add_argument("--app", required=True)

    p_eval = sub.add_parser("eval", help="Run baseline + agent on the corpus, score against ground truth.")
    p_eval.add_argument("--only", choices=["baseline", "agent"], default=None, help="Run a single arm.")
    p_eval.add_argument(
        "--repeat",
        type=int,
        default=1,
        metavar="N",
        help="Run each arm N times and report a mean and range. A single run is not a result: "
             "the failing case moves between runs while the total barely does.",
    )
    p_eval.add_argument(
        "--baseline-mode",
        choices=["source_only", "curated"],
        default="source_only",
        help="source_only models the status quo; curated also hands over captured runtime evidence.",
    )

    sub.add_parser("report", help="Render comparison tables + changelog from eval results.")

    args = parser.parse_args(argv)

    if args.command == "capture":
        from a11y_loop.capture import run_capture

        return run_capture(app=args.app, variant=args.variant)
    if args.command == "audit":
        from a11y_loop.audit import run_audit

        return run_audit(app=args.app)
    if args.command == "fix":
        from a11y_loop.fix import run_fix

        return run_fix(app=args.app)
    if args.command == "verify":
        from a11y_loop.verify import run_verify

        return run_verify(app=args.app)
    if args.command == "eval":
        from a11y_loop.evaluate import run_eval

        return run_eval(only=args.only, baseline_mode=args.baseline_mode, repeat=args.repeat)
    if args.command == "report":
        from a11y_loop.report import run_report

        return run_report()

    parser.error(f"unknown command {args.command!r}")
    return 2


if __name__ == "__main__":
    sys.exit(main())
