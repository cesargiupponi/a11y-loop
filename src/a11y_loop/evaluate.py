"""Eval harness: run baseline and agent arms on the same corpus, score against
ground truth. Cross-platform — consumes committed fixtures, never the simulator."""

from __future__ import annotations

import json
import sys

from a11y_loop.paths import eval_dir


def run_eval(only: str | None = None) -> int:
    ground_truth = eval_dir() / "ground_truth.json"
    if not ground_truth.exists():
        print("eval: no ground truth yet (eval/ground_truth.json missing) — corpus not seeded.", file=sys.stderr)
        print("eval: nothing to do.")
        return 0
    manifest = json.loads(ground_truth.read_text())
    print(f"eval: {len(manifest.get('cases', []))} cases loaded; arms: {only or 'baseline+agent'}")
    raise NotImplementedError("scoring arms land in Phase 2/3")
