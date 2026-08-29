"""Repo-relative path helpers. Everything resolves from the repo root so the CLI
works from any cwd inside the project."""

from __future__ import annotations

from pathlib import Path


def repo_root() -> Path:
    """Walk up from this file to the directory containing pyproject.toml."""
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "pyproject.toml").exists():
            return parent
    raise RuntimeError("repo root not found (pyproject.toml missing)")


def fixtures_dir(app: str | None = None) -> Path:
    d = repo_root() / "fixtures"
    return d / app if app else d


def corpus_dir(app: str | None = None) -> Path:
    d = repo_root() / "corpus"
    return d / app if app else d


def eval_dir() -> Path:
    return repo_root() / "eval"


def trajectories_dir() -> Path:
    return repo_root() / "trajectories"


def results_dir() -> Path:
    return repo_root() / "results"
