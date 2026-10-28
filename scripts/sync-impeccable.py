"""Refresh the owned Impeccable snapshot from a verified, checked-out fork commit."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path, PurePosixPath


REPOSITORY = "medking82/impeccable"
UPSTREAM = "pbakaus/impeccable"
MAX_FILES = 200
MAX_FILE_BYTES = 2 * 1024 * 1024
MAX_TOTAL_BYTES = 8 * 1024 * 1024


class SnapshotError(RuntimeError):
    pass


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def safe_name(name: str) -> str:
    path = PurePosixPath(name)
    if not name or path.is_absolute() or path.as_posix() != name:
        raise SnapshotError(f"Unsafe snapshot path: {name!r}")
    for part in path.parts:
        stem = part.split(".")[0].upper()
        if (part in {".", ".."} or part.endswith((".", " "))
                or re.search(r'[\\:<>"|?*\x00-\x1f]', part)
                or stem in {"CON", "PRN", "AUX", "NUL"}
                or re.fullmatch(r"(?:COM|LPT)[1-9]", stem)):
            raise SnapshotError(f"Unsafe snapshot path: {name!r}")
    return name


def collect(source: Path) -> dict[str, bytes]:
    skill = source / ".agents/skills/impeccable"
    if not skill.is_dir() or skill.is_symlink():
        raise SnapshotError("Missing regular upstream skill directory")
    files: dict[str, bytes] = {}
    for path in sorted(skill.rglob("*")):
        if path.is_symlink() or (hasattr(path, "is_junction") and path.is_junction()):
            raise SnapshotError(f"Linked upstream path: {path}")
        if path.is_dir():
            continue
        if not path.is_file():
            raise SnapshotError(f"Nonregular upstream file: {path}")
        name = path.relative_to(skill).as_posix()
        if name == "agents/openai.yaml":
            continue  # The bundle has only one discoverable skill and invocation policy.
        if name == "SKILL.md":
            name = "guide.md"
        elif path.name.casefold() == "skill.md":
            raise SnapshotError(f"Unexpected nested skill entrypoint: {path}")
        files[safe_name(name)] = path.read_bytes()
    for name in ("LICENSE", "NOTICE.md"):
        path = source / name
        if path.is_symlink() or not path.is_file():
            raise SnapshotError(f"Missing upstream attribution file: {name}")
        files[name] = path.read_bytes()
    if not {"guide.md", "reference/craft-floor.md", "scripts/VERSION",
            "scripts/engine-checksums.txt", "scripts/impeccable.cmd"}.issubset(files):
        raise SnapshotError("Incomplete upstream skill snapshot")
    if (len(files) > MAX_FILES or len({n.casefold() for n in files}) != len(files)
            or any(len(data) > MAX_FILE_BYTES for data in files.values())
            or sum(map(len, files.values())) > MAX_TOTAL_BYTES):
        raise SnapshotError("Snapshot exceeds limits or contains colliding paths")
    return files


def manifest(commit: str, files: dict[str, bytes]) -> dict:
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise SnapshotError("Source commit must be a full lowercase Git SHA")
    return {"schema_version": 1, "repository": REPOSITORY, "upstream": UPSTREAM,
            "commit": commit, "files": {name: digest(data) for name, data in sorted(files.items())}}


def existing(root: Path) -> tuple[dict | None, dict[str, bytes]]:
    if not root.exists():
        return None, {}
    if root.is_symlink() or not root.is_dir():
        raise SnapshotError("Snapshot destination is not a regular directory")
    path = root / "source.json"
    if not path.is_file() or path.is_symlink():
        raise SnapshotError("Existing snapshot has no owned source manifest")
    info = json.loads(path.read_text(encoding="utf-8"))
    files: dict[str, bytes] = {}
    for item in root.rglob("*"):
        if item.is_symlink() or (hasattr(item, "is_junction") and item.is_junction()):
            raise SnapshotError(f"Linked snapshot path: {item}")
        if item.is_dir():
            continue
        name = safe_name(item.relative_to(root).as_posix())
        if name != "source.json":
            if not item.is_file():
                raise SnapshotError(f"Nonregular snapshot file: {item}")
            files[name] = item.read_bytes()
    if info != manifest(info.get("commit", ""), files):
        raise SnapshotError("Snapshot has local edits, unowned files, or invalid provenance")
    return info, files


def protected(name: str) -> bool:
    name = name.casefold()
    return name.startswith(("scripts/", "agents/")) or name in {"license", "notice.md"}


def refresh(repo: Path, source: Path, commit: str, *, check: bool = False,
            allow_code_updates: bool = False) -> bool:
    root = repo / "skills/impeccable/upstream"
    previous, old = existing(root)
    files = collect(source)
    desired = manifest(commit, files)
    changed = {name for name in old.keys() | files.keys() if old.get(name) != files.get(name)}
    if previous and not allow_code_updates and any(protected(name) for name in changed):
        raise SnapshotError("Upstream executable, agent, or license changes require manual review")
    if previous == desired:
        return True
    if check:
        return False
    # All ownership, paths, size and policy checks precede the first write.
    root.mkdir(parents=True, exist_ok=True)
    for name, data in files.items():
        target = root.joinpath(*PurePosixPath(name).parts)
        if old.get(name) != data:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
    for name in old.keys() - files.keys():
        root.joinpath(*PurePosixPath(name).parts).unlink()
    (root / "source.json").write_text(json.dumps(desired, indent=2) + "\n", encoding="utf-8")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path, help="Clean fork checkout at --commit")
    parser.add_argument("--commit", required=True)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--allow-code-updates", action="store_true",
                        help="Accept separately reviewed script, agent, and license changes")
    args = parser.parse_args()
    try:
        current = refresh(args.repo.resolve(), args.source.resolve(), args.commit,
                          check=args.check, allow_code_updates=args.allow_code_updates)
    except (OSError, ValueError, TypeError, SnapshotError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print("Impeccable snapshot is current." if current else "Impeccable snapshot is stale.")
    return 0 if current else 1


if __name__ == "__main__":
    raise SystemExit(main())
