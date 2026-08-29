"""Thin runtime around the Claude Agent SDK.

Two responsibilities, kept in one place so both arms are measured identically:

1. Run a prompt and return the text plus what it cost and how long it took.
2. Record the full message stream to `trajectories/` — the agent's instructions,
   every tool call, every tool result, and the final output. These are a
   required deliverable and the evidence behind the changelog, so nothing is
   summarized on the way in.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from claude_agent_sdk import ClaudeAgentOptions, query

from a11y_loop.paths import trajectories_dir

MODEL = "claude-opus-5"


@dataclass
class RunResult:
    text: str
    cost_usd: float
    duration_seconds: float
    turns: int
    trajectory_path: Path
    tool_calls: list[str] = field(default_factory=list)


def _block_to_record(block: Any) -> dict:
    kind = type(block).__name__
    record: dict[str, Any] = {"block": kind}
    if hasattr(block, "text"):
        record["text"] = block.text
    if hasattr(block, "name"):
        record["tool"] = block.name
    if hasattr(block, "input"):
        record["input"] = block.input
    if hasattr(block, "content"):
        record["content"] = str(block.content)[:20000]
    if hasattr(block, "is_error"):
        record["is_error"] = block.is_error
    return record


async def run_agent(
    *,
    name: str,
    prompt: str,
    system_prompt: str | None = None,
    allowed_tools: list[str] | None = None,
    cwd: Path | None = None,
    max_turns: int = 1,
    permission_mode: str = "default",
) -> RunResult:
    """Run one agent and record its trajectory.

    `allowed_tools=[]` gives a no-tools single-pass run, which is how the
    baseline arm is held to "one direct prompt with basic instructions".
    """
    options = ClaudeAgentOptions(
        model=MODEL,
        max_turns=max_turns,
        allowed_tools=allowed_tools if allowed_tools is not None else [],
        permission_mode=permission_mode,
        **({"system_prompt": system_prompt} if system_prompt else {}),
        **({"cwd": str(cwd)} if cwd else {}),
    )

    trajectory_dir = trajectories_dir()
    trajectory_dir.mkdir(parents=True, exist_ok=True)
    trajectory_path = trajectory_dir / f"{name}.jsonl"

    texts: list[str] = []
    tool_calls: list[str] = []
    cost = 0.0
    turns = 0
    started = time.monotonic()

    with trajectory_path.open("w") as trajectory:
        trajectory.write(
            json.dumps(
                {
                    "event": "run_start",
                    "agent": name,
                    "model": MODEL,
                    "max_turns": max_turns,
                    "allowed_tools": options.allowed_tools,
                    "system_prompt": system_prompt,
                    "prompt": prompt,
                }
            )
            + "\n"
        )

        async for message in query(prompt=prompt, options=options):
            kind = type(message).__name__
            if kind in {"AssistantMessage", "UserMessage"}:
                blocks = [_block_to_record(b) for b in message.content] if isinstance(message.content, list) else [{"text": str(message.content)}]
                trajectory.write(json.dumps({"event": kind, "blocks": blocks}) + "\n")
                for block, record in zip(message.content if isinstance(message.content, list) else [], blocks):
                    if record.get("text") and kind == "AssistantMessage":
                        texts.append(record["text"])
                    if record.get("tool"):
                        tool_calls.append(record["tool"])
            elif kind == "ResultMessage":
                cost = getattr(message, "total_cost_usd", 0.0) or 0.0
                turns = getattr(message, "num_turns", 0) or 0
                trajectory.write(
                    json.dumps({"event": "result", "cost_usd": cost, "turns": turns}) + "\n"
                )

    return RunResult(
        text="\n".join(texts),
        cost_usd=cost,
        duration_seconds=time.monotonic() - started,
        turns=turns,
        trajectory_path=trajectory_path,
        tool_calls=tool_calls,
    )
