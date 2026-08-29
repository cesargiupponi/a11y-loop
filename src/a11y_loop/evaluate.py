"""Eval harness: run the baseline and agent arms on the same corpus and score
both against ground truth.

Cross-platform by construction — it consumes committed fixtures rather than a
simulator, so the headline comparison reproduces without a Mac.
"""

from __future__ import annotations

import sys

import anyio

from a11y_loop.paths import eval_dir, results_dir
from a11y_loop.scoring import save_score, score_arm


async def _run_arms(only: str | None, baseline_mode: str = "source_only") -> list:
    scores = []

    if only in (None, "baseline"):
        from a11y_loop.baseline import run_baseline_arm

        print(f"eval: running baseline ({baseline_mode}: one direct prompt, no tools)…")
        run = await run_baseline_arm(baseline_mode)
        score = score_arm(
            f"baseline-{baseline_mode}",
            run["workspace"],
            run["findings"],
            duration_seconds=run["duration_seconds"],
            cost_usd=run["cost_usd"],
        )
        save_score(score, results_dir() / f"baseline-{baseline_mode}.json")
        scores.append(score)

    if only in (None, "agent"):
        from a11y_loop.pipeline import run_agent_arm

        print("eval: running agent pipeline (audit -> fix -> verify)…")
        run = await run_agent_arm()
        score = score_arm(
            "agent",
            run["workspace"],
            run["findings"],
            duration_seconds=run["duration_seconds"],
            cost_usd=run["cost_usd"],
        )
        save_score(score, results_dir() / "agent.json")
        scores.append(score)

    return scores


def run_eval(only: str | None = None, baseline_mode: str = "source_only") -> int:
    ground_truth = eval_dir() / "ground_truth.json"
    if not ground_truth.exists():
        print(
            "eval: no ground truth (eval/ground_truth.json missing). Run: python eval/seed.py",
            file=sys.stderr,
        )
        return 1

    scores = anyio.run(_run_arms, only, baseline_mode)

    print()
    for score in scores:
        print(score.summary_line())
    print(f"\neval: per-arm detail written to {results_dir().name}/")
    return 0
