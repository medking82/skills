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


# The fork moved most of these upstream files' bodies into fork-owned references.
# Git cannot follow moved text, so an upstream edit there always conflicts. The
# sync keeps the fork's entrypoint and applies the same upstream patch to the
# reference instead; a hunk without matching context still stops the sync.
RELOCATED_UPSTREAM_FILES = {
    "skills/emil-design-eng/SKILL.md": "skills/emil-design-eng/references/craft-guide.md",
}


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


def port_relocated_changes(repo: Path, upstream: str, merge_output: str) -> None:
    """Resolve conflicts only in relocated files by porting upstream's patch to the fork's reference."""
    conflicted = [path for path in git(repo, "diff", "--name-only", "--diff-filter=U", "-z").stdout.split("\0") if path]
    if not conflicted or any(path not in RELOCATED_UPSTREAM_FILES for path in conflicted):
        raise SyncError(merge_output)
    base = git(repo, "merge-base", "HEAD", upstream).stdout.strip()
    for source in conflicted:
        target = RELOCATED_UPSTREAM_FILES[source]
        patch = git(repo, "diff", "--no-renames", "--no-color", base, upstream, "--", source).stdout
        patch = patch.replace(f"a/{source}", f"a/{target}").replace(f"b/{source}", f"b/{target}")
        git(repo, "checkout", "--ours", "--", source)
        git(repo, "add", "--", source)
        # Bytes keep the patch's LF line endings; text mode on Windows would write CRLF.
        applied = subprocess.run(
            ["git", "-C", str(repo), "apply", "--index", "-"],
            input=patch.encode("utf-8"),
            capture_output=True,
            creationflags=NO_WINDOW,
        )
        if applied.returncode:
            error = applied.stderr.decode("utf-8", "replace")
            raise SyncError(f"{merge_output}Upstream change to {source} does not apply to {target}:\n{error}")
        print(f"Ported upstream change to {source} into {target}.")


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

    # Documentation and skill content may follow upstream. The fork owns
    # executable validation, workflow permissions, hooks, and other automation.
    paths = git(repo, "diff", "--name-only", "--no-renames", "-z", f"HEAD...{upstream}").stdout
    blocked = [
        path for path in paths.split("\0") if path
        and path != "LICENSE"
        and not path.startswith("skills/")
        and not (path.lower().endswith(".md") and ("/" not in path or path.startswith("docs/")))
    ]
    if blocked:
        raise SyncError("Upstream changes outside skill content require manual review: " + ", ".join(blocked))

    try:
        merge = git(repo, *BOT_IDENTITY, "merge", "--no-ff", "--no-commit", upstream, check=False)
        if merge.returncode:
            port_relocated_changes(repo, upstream, merge.stdout + merge.stderr)
        if (repo / "skills/design/SKILL.md").exists():
            # The upstream path allowlist above prevents replacing this trusted
            # builder. It admits only registered modes and manifest-owned output.
            rebuild = subprocess.run(
                [sys.executable, "-B", str(repo / "scripts/build-design-skill.py")],
                cwd=repo,
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
                encoding="utf-8",
                creationflags=NO_WINDOW,
            )
            if rebuild.returncode:
                raise SyncError("Combined design rebuild failed:\n" + rebuild.stdout + rebuild.stderr)
            # Stage before validation so merge --abort also removes newly
            # generated files if metadata validation rejects the merged source.
            git(repo, "add", "--", "skills/design/references")
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
        regression = subprocess.run(
            [sys.executable, "-B", "-m", "unittest", "discover", "-s", "tests", "-q"],
            cwd=repo,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            encoding="utf-8",
            creationflags=NO_WINDOW,
        )
        if regression.returncode:
            raise SyncError("Merged regression tests failed:\n" + regression.stdout + regression.stderr)
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
