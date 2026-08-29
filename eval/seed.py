"""Generate the seeded corpus app and the ground-truth manifest.

    python eval/seed.py

Reads the clean app (corpus/Ledgerly), applies every recorded transformation in
eval/seeds.py, writes the seeded app (corpus/LedgerlySeeded) and the exact
ground truth (eval/ground_truth.json).

Deterministic: same inputs, same outputs, and every transformation must match
exactly once or the run fails loudly. A silently skipped seed would inflate the
measured fix rate, so this refuses to produce a partial corpus.
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from seeds import APP, SEEDS, mechanical, report_only  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
CLEAN = ROOT / "corpus" / APP
SEEDED = ROOT / "corpus" / f"{APP}Seeded"
GROUND_TRUTH = ROOT / "eval" / "ground_truth.json"

# Build products and generated projects never belong in the seeded copy.
IGNORE = shutil.ignore_patterns("DerivedData", "*.xcodeproj", "build", ".DS_Store")


def line_of(text: str, needle: str) -> int:
    """1-indexed line number where `needle` starts."""
    return text[: text.index(needle)].count("\n") + 1


def main() -> int:
    if not CLEAN.exists():
        print(f"seed: clean corpus missing at {CLEAN}", file=sys.stderr)
        return 1

    if SEEDED.exists():
        shutil.rmtree(SEEDED)
    shutil.copytree(CLEAN, SEEDED, ignore=IGNORE)

    cases: list[dict] = []
    failures: list[str] = []

    for seed in SEEDS:
        target = SEEDED / seed.file
        source = target.read_text()
        occurrences = source.count(seed.find)
        if occurrences != 1:
            failures.append(
                f"{seed.id}: pattern matched {occurrences} times in {seed.file} (expected exactly 1)"
            )
            continue

        patched = source.replace(seed.find, seed.replace)
        target.write_text(patched)

        case = seed.as_case()
        case["clean_line"] = line_of(source, seed.find)
        case["seeded_line"] = line_of(patched, seed.replace.lstrip("\n")) if seed.replace.strip() else case["clean_line"]
        cases.append(case)

    if failures:
        print("seed: refusing to write a partial corpus:", file=sys.stderr)
        for f in failures:
            print(f"  - {f}", file=sys.stderr)
        shutil.rmtree(SEEDED)
        return 1

    manifest = {
        "app": APP,
        "clean_source": str(CLEAN.relative_to(ROOT)),
        "seeded_source": str(SEEDED.relative_to(ROOT)),
        "totals": {
            "cases": len(cases),
            "mechanical": len(mechanical()),
            "report_only": len(report_only()),
            "screens": len({c["screen"] for c in cases}),
        },
        "scoring": {
            "primary_metric": "verified_fix_rate",
            "definition": (
                "share of mechanical seeded violations that are detected, patched, and pass "
                "their check after patching"
            ),
            "report_only_note": (
                "report-only cases score detection only; the correct remedy is a design "
                "decision left to a human reviewer"
            ),
            "pre_existing_note": (
                "issues present in the clean capture are pre-existing, not seeded: they are "
                "reported separately and never counted as false positives"
            ),
        },
        "cases": cases,
    }
    GROUND_TRUTH.write_text(json.dumps(manifest, indent=2) + "\n")

    print(f"seed: wrote {SEEDED.relative_to(ROOT)} with {len(cases)} seeded violations")
    print(
        f"seed: {manifest['totals']['mechanical']} mechanical (scored on fixes), "
        f"{manifest['totals']['report_only']} report-only, "
        f"across {manifest['totals']['screens']} screens"
    )
    print(f"seed: ground truth -> {GROUND_TRUTH.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
