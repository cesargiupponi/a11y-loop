"""The ground truth has to be trustworthy before any number computed from it
means anything.

The load-bearing property: every mechanical case must FAIL its check on the
seeded source and PASS it on the clean source. A check that passes on seeded
source would hand out free credit; one that fails on clean source would make a
correct fix unscoreable. Both silently corrupt the headline metric.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from a11y_loop.checks import run_check

ROOT = Path(__file__).resolve().parent.parent
GROUND_TRUTH = json.loads((ROOT / "eval" / "ground_truth.json").read_text())
CASES = GROUND_TRUTH["cases"]
MECHANICAL = [c for c in CASES if c["fixable"]]
# Traps invert the invariant: the seeded state is already correct, and the case
# is failed by changing it rather than by leaving it.
TRAPS = [c for c in MECHANICAL if c["violation_class"] == "false_positive_trap"]
DEFECTS = [c for c in MECHANICAL if c["violation_class"] != "false_positive_trap"]
REPORT_ONLY = [c for c in CASES if not c["fixable"]]


def source_for(case: dict, variant: str) -> str:
    root = ROOT / GROUND_TRUTH[f"{variant}_source"]
    return (root / case["file"]).read_text()


def ids(cases):
    return [c["id"] for c in cases]


def test_corpus_meets_the_brief():
    assert len(CASES) >= 10, "the brief asks for ten or more evaluation cases"
    assert len({c["screen"] for c in CASES}) == 5
    assert any(c["violation_class"] == "semantic_value_loss" for c in CASES), "hard case missing"


@pytest.mark.parametrize("case", DEFECTS, ids=ids(DEFECTS))
def test_check_fails_on_seeded_source(case):
    result = run_check(case["check"], source_for(case, "seeded"))
    assert not result.passed, (
        f"{case['id']} passes its check on the seeded source, so a broken app would "
        f"score as fixed: {result.reason}"
    )


DEGRADED = [c for c in DEFECTS if c.get("exists_in_clean", True)]


@pytest.mark.parametrize("case", DEGRADED, ids=ids(DEGRADED))
def test_check_passes_on_clean_source(case):
    result = run_check(case["check"], source_for(case, "clean"))
    assert result.passed, (
        f"{case['id']} fails its check on the clean source, so a correct fix could "
        f"never score: {result.reason}"
    )


@pytest.mark.parametrize("case", REPORT_ONLY, ids=ids(REPORT_ONLY))
def test_report_only_cases_are_never_scored_as_fixed(case):
    assert not run_check(case["check"], source_for(case, "clean")).passed


@pytest.mark.parametrize("case", TRAPS, ids=ids(TRAPS))
def test_trap_passes_while_untouched(case):
    """A trap is passed by leaving the code alone; the seeded state is correct."""
    assert run_check(case["check"], source_for(case, "seeded")).passed


@pytest.mark.parametrize("case", TRAPS, ids=ids(TRAPS))
def test_trap_fails_once_patched(case):
    """And failed by 'fixing' it — which is what an unverified suspicion does."""
    patched = source_for(case, "seeded").replace(".frame(width: 24, height: 24)", ".frame(minWidth: 44, minHeight: 44)")
    assert not run_check(case["check"], patched).passed


def test_every_case_is_anchored_in_its_file():
    for case in CASES:
        source = source_for(case, "seeded")
        assert f'.accessibilityIdentifier("{case["anchor"]}")' in source, (
            f"{case['id']}: anchor {case['anchor']!r} is missing from {case['file']}, "
            "so the check cannot locate the element"
        )
