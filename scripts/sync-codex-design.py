"""Update only the enrolled design package from medking82/skills:main."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import tempfile
import urllib.request
import zipfile


REPOSITORY = "medking82/skills"
API = "https://api.github.com/repos/" + REPOSITORY
MAX_BYTES = 32 * 1024 * 1024
MAX_FILES = 600


class SyncError(RuntimeError):
    pass


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def relative(name: str) -> PurePosixPath:
    path = PurePosixPath(name)
    if not name or path.is_absolute() or path.as_posix() != name:
        raise SyncError("Unsafe package path: " + name)
    for part in path.parts:
        stem = part.split(".")[0].upper()
        if (part in (".", "..") or part.endswith((" ", "."))
                or re.search(r'[\\:<>"|?*\x00-\x1f]', part)
                or stem in {"CON", "PRN", "AUX", "NUL"}
                or re.fullmatch(r"(?:COM|LPT)[1-9]", stem)):
            raise SyncError("Unsafe package path: " + name)
    return path


def regular(path: Path) -> Path:
    path = path.absolute()
    for item in (path, *path.parents):
        if item.is_symlink() or (hasattr(item, "is_junction") and item.is_junction()):
            raise SyncError("Linked path requires reconciliation: " + str(item))
    return path


def tree_files(root: Path) -> dict[str, str]:
    regular(root)
    if not root.is_dir():
        raise SyncError("Installed design package is missing")
    result = {}
    for base, directories, names in os.walk(root, followlinks=False):
        for name in directories + names:
            item = regular(Path(base) / name)
            if item.is_file():
                result[item.relative_to(root).as_posix()] = digest(item.read_bytes())
            elif not item.is_dir():
                raise SyncError("Nonregular installed file: " + str(item))
    return result


def request(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "codex-design-sync"})
    with urllib.request.urlopen(req, timeout=45) as response:
        data = response.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise SyncError("GitHub response exceeds the package size limit")
    return data


def revision(value: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{40}", value):
        raise SyncError("Invalid source commit")
    return value


def fetch_head() -> str:
    return revision(json.loads(request(API + "/git/ref/heads/main"))["object"]["sha"])


def check_ancestry(before: str, after: str) -> None:
    comparison = json.loads(request(API + "/compare/" + revision(before) + "..." + revision(after)))
    if comparison.get("status") not in ("ahead", "identical") or comparison.get("behind_by") != 0:
        raise SyncError("Source history was rewritten; installed version retained")


def extract_package(data: bytes, commit: str) -> dict[str, bytes]:
    prefix = "skills-" + revision(commit) + "/skills/design/"
    package = {}
    seen = set()
    total = 0
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        for item in archive.infolist():
            if not item.filename.startswith(prefix) or item.is_dir():
                continue
            name = item.filename[len(prefix):]
            relative(name)
            if item.external_attr >> 16 & 0o170000 not in (0, 0o100000):
                raise SyncError("Nonregular archive entry: " + name)
            if name.casefold() in seen:
                raise SyncError("Duplicate package path: " + name)
            seen.add(name.casefold())
            total += item.file_size
            if len(seen) > MAX_FILES or total > MAX_BYTES:
                raise SyncError("Package exceeds the enrollment limits")
            package[name] = archive.read(item)
    validate_package(package)
    return package


def download_package(commit: str) -> dict[str, bytes]:
    return extract_package(request("https://codeload.github.com/" + REPOSITORY + "/zip/" + revision(commit)), commit)


def validate_package(package: dict[str, bytes]) -> list[str]:
    if not package or len(package) > MAX_FILES or sum(map(len, package.values())) > MAX_BYTES:
        raise SyncError("Invalid package size")
    names = set()
    for name in package:
        relative(name)
        if name.casefold() in names:
            raise SyncError("Duplicate package path: " + name)
        names.add(name.casefold())
        if PurePosixPath(name).name.casefold() == "skill.md" and name != "SKILL.md":
            raise SyncError("Unexpected specialist discovery entrypoint")
    text = package.get("SKILL.md", b"").decode("utf-8")
    frontmatter = re.match(r"\A---\r?\n(.*?)\r?\n---(?:\r?\n|$)", text, re.S)
    if not frontmatter or not re.search(r"^name:\s*design\s*$", frontmatter[1], re.M):
        raise SyncError("Missing design entrypoint metadata")
    if not re.search(r"^description:\s*\S", frontmatter[1], re.M):
        raise SyncError("Missing design description")
    manifest = json.loads(package["references/sources.json"])
    modes = manifest.get("modes")
    if manifest.get("schema_version") != 1 or not isinstance(modes, dict) or not modes:
        raise SyncError("Invalid design source manifest")
    for name, mode in modes.items():
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name):
            raise SyncError("Invalid design mode name")
        guide = "references/" + relative(mode["guide"]).as_posix()
        if guide not in package or "(" + guide + ")" not in text:
            raise SyncError("Missing routed mode guide: " + name)
    expected = {"references/" + relative(name).as_posix(): entry["sha256"]
                for name, entry in manifest["files"].items()}
    actual = {name: digest(data) for name, data in package.items()
              if name.startswith("references/") and name != "references/sources.json"}
    if actual != expected:
        raise SyncError("Design references do not match their manifest")
    return sorted(modes)


def atomic_json(path: Path, value: dict) -> None:
    regular(path)
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix=path.name + ".", delete=False) as handle:
        temporary = Path(handle.name)
        handle.write((json.dumps(value, indent=2, sort_keys=True) + "\n").encode())
        handle.flush()
        os.fsync(handle.fileno())
    try:
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def windows_dacl(path: Path) -> tuple[str, bool]:
    """Read the owner and DACL without relying on account names."""
    import ctypes
    from ctypes import wintypes

    api = ctypes.WinDLL("advapi32", use_last_error=True)
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    pointer = ctypes.c_void_p
    api.GetNamedSecurityInfoW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                                         pointer, pointer, ctypes.POINTER(pointer), pointer,
                                         ctypes.POINTER(pointer)]
    api.GetNamedSecurityInfoW.restype = wintypes.DWORD
    api.GetSecurityDescriptorControl.argtypes = [pointer, ctypes.POINTER(wintypes.WORD),
                                                 ctypes.POINTER(wintypes.DWORD)]
    api.GetSecurityDescriptorControl.restype = wintypes.BOOL
    api.ConvertSecurityDescriptorToStringSecurityDescriptorW.argtypes = [
        pointer, wintypes.DWORD, wintypes.DWORD, ctypes.POINTER(pointer), pointer]
    api.ConvertSecurityDescriptorToStringSecurityDescriptorW.restype = wintypes.BOOL
    kernel.LocalFree.argtypes = [pointer]
    kernel.LocalFree.restype = pointer

    owner, dacl, descriptor, text = pointer(), pointer(), pointer(), pointer()
    status = api.GetNamedSecurityInfoW(str(path), 1, 5, ctypes.byref(owner), None, ctypes.byref(dacl),
                                       None, ctypes.byref(descriptor))
    if status:
        raise ctypes.WinError(status, "GetNamedSecurityInfoW")
    try:
        if not owner.value or not dacl.value:
            raise SyncError("Cannot safely preserve an unknown owner or null DACL: " + str(path))
        control, revision = wintypes.WORD(), wintypes.DWORD()
        if not api.GetSecurityDescriptorControl(descriptor, ctypes.byref(control), ctypes.byref(revision)):
            raise ctypes.WinError(ctypes.get_last_error(), "GetSecurityDescriptorControl")
        if not api.ConvertSecurityDescriptorToStringSecurityDescriptorW(descriptor, 1, 5,
                                                                         ctypes.byref(text), None):
            raise ctypes.WinError(ctypes.get_last_error(), "ConvertSecurityDescriptorToStringSecurityDescriptorW")
        return ctypes.wstring_at(text), bool(control.value & 0x1000)
    finally:
        if text.value:
            kernel.LocalFree(text)
        if descriptor.value:
            kernel.LocalFree(descriptor)


def windows_set_dacl(path: Path, saved: tuple[str, bool]) -> None:
    """Restore only the saved DACL; Windows propagates its inheritable entries."""
    import ctypes
    from ctypes import wintypes

    api = ctypes.WinDLL("advapi32", use_last_error=True)
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    pointer = ctypes.c_void_p
    api.ConvertStringSecurityDescriptorToSecurityDescriptorW.argtypes = [
        wintypes.LPCWSTR, wintypes.DWORD, ctypes.POINTER(pointer), pointer]
    api.ConvertStringSecurityDescriptorToSecurityDescriptorW.restype = wintypes.BOOL
    api.GetSecurityDescriptorDacl.argtypes = [pointer, ctypes.POINTER(wintypes.BOOL),
                                               ctypes.POINTER(pointer), ctypes.POINTER(wintypes.BOOL)]
    api.GetSecurityDescriptorDacl.restype = wintypes.BOOL
    api.SetNamedSecurityInfoW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                                         pointer, pointer, pointer, pointer]
    api.SetNamedSecurityInfoW.restype = wintypes.DWORD
    kernel.LocalFree.argtypes = [pointer]
    kernel.LocalFree.restype = pointer

    descriptor, dacl = pointer(), pointer()
    if not api.ConvertStringSecurityDescriptorToSecurityDescriptorW(saved[0], 1,
                                                                     ctypes.byref(descriptor), None):
        raise ctypes.WinError(ctypes.get_last_error(), "ConvertStringSecurityDescriptorToSecurityDescriptorW")
    try:
        present, defaulted = wintypes.BOOL(), wintypes.BOOL()
        if not api.GetSecurityDescriptorDacl(descriptor, ctypes.byref(present),
                                              ctypes.byref(dacl), ctypes.byref(defaulted)):
            raise ctypes.WinError(ctypes.get_last_error(), "GetSecurityDescriptorDacl")
        if not present.value or not dacl.value:
            raise SyncError("Cannot safely restore a null DACL: " + str(path))
        flags = 0x80000004 if saved[1] else 0x20000004
        status = api.SetNamedSecurityInfoW(str(path), 1, flags, None, None, dacl, None)
        if status:
            raise ctypes.WinError(status, "SetNamedSecurityInfoW")
    finally:
        kernel.LocalFree(descriptor)


def security_snapshot(root: Path) -> dict[str, tuple[str, bool]] | None:
    if os.name != "nt":
        return None
    result = {".": windows_dacl(root)}
    for base, directories, names in os.walk(root, followlinks=False):
        for name in directories + names:
            item = regular(Path(base) / name)
            result[item.relative_to(root).as_posix()] = windows_dacl(item)
    return result


def restore_security(root: Path, saved: dict[str, tuple[str, bool]] | None) -> None:
    if saved is None:
        return
    windows_set_dacl(root, saved["."])
    restored = security_snapshot(root)
    # Applying a DACL marks it auto-inherited. That control flag is bookkeeping;
    # compare protection and the ordered ACEs, including their inheritance flags.
    def comparable(value):
        sddl, protected = value
        owner, separator, dacl = sddl.partition("D:")
        if not separator:
            raise SyncError("Invalid saved design DACL")
        flags, separator, entries = dacl.partition("(")
        return owner + "D:" + flags.replace("AI", "") + separator + entries, protected
    if any(comparable(restored[name]) != comparable(saved[name])
           for name in saved.keys() & restored.keys()):
        raise SyncError("Existing design permissions could not be preserved; update cancelled")


def sync(runtime: Path, destination: Path, *, enroll: str | None = None, apply: bool = False) -> dict:
    regular(runtime)
    regular(destination)
    state_path = runtime / "state.json"
    installed = tree_files(destination)
    if enroll:
        if state_path.exists():
            raise SyncError("Design is already enrolled; existing receipt retained")
        head = revision(enroll)
        package = download_package(head)
        hashes = {name: digest(data) for name, data in package.items()}
        if installed != hashes:
            raise SyncError("Installed design differs from the enrollment commit")
        atomic_json(state_path, {"repository": REPOSITORY, "destination": str(destination.absolute()),
                                 "commit": head, "files": hashes})
        return {"status": "enrolled", "commit": head, "modes": validate_package(package)}
    before = state_path.read_bytes()
    state = json.loads(before)
    if state["repository"] != REPOSITORY or state["destination"] != str(destination.absolute()):
        raise SyncError("Unexpected design ownership receipt")
    revision(state["commit"])
    if installed != state["files"]:
        raise SyncError("Local design modifications detected; installed files retained")
    head = fetch_head()
    if head == state["commit"]:
        return {"status": "unchanged", "commit": head}
    check_ancestry(state["commit"], head)
    package = download_package(head)
    modes = validate_package(package)
    desired = dict(state, commit=head, files={name: digest(data) for name, data in package.items()})
    report = {"status": "available", "commit": head, "previous_commit": state["commit"], "modes": modes}
    if not apply:
        return report
    if tree_files(destination) != installed or state_path.read_bytes() != before:
        raise SyncError("Installed package changed during download; update cancelled")
    if desired["files"] == installed:
        atomic_json(state_path, desired)
        return dict(report, status="unchanged")
    with tempfile.TemporaryDirectory(prefix="stage-", dir=runtime) as temporary:
        if Path(temporary).resolve().parent != runtime.resolve():
            raise SyncError("Staging directory is outside the enrolled runtime")
        stage = Path(temporary) / "design"
        stage.mkdir()
        for name, data in package.items():
            target = stage.joinpath(*relative(name).parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        backup = runtime / "backups" / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ"))
        regular(backup)
        backup.mkdir(parents=True)
        (backup / "state.before.json").write_bytes(before)
        if tree_files(destination) != installed or state_path.read_bytes() != before:
            raise SyncError("Installed package changed before replacement")
        security = security_snapshot(destination)
        destination.rename(backup / "design")
        try:
            if security_snapshot(backup / "design") != security:
                raise SyncError("Installed permissions changed before replacement")
            stage.rename(destination)
            restore_security(destination, security)
            atomic_json(state_path, desired)
            if tree_files(destination) != desired["files"]:
                raise SyncError("Installed package changed during replacement")
        except BaseException:
            if destination.exists():
                if tree_files(destination) != desired["files"]:
                    raise SyncError("Concurrent edit during rollback; backup retained at " + str(backup))
                destination.rename(backup / "failed-design")
            (backup / "design").rename(destination)
            if state_path.read_bytes() != before:
                if json.loads(state_path.read_bytes()) != desired:
                    raise SyncError("Concurrent receipt edit; recovery backup retained at " + str(backup))
                atomic_json(state_path, state)
            raise
    return dict(report, status="updated", backup=str(backup))


@contextmanager
def run_lock(path: Path):
    regular(path)
    with path.open("a+b") as handle:
        if not path.stat().st_size:
            handle.write(b"0")
            handle.flush()
        handle.seek(0)
        if os.name == "nt":
            import msvcrt
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            yield
        finally:
            if os.name == "nt":
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle, fcntl.LOCK_UN)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime", type=Path, default=Path.home() / ".codex/design-sync")
    parser.add_argument("--enroll", metavar="COMMIT")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    runtime = regular(args.runtime)
    if runtime != (Path.home() / ".codex/design-sync").absolute():
        parser.error("Runtime must be the current user's .codex/design-sync")
    runtime.mkdir(parents=True, exist_ok=True)
    destination = Path.home() / ".codex/skills/design"
    try:
        with run_lock(runtime / "run.lock"):
            try:
                report = sync(runtime, destination, enroll=args.enroll, apply=args.apply)
                code = 0
            except Exception as error:
                report = {"status": "attention", "reason": str(error)}
                code = 2
            report["checked_at_utc"] = datetime.now(timezone.utc).isoformat()
            atomic_json(runtime / "last-run.json", report)
            with (runtime / "runs.jsonl").open("a", encoding="utf-8") as log:
                log.write(json.dumps(report, sort_keys=True) + "\n")
    except OSError as error:
        report = {"status": "attention", "reason": "Updater busy or runtime unavailable: " + str(error)}
        code = 2
    print(json.dumps(report, sort_keys=True))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
