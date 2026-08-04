#!/usr/bin/env python3
"""Digest-bound Apple Design skill sync for Linux and Windows consumers."""

from __future__ import annotations

import argparse
import contextlib
import dataclasses
import fcntl
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import sys
import tarfile
import tempfile
import urllib.request
import uuid


CANONICAL_ARCHIVE = (
    "https://codeload.github.com/medking82/skills/tar.gz/refs/heads/main"
)
SKILL_NAME = "apple-design"
WINDOWS_MOUNT = Path("/mnt/c")
WINDOWS_PROFILE = Path("/mnt/c/Users/Marck")
EXPECTED_WINDOWS_FSTYPES = {"9p", "drvfs"}
SCOPE_PROFILE_WSL = "wsl"
SCOPE_PROFILE_LINUX = "linux"


class SyncError(RuntimeError):
    """An expected fail-closed updater error."""


@dataclasses.dataclass(frozen=True)
class Scope:
    name: str
    root: Path

    @property
    def target(self) -> Path:
        return self.root / SKILL_NAME


@dataclasses.dataclass(frozen=True)
class ScopeState:
    scope: Scope
    status: str


@dataclasses.dataclass
class Change:
    scope: Scope
    stage: Path
    backup: Path
    root_created: bool
    had_target: bool
    swapped: bool = False


def _lexists(path: Path) -> bool:
    return os.path.lexists(os.fspath(path))


def _assert_plain_directory(path: Path, label: str) -> None:
    if not _lexists(path):
        raise SyncError(f"{label} is missing: {path}")
    if path.is_symlink():
        raise SyncError(f"{label} must not be a symlink: {path}")
    if not path.is_dir():
        raise SyncError(f"{label} is not a directory: {path}")


def _regular_files(root: Path) -> list[Path]:
    _assert_plain_directory(root, "Tree root")
    files: list[Path] = []
    pending = [root]
    while pending:
        current = pending.pop()
        with os.scandir(current) as entries:
            for entry in sorted(entries, key=lambda item: item.name):
                item = Path(entry.path)
                if entry.is_symlink():
                    raise SyncError(f"Symlinks are not allowed: {item}")
                if entry.is_dir(follow_symlinks=False):
                    pending.append(item)
                elif entry.is_file(follow_symlinks=False):
                    files.append(item)
                else:
                    raise SyncError(f"Special files are not allowed: {item}")
    files.sort(key=lambda item: item.relative_to(root).as_posix())
    if not files:
        raise SyncError(f"Skill source is empty: {root}")
    return files


def _validate_skill_tree(root: Path) -> list[Path]:
    files = _regular_files(root)
    skill_file = root / "SKILL.md"
    if skill_file not in files:
        raise SyncError(f"Skill source has no regular SKILL.md: {root}")
    try:
        content = skill_file.read_text(encoding="utf-8")
    except UnicodeError as error:
        raise SyncError(f"SKILL.md is not valid UTF-8: {skill_file}") from error
    frontmatter = re.match(
        r"\A---\r?\n(?P<body>.*?)\r?\n---(?:\r?\n|\Z)",
        content,
        flags=re.DOTALL,
    )
    if not frontmatter or not re.search(
        r"^name:\s*apple-design\s*$",
        frontmatter.group("body"),
        flags=re.MULTILINE,
    ):
        raise SyncError("SKILL.md frontmatter must declare name: apple-design")
    return files


def _tree_manifest(root: Path) -> str:
    entries = []
    for file_path in _validate_skill_tree(root):
        data = file_path.read_bytes()
        entries.append(
            {
                "path": file_path.relative_to(root).as_posix(),
                "length": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
            }
        )
    # PowerShell ConvertTo-Json emits a bare object for one pipeline item and an
    # array for multiple items. Matching that shape preserves existing digests.
    payload: object = entries[0] if len(entries) == 1 else entries
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def _manifest_sha256(manifest: str) -> str:
    return hashlib.sha256(manifest.encode("utf-8")).hexdigest()


def _safe_archive_parts(name: str) -> tuple[str, ...]:
    if not name or name.startswith("/") or "\\" in name or "\0" in name:
        raise SyncError(f"Unsafe archive path: {name!r}")
    parts = PurePosixPath(name).parts
    if not parts or any(part in {"", ".", ".."} for part in parts):
        raise SyncError(f"Unsafe archive path: {name!r}")
    return parts


