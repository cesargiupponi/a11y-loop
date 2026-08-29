"""capture — macOS-only. Builds a corpus app, runs the accessibility-audit UI
tests in the simulator, and normalizes the results into committed fixtures.

Fixtures are the contract between this Mac-only stage and everything else:
audit/fix/verify/eval read fixtures and run on any OS, so judges reproduce the
headline result without Xcode.

Layout produced:  fixtures/<App>/<variant>/<screen>.json   (audit issues + a11y tree)
                  fixtures/<App>/<variant>/<screen>.png    (screenshot)
"""

from __future__ import annotations

import json
import platform
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from a11y_loop.paths import corpus_dir, fixtures_dir

SIMULATOR = "iPhone 16"


def _run(cmd: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)


def _scheme_name(app_dir: Path) -> str:
    """Scheme comes from project.yml, so a seeded copy in a differently named
    directory still builds the same scheme as the clean app."""
    for line in (app_dir / "project.yml").read_text().splitlines():
        if line.startswith("name:"):
            return line.split(":", 1)[1].strip()
    raise RuntimeError(f"no project name in {app_dir}/project.yml")


def _latest_xcresult(app_dir: Path) -> Path:
    results = sorted(
        (app_dir / "DerivedData" / "Logs" / "Test").glob("*.xcresult"),
        key=lambda p: p.stat().st_mtime,
    )
    if not results:
        raise RuntimeError("no .xcresult produced by the test run")
    return results[-1]


def _export_attachments(xcresult: Path, dest: Path) -> int:
    """Export attachments and rename them from UUIDs to their screen names."""
    dest.mkdir(parents=True, exist_ok=True)
    for stale in dest.iterdir():
        stale.unlink()

    with tempfile.TemporaryDirectory() as tmp:
        staging = Path(tmp)
        export = _run(
            [
                "xcrun", "xcresulttool", "export", "attachments",
                "--path", str(xcresult),
                "--output-path", str(staging),
            ]
        )
        if export.returncode != 0:
            raise RuntimeError(f"xcresulttool export failed:\n{export.stderr}")

        manifest = json.loads((staging / "manifest.json").read_text())
        count = 0
        for test in manifest:
            for attachment in test.get("attachments", []):
                exported = attachment.get("exportedFileName")
                if not exported:
                    continue
                # Xcode returns "<screen>_<n>_<uuid>.<ext>"; keep "<screen>.<ext>"
                # so fixture paths are stable across runs.
                readable = attachment.get("suggestedHumanReadableName") or exported
                screen = readable.split("_", 1)[0]
                shutil.copyfile(staging / exported, dest / f"{screen}{Path(exported).suffix}")
                count += 1
    return count


def run_capture(app: str, variant: str = "seeded") -> int:
    if platform.system() != "Darwin":
        print(
            "capture: macOS + Xcode required. Committed fixtures already cover the "
            "eval — run `a11y-loop eval` instead.",
            file=sys.stderr,
        )
        return 2

    app_dir = corpus_dir(app)
    if not app_dir.exists():
        print(f"capture: no corpus app at {app_dir}", file=sys.stderr)
        return 1
    scheme = _scheme_name(app_dir)
    project = app_dir / f"{scheme}.xcodeproj"
    if not project.exists():
        gen = _run(["xcodegen", "generate"], cwd=app_dir)
        if gen.returncode != 0:
            print(f"capture: xcodegen failed:\n{gen.stderr}", file=sys.stderr)
            return 1

    print(f"capture: running accessibility audit tests for {app} ({variant}) on {SIMULATOR}…")
    test = _run(
        [
            "xcodebuild", "test",
            "-project", str(project),
            "-scheme", scheme,
            "-destination", f"platform=iOS Simulator,name={SIMULATOR}",
            "-derivedDataPath", str(app_dir / "DerivedData"),
        ],
        cwd=app_dir,
    )
    if "** TEST SUCCEEDED **" not in test.stdout:
        tail = "\n".join(l for l in test.stdout.splitlines() if "error:" in l)[-2000:]
        print(f"capture: UI tests failed.\n{tail}", file=sys.stderr)
        return 1

    dest = fixtures_dir(app) / variant
    count = _export_attachments(_latest_xcresult(app_dir), dest)
    screens = sorted(p.stem for p in dest.glob("*.json"))
    print(f"capture: wrote {count} files to {dest.relative_to(dest.parents[3])}")
    print(f"capture: screens = {', '.join(screens)}")
    return 0
