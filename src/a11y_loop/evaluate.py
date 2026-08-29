"""Eval harness: run the baseline and agent arms on the same corpus and score
both against ground truth.

Cross-platform by construction — it consumes committed fixtures rather than a
simulator, so the headline comparison reproduces without a Mac.

Model runs are not deterministic, and on this corpus the case that fails moves
between runs while the total barely does. A single run is therefore not a result:
use `--repeat` to report a mean and a range, which is what the numbers in the
README are.
"""

from __future__ import annotations

import json
import statistics
import sys

import anyio

from a11y_loop.paths import eval_dir, results_dir
from a11y_loop.scoring import ArmScore, save_score, score_arm


async def _run_baseline(baseline_mode: str) -> ArmScore:
    from a11y_loop.baseline import run_baseline_arm

    print(f"eval: baseline ({baseline_mode}: one direct prompt, no tools)…")
    run = await run_baseline_arm(baseline_mode)
    return score_arm(
        f"baseline-{baseline_mode}",
        run["workspace"],
        run["findings"],
        duration_seconds=run["duration_seconds"],
        cost_usd=run["cost_usd"],
    )


async def _run_agent() -> ArmScore:
    from a11y_loop.pipeline import run_agent_arm

    print("eval: agent pipeline (audit -> fix -> verify)…")
    run = await run_agent_arm()
    return score_arm(
        "agent",
        run["workspace"],
        run["findings"],
        duration_seconds=run["duration_seconds"],
        cost_usd=run["cost_usd"],
    )


async def _run_arms(only: str | None, baseline_mode: str, repeat: int) -> dict[str, list[ArmScore]]:
    collected: dict[str, list[ArmScore]] = {}

    for attempt in range(1, repeat + 1):
        if repeat > 1:
            print(f"\n=== run {attempt} of {repeat} ===")

        if only in (None, "baseline"):
            score = await _run_baseline(baseline_mode)
            collected.setdefault(score.arm, []).append(score)
            save_score(score, results_dir() / f"{score.arm}.json")
            if repeat > 1:
                save_score(score, results_dir() / "runs" / f"{score.arm}-{attempt}.json")

        if only in (None, "agent"):
            score = await _run_agent()
            collected.setdefault(score.arm, []).append(score)
            save_score(score, results_dir() / "agent.json")
            if repeat > 1:
                save_score(score, results_dir() / "runs" / f"agent-{attempt}.json")

    return collected


def _summarise(collected: dict[str, list[ArmScore]]) -> dict:
    summary = {}
    for arm, scores in collected.items():
        fixed = [s.fixes_verified for s in scores]
        summary[arm] = {
            "runs": len(scores),
            "mechanical_total": scores[0].mechanical_total,
            "fixes_verified": fixed,
            "mean": statistics.mean(fixed),
            "min": min(fixed),
            "max": max(fixed),
            "mean_rate": statistics.mean(s.verified_fix_rate for s in scores),
            "cost_usd_mean": statistics.mean(s.cost_usd for s in scores),
            "duration_seconds_mean": statistics.mean(s.duration_seconds for s in scores),
            # Which case failed, per run. The interesting part on this corpus:
            # the total holds while the membership of this list changes.
            "failed_cases": [
                sorted(o.id for o in s.outcomes if o.fixable and not o.fix_verified)
                for s in scores
            ],
        }
    return summary


def run_eval(only: str | None = None, baseline_mode: str = "source_only", repeat: int = 1) -> int:
    ground_truth = eval_dir() / "ground_truth.json"
    if not ground_truth.exists():
        print(
            "eval: no ground truth (eval/ground_truth.json missing). Run: python eval/seed.py",
            file=sys.stderr,
        )
        return 1

    collected = anyio.run(_run_arms, only, baseline_mode, repeat)

    print()
    for scores in collected.values():
        for score in scores:
            print(score.summary_line())

    if repeat > 1:
        summary = _summarise(collected)
        path = results_dir() / "variance.json"
        path.write_text(json.dumps(summary, indent=2) + "\n")

        print(f"\nAcross {repeat} runs:")
        for arm, data in summary.items():
            spread = (
                f"{data['min']}" if data["min"] == data["max"] else f"{data['min']}–{data['max']}"
            )
            print(
                f"  {arm:22} mean {data['mean']:.1f}/{data['mechanical_total']} "
                f"({data['mean_rate']:.0%}), range {spread}, "
                f"${data['cost_usd_mean']:.2f}/run"
            )
            print(f"  {'':22} failed per run: {data['failed_cases']}")
        print(f"\neval: variance summary -> {path.name}")

    print(f"\neval: per-arm detail written to {results_dir().name}/")
    return 0