def _download_canonical_source(temporary_root: Path) -> Path:
    archive_path = temporary_root / "skills-main.tar.gz"
    request = urllib.request.Request(
        CANONICAL_ARCHIVE,
        headers={"User-Agent": "apple-design-wsl-updater/1"},
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        with archive_path.open("wb") as archive_file:
            shutil.copyfileobj(response, archive_file)

    source_root = temporary_root / "source"
    source_root.mkdir()
    with tarfile.open(archive_path, mode="r:gz") as archive:
        selected: list[tuple[tarfile.TarInfo, tuple[str, ...]]] = []
        prefixes: set[str] = set()
        for member in archive.getmembers():
            parts = _safe_archive_parts(member.name)
            if len(parts) >= 3 and parts[1:3] == ("skills", SKILL_NAME):
                prefixes.add(parts[0])
                selected.append((member, parts))
        if len(prefixes) != 1:
            raise SyncError(
                "Expected exactly one skills/apple-design directory in canonical "
                f"archive; found {len(prefixes)}"
            )

        prefix = next(iter(prefixes))
        seen_files: set[Path] = set()
        for member, parts in selected:
            if parts[0] != prefix:
                continue
            relative_parts = parts[3:]
            if not relative_parts:
                if not member.isdir():
                    raise SyncError("Canonical apple-design root is not a directory")
                continue
            destination = source_root.joinpath(*relative_parts)
            if member.isdir():
                destination.mkdir(parents=True, exist_ok=True)
                continue
            if not member.isfile():
                raise SyncError(
                    f"Canonical archive contains a link or special file: {member.name}"
                )
            if destination in seen_files or _lexists(destination):
                raise SyncError(f"Canonical archive contains duplicate path: {member.name}")
            seen_files.add(destination)
            destination.parent.mkdir(parents=True, exist_ok=True)
            extracted = archive.extractfile(member)
            if extracted is None:
                raise SyncError(f"Cannot read canonical archive member: {member.name}")
            with extracted, destination.open("xb") as output:
                shutil.copyfileobj(extracted, output)

    _validate_skill_tree(source_root)
    return source_root


def _mount_fstype(mountpoint: Path) -> str | None:
    try:
        lines = Path("/proc/self/mountinfo").read_text(encoding="utf-8").splitlines()
    except OSError:
        return None
    for line in lines:
        before, separator, after = line.partition(" - ")
        if not separator:
            continue
        fields = before.split()
        if len(fields) < 5:
            continue
        decoded = (
            fields[4]
            .replace("\\040", " ")
            .replace("\\011", "\t")
            .replace("\\012", "\n")
            .replace("\\134", "\\")
        )
        if decoded == str(mountpoint):
            after_fields = after.split()
            return after_fields[0] if after_fields else None
    return None


def _validate_windows_environment(mountpoint: Path, profile: Path) -> None:
    _assert_plain_directory(mountpoint, "Windows mount")
    if not os.path.ismount(mountpoint):
        raise SyncError(f"Windows mount is not mounted: {mountpoint}")
    filesystem = _mount_fstype(mountpoint)
    if filesystem not in EXPECTED_WINDOWS_FSTYPES:
        raise SyncError(
            f"Windows mount has unexpected filesystem {filesystem!r}: {mountpoint}"
        )
    _assert_plain_directory(profile, "Windows profile")
    try:
        resolved_mount = mountpoint.resolve(strict=True)
        resolved_profile = profile.resolve(strict=True)
        if os.path.commonpath([str(resolved_mount), str(resolved_profile)]) != str(
            resolved_mount
        ):
            raise SyncError(f"Windows profile resolves outside {mountpoint}: {profile}")
    except OSError as error:
        raise SyncError(f"Cannot resolve Windows profile: {profile}") from error
    for consumer in (profile / ".codex", profile / ".claude"):
        _assert_plain_directory(consumer, "Windows consumer root")


def _validate_linux_environment(home: Path, environment: str) -> None:
    _assert_plain_directory(home, f"{environment} home")
    try:
        resolved_home = home.resolve(strict=True)
    except OSError as error:
        raise SyncError(f"Cannot resolve {environment} home: {home}") from error
    for name, consumer in (
        ("Codex", home / ".agents"),
        ("Claude", home / ".claude"),
    ):
        _assert_plain_directory(consumer, f"{environment} {name} home")
        try:
            resolved_consumer = consumer.resolve(strict=True)
            if os.path.commonpath([str(resolved_home), str(resolved_consumer)]) != str(
                resolved_home
            ):
                raise SyncError(
                    f"{environment} {name} home resolves outside {home}: {consumer}"
                )
        except OSError as error:
            raise SyncError(
                f"Cannot resolve {environment} {name} home: {consumer}"
            ) from error


def _default_scopes(home: Path, windows_profile: Path) -> list[Scope]:
    return [
        Scope("WslCodex", home / ".agents" / "skills"),
        Scope("WslClaude", home / ".claude" / "skills"),
        Scope("WindowsCodex", windows_profile / ".codex" / "skills"),
        Scope("WindowsClaude", windows_profile / ".claude" / "skills"),
    ]


def _linux_scopes(home: Path) -> list[Scope]:
    return [
        Scope("LinuxCodex", home / ".agents" / "skills"),
        Scope("LinuxClaude", home / ".claude" / "skills"),
    ]


def _parse_test_scopes(values: list[str]) -> list[Scope]:
    scopes: list[Scope] = []
    names: set[str] = set()
    for value in values:
        name, separator, raw_path = value.partition("=")
        if not separator or not name or not raw_path:
            raise SyncError(f"Invalid test scope {value!r}; expected NAME=/absolute/path")
        if name in names:
            raise SyncError(f"Duplicate scope name: {name}")
        root = Path(raw_path)
        if not root.is_absolute():
            raise SyncError(f"Scope root must be absolute: {root}")
        names.add(name)
        scopes.append(Scope(name, root))
    if not scopes:
        raise SyncError("At least one scope is required")
    return scopes


def _inspect_scope(scope: Scope, canonical_manifest: str) -> ScopeState:
    if _lexists(scope.root):
        _assert_plain_directory(scope.root, f"{scope.name} skills root")
    if not _lexists(scope.target):
        return ScopeState(scope, "missing")
    installed_manifest = _tree_manifest(scope.target)
    status = "current" if installed_manifest == canonical_manifest else "drifted"
    return ScopeState(scope, status)


def _prepare_scope_root(scope: Scope) -> bool:
    if _lexists(scope.root):
        _assert_plain_directory(scope.root, f"{scope.name} skills root")
        return False
    _assert_plain_directory(scope.root.parent, f"{scope.name} skills parent")
    scope.root.mkdir()
    return True


def _remove_tree(path: Path) -> None:
    if not _lexists(path):
        return
    if path.is_symlink() or not path.is_dir():
        raise SyncError(f"Refusing to remove non-directory transaction path: {path}")
    shutil.rmtree(path)


def _rollback(changes: list[Change]) -> None:
    rollback_errors: list[str] = []
    for change in reversed(changes):
        try:
            if _lexists(change.scope.target) and (
                change.swapped or _lexists(change.backup)
            ):
                _remove_tree(change.scope.target)
            if _lexists(change.backup):
                change.backup.rename(change.scope.target)
            _remove_tree(change.stage)
            if change.root_created and _lexists(change.scope.root):
                if any(change.scope.root.iterdir()):
                    raise SyncError(
                        f"Created root is not empty after rollback: {change.scope.root}"
                    )
                change.scope.root.rmdir()
        except Exception as error:  # Keep restoring the remaining scopes.
            rollback_errors.append(f"{change.scope.name}: {error}")
    if rollback_errors:
        raise SyncError("Rollback incomplete: " + "; ".join(rollback_errors))


def _apply_transaction(
    states: list[ScopeState],
    canonical_source: Path,
    canonical_manifest: str,
    fail_after_swaps: int | None,
) -> None:
    transaction_id = uuid.uuid4().hex
    changes: list[Change] = []
    try:
        for state in states:
            if state.status == "current":
                continue
            root_created = _prepare_scope_root(state.scope)
            stage = state.scope.root / f".{SKILL_NAME}.stage.{transaction_id}"
            backup = state.scope.root / f".{SKILL_NAME}.backup.{transaction_id}"
            if _lexists(stage) or _lexists(backup):
                raise SyncError(f"Transaction path collision in {state.scope.root}")
            change = Change(
                scope=state.scope,
                stage=stage,
                backup=backup,
                root_created=root_created,
                had_target=_lexists(state.scope.target),
            )
            changes.append(change)
            shutil.copytree(canonical_source, stage, symlinks=False)
            if _tree_manifest(stage) != canonical_manifest:
                raise SyncError(
                    f"Staged {state.scope.name} copy does not match canonical manifest"
                )

        swap_count = 0
        for change in changes:
            if change.had_target:
                change.scope.target.rename(change.backup)
            change.stage.rename(change.scope.target)
            change.swapped = True
            swap_count += 1
            if fail_after_swaps is not None and swap_count == fail_after_swaps:
                raise SyncError(f"Injected failure after {swap_count} scope swap(s)")

        for state in states:
            if _tree_manifest(state.scope.target) != canonical_manifest:
                raise SyncError(
                    f"Post-write verification failed for {state.scope.name}"
                )
    except Exception as error:
        try:
            _rollback(changes)
        except Exception as rollback_error:
            raise SyncError(f"{error}; {rollback_error}") from error
        raise

    cleanup_errors: list[str] = []
    for change in changes:
        try:
            _remove_tree(change.backup)
        except Exception as error:
            cleanup_errors.append(f"{change.scope.name}: {error}")
    if cleanup_errors:
        raise SyncError(
            "Apply committed, but backup cleanup failed: " + "; ".join(cleanup_errors)
        )
    for change in changes:
        print(f"APPLE_DESIGN_SYNC scope={change.scope.name} status=applied")


@contextlib.contextmanager
def _updater_lock(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_CREAT | os.O_RDWR
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags, 0o600)
    lock_file = os.fdopen(descriptor, "a+")
    try:
        try:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            yield False
            return
        yield True
    finally:
        lock_file.close()


def _default_lock_file() -> Path:
    runtime_root = Path(
        os.environ.get("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}")
    )
    if runtime_root.is_dir():
        return runtime_root / "apple-design-skill-update.lock"
    return Path(tempfile.gettempdir()) / f"apple-design-skill-update-{os.getuid()}.lock"


def _mode(value: str) -> str:
    normalized = value.lower()
    if normalized == "check":
        return "Check"
    if normalized == "apply":
        return "Apply"
    raise argparse.ArgumentTypeError("mode must be Check or Apply")


def _scope_profile(value: str) -> str:
    normalized = value.lower()
    if normalized in {SCOPE_PROFILE_WSL, SCOPE_PROFILE_LINUX}:
        return normalized
    raise argparse.ArgumentTypeError("scope profile must be wsl or linux")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Check or apply the published Apple Design skill to the selected "
            "consumer snapshots."
        )
    )
    parser.add_argument("--mode", type=_mode, default="Check")
    parser.add_argument(
        "--scope-profile",
        type=_scope_profile,
        default=SCOPE_PROFILE_WSL,
        metavar="{wsl,linux}",
        help=(
            "consumer layout: wsl (default) checks Linux and Windows snapshots; "
            "linux checks only this Linux user's Codex and Claude snapshots"
        ),
    )
    parser.add_argument("--expected-source-sha256")
    parser.add_argument("--test-source-path", type=Path, help=argparse.SUPPRESS)
    parser.add_argument(
        "--test-scope", action="append", default=[], help=argparse.SUPPRESS
    )
    parser.add_argument(
        "--test-fail-after-swaps", type=int, help=argparse.SUPPRESS
    )
    parser.add_argument("--test-lock-file", type=Path, help=argparse.SUPPRESS)
    parser.add_argument(
        "--test-windows-mount",
        type=Path,
        default=WINDOWS_MOUNT,
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--test-windows-profile",
        type=Path,
        default=WINDOWS_PROFILE,
        help=argparse.SUPPRESS,
    )
    return parser


