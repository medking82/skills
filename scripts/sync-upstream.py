"""Prepare a validated upstream merge in a clean main checkout; never push it."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


UPSTREAM_URL = "https://github.com/emilkowalski/skills.git"
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
BOT_IDENTITY = (
    "-c", "user.name=github-actions[bot]",
    "-c", "user.email=41898282+github-actions[bot]@users.noreply.github.com",
)


class SyncError(RuntimeError):
    pass


def git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        encoding="utf-8",
        creationflags=NO_WINDOW,
    )
    if check and result.returncode:
        raise SyncError(result.stdout + result.stderr)
    return result


def prepare_sync(repo: Path, upstream_url: str = UPSTREAM_URL) -> bool:
    """Return whether a merge was committed. Failures leave the original HEAD intact."""
    if git(repo, "branch", "--show-current").stdout.strip() != "main":
        raise SyncError("Upstream sync requires a main checkout.")
    if git(repo, "status", "--porcelain", "--untracked-files=all").stdout:
        raise SyncError("Upstream sync requires a clean checkout; local changes were preserved.")
    if git(repo, "rev-parse", "--verify", "-q", "MERGE_HEAD", check=False).returncode == 0:
        raise SyncError("Finish the existing merge before syncing upstream.")

    git(repo, "fetch", "--no-tags", upstream_url, "refs/heads/main")
    upstream = git(repo, "rev-parse", "FETCH_HEAD").stdout.strip()
    ancestry = git(repo, "merge-base", "--is-ancestor", upstream, "HEAD", check=False)
    if ancestry.returncode == 0:
        print("The fork already contains upstream main; no commit needed.")
        return False
    if ancestry.returncode != 1:
        raise SyncError(ancestry.stderr)

    # Only content is eligible for unattended updates. The fork owns executable
    # validation, workflow permissions, hooks, and all other automation surfaces.
    paths = git(repo, "diff", "--name-only", "--no-renames", "-z", f"HEAD...{upstream}").stdout
    blocked = [
        path for path in paths.split("\0") if path
        and path not in {"README.md", "LICENSE"}
        and not path.startswith("skills/")
    ]
    if blocked:
        raise SyncError("Upstream changes outside skill content require manual review: " + ", ".join(blocked))

    try:
        git(repo, *BOT_IDENTITY, "merge", "--no-ff", "--no-commit", upstream)
        validation = subprocess.run(
            [sys.executable, "-B", str(repo / "tests" / "test_skill_metadata.py")],
            cwd=repo,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            encoding="utf-8",
            creationflags=NO_WINDOW,
        )
        if validation.returncode:
            raise SyncError("Merged skill metadata failed validation:\n" + validation.stdout + validation.stderr)
        git(repo, *BOT_IDENTITY, "commit", "-m", f"chore: sync emilkowalski/skills at {upstream[:12]}")
    except Exception:
        if git(repo, "rev-parse", "--verify", "-q", "MERGE_HEAD", check=False).returncode == 0:
            git(repo, "merge", "--abort")
        raise

    print(f"Prepared and validated upstream merge {upstream}; ready to push.")
    return True


def main() -> int:
    try:
        changed = prepare_sync(Path(__file__).resolve().parents[1])
    except (SyncError, OSError) as error:
        print(f"Upstream sync stopped: {error}", file=sys.stderr)
        return 1
    if output_file := os.environ.get("GITHUB_OUTPUT"):
        with open(output_file, "a", encoding="utf-8") as output:
            output.write(f"changed={str(changed).lower()}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
