#!/usr/bin/env python3
"""Locate the neutral agent-sop-kit runtime without copying it into every project."""

from __future__ import annotations

import os
import runpy
import subprocess
import sys
from pathlib import Path

NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def git_sibling_candidates(project: Path) -> list[Path]:
    try:
        result = subprocess.run(
            ["git", "-C", str(project), "rev-parse", "--path-format=absolute",
             "--git-common-dir"],
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
            creationflags=NO_WINDOW,
        )
    except (OSError, subprocess.SubprocessError):
        return []
    if result.returncode != 0 or not result.stdout.strip():
        return []
    common = Path(result.stdout.strip()).resolve()
    if common.name != ".git":
        return []
    return [common.parent.parent / name for name in ("agent-sop-kit", "claude-sop-kit")]


def candidates() -> list[Path]:
    project = Path(__file__).resolve().parents[1]
    values: list[Path] = []
    for name in ("AGENT_SOP_KIT_ROOT", "CLAUDE_SOP_KIT_ROOT"):
        explicit = os.environ.get(name)
        if explicit:
            values.append(Path(explicit).expanduser())
    values.extend(git_sibling_candidates(project))
    values.append(project.parent / "agent-sop-kit")
    values.append(project.parent / "claude-sop-kit")
    if project.parent.name in {".worktrees", "worktrees"}:
        values.append(project.parent.parent / "agent-sop-kit")
        values.append(project.parent.parent / "claude-sop-kit")
    values.append(Path.home() / ".local" / "share" / "agent-sop-kit")
    values.append(Path.home() / ".local" / "share" / "claude-sop-kit")
    unique = dict.fromkeys(value.resolve() / "runtime" / "sop.py" for value in values)
    return list(unique)


for runtime in candidates():
    if runtime.is_file() and (runtime.parents[1] / "sop-init.py").is_file():
        runpy.run_path(str(runtime), run_name="__main__")
        raise SystemExit(0)

sys.stderr.write(
    "ERROR: agent-sop-kit runtime not found. Clone it beside this repository or set "
    "AGENT_SOP_KIT_ROOT (legacy CLAUDE_SOP_KIT_ROOT remains supported).\n"
)
raise SystemExit(2)