def _run(args: argparse.Namespace) -> int:
    if args.test_scope:
        scopes = _parse_test_scopes(args.test_scope)
    else:
        home = Path.home()
        if args.scope_profile == SCOPE_PROFILE_WSL:
            _validate_windows_environment(
                args.test_windows_mount, args.test_windows_profile
            )
            _validate_linux_environment(home, "WSL")
            scopes = _default_scopes(home, args.test_windows_profile)
        else:
            _validate_linux_environment(home, "Linux")
            scopes = _linux_scopes(home)

    lock_path = args.test_lock_file or _default_lock_file()
    with _updater_lock(lock_path) as acquired:
        if not acquired:
            print("APPLE_DESIGN_SYNC status=skipped reason=lock-held")
            return 0
        with contextlib.ExitStack() as resources:
            if args.test_source_path:
                canonical_source = args.test_source_path.resolve(strict=True)
                _validate_skill_tree(canonical_source)
            else:
                temporary_root = Path(
                    resources.enter_context(
                        tempfile.TemporaryDirectory(prefix="apple-design-sync-")
                    )
                )
                canonical_source = _download_canonical_source(temporary_root)

            canonical_manifest = _tree_manifest(canonical_source)
            canonical_sha256 = _manifest_sha256(canonical_manifest)
            print(f"APPLE_DESIGN_SYNC source_sha256={canonical_sha256}")

            if args.mode == "Apply":
                expected = args.expected_source_sha256
                if expected is None:
                    raise SyncError(
                        "Apply requires --expected-source-sha256 from a prior Check"
                    )
                if not re.fullmatch(r"[0-9a-fA-F]{64}", expected):
                    raise SyncError(
                        "Expected source SHA-256 must contain exactly 64 hex characters"
                    )
                if expected.lower() != canonical_sha256:
                    raise SyncError(
                        "Expected source SHA-256 does not match canonical manifest: "
                        f"expected={expected.lower()} actual={canonical_sha256}"
                    )

            states = [
                _inspect_scope(scope, canonical_manifest) for scope in scopes
            ]
            for state in states:
                print(
                    f"APPLE_DESIGN_SYNC scope={state.scope.name} "
                    f"status={state.status}"
                )

            if args.mode == "Check":
                return 3 if any(state.status != "current" for state in states) else 0

            _apply_transaction(
                states,
                canonical_source,
                canonical_manifest,
                args.test_fail_after_swaps,
            )
            return 0


def main() -> int:
    args = _parser().parse_args()
    try:
        return _run(args)
    except Exception as error:
        print(
            f"APPLE_DESIGN_SYNC status=error message={error}",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
