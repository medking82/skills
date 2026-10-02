"""Build owned design references from the maintained standalone mode sources."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path, PurePosixPath


GENERATOR = "scripts/build-design-skill.py"
MODE_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
MODES = (
    "animate", "animate-expo", "animation-vocabulary", "apple-design", "ask-sonner", "break-ui",
    "emil-design-eng", "find-animation-opportunities", "improve-animations", "mobile-native",
    "pick-ui-library", "prototype", "review-animations", "write-swift",
)


class BundleError(RuntimeError):
    pass


def digest(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def without_frontmatter(content: bytes, source: Path) -> bytes:
    """Remove metadata only, preserving every byte of the remaining body."""
    lines = content.splitlines(keepends=True)
    if not lines or lines[0].strip() != b"---":
        raise BundleError(f"Missing frontmatter: {source}")
    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == b"---":
            body = b"".join(lines[index + 1 :])
            if not body.strip():
                raise BundleError(f"Empty guide: {source}")
            return body
    raise BundleError(f"Unclosed frontmatter: {source}")


def safe_path(root: Path, relative: str) -> Path:
    path = PurePosixPath(relative)
    if path.is_absolute() or not path.parts or any(
        part in {".", ".."} or ":" in part or "\\" in part for part in path.parts
    ) or path.as_posix() != relative:
        raise BundleError(f"Unsafe generated path: {relative!r}")
    target = root.joinpath(*path.parts)
    for candidate in (root, *target.parents, target):
        if candidate.is_symlink():
            raise BundleError(f"Symlink is not an owned bundle path: {candidate}")
    if not target.resolve().is_relative_to(root.resolve()):
        raise BundleError(f"Generated path escapes bundle: {relative}")
    for parent in target.parents:
        if parent == root.parent:
            break
        if parent.exists() and not parent.is_dir():
            raise BundleError(f"Generated parent is not a directory: {parent}")
    if target.exists() and not target.is_file():
        raise BundleError(f"Generated path is not a file: {target}")
    return target


def excluded(relative: Path) -> bool:
    return relative.name == "SKILL.md" or relative.as_posix() == "agents/openai.yaml"


def expected_bundle(repo: Path) -> tuple[dict[str, bytes], dict]:
    skills = repo / "skills"
    if not skills.is_dir() or skills.is_symlink():
        raise BundleError(f"Invalid skill source root: {skills}")
    discovered = {
        mode.name for mode in skills.iterdir()
        if mode.name != "design" and (mode / "SKILL.md").is_file()
    }
    if discovered != set(MODES):
        raise BundleError(
            "Mode inventory changed; update the accepted scope and design router before building. "
            f"Missing: {sorted(set(MODES) - discovered)}; new: {sorted(discovered - set(MODES))}"
        )
    router = skills / "design" / "SKILL.md"
    if not router.is_file() or router.is_symlink():
        raise BundleError(f"Missing design router: {router}")
    router_text = router.read_text(encoding="utf-8")
    routed = set(re.findall(r"\]\(references/([a-z0-9-]+)/guide\.md\)", router_text))
    if routed != set(MODES):
        raise BundleError("Design router must link every accepted mode guide, and no unknown modes")
    output: dict[str, bytes] = {}
    manifest = {"schema_version": 1, "generator": GENERATOR, "modes": {}, "files": {}}
    for mode in sorted(skills.iterdir()):
        if mode.name == "design" or not (mode / "SKILL.md").is_file():
            continue
        if mode.is_symlink() or not MODE_PATTERN.fullmatch(mode.name):
            raise BundleError(f"Invalid mode source: {mode}")
        entrypoint = mode / "SKILL.md"
        if entrypoint.is_symlink():
            raise BundleError(f"Symlink source: {entrypoint}")
        content = entrypoint.read_bytes()
        guide = f"{mode.name}/guide.md"
        output[guide] = without_frontmatter(content, entrypoint)
        manifest["modes"][mode.name] = {
            "entrypoint": entrypoint.relative_to(repo).as_posix(),
            "source_sha256": digest(content), "guide": guide,
        }
        manifest["files"][guide] = {
            "source": entrypoint.relative_to(repo).as_posix(),
            "source_sha256": digest(content), "sha256": digest(output[guide]),
        }
        for source in sorted(mode.rglob("*")):
            relative = source.relative_to(mode)
            if excluded(relative):
                continue
            if source.is_symlink():
                raise BundleError(f"Symlink source: {source}")
            if not source.is_file():
                continue
            target = f"{mode.name}/{relative.as_posix()}"
            if target in output:
                raise BundleError(f"Supporting file collides with guide: {source}")
            data = source.read_bytes()
            output[target] = data
            manifest["files"][target] = {
                "source": source.relative_to(repo).as_posix(),
                "source_sha256": digest(data), "sha256": digest(data),
            }
    if not manifest["modes"]:
        raise BundleError("No source modes found")
    if len({name.casefold() for name in output}) != len(output):
        raise BundleError("Generated paths collide on case-insensitive filesystems")
    return output, manifest


def read_owned_manifest(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
        if set(manifest) != {"schema_version", "generator", "modes", "files"} or (
            manifest["schema_version"] != 1 or manifest["generator"] != GENERATOR
        ):
            raise ValueError("Unknown manifest owner or schema")
        if not isinstance(manifest["modes"], dict) or not isinstance(manifest["files"], dict):
            raise ValueError("Invalid manifest collections")
        for mode, info in manifest["modes"].items():
            if not MODE_PATTERN.fullmatch(mode) or info != {
                "entrypoint": f"skills/{mode}/SKILL.md",
                "source_sha256": info["source_sha256"], "guide": f"{mode}/guide.md",
            } or not re.fullmatch(r"[0-9a-f]{64}", info["source_sha256"]):
                raise ValueError("Invalid mode ownership")
        for relative, info in manifest["files"].items():
            target = PurePosixPath(relative)
            mode = target.parts[0]
            if mode not in manifest["modes"] or len(target.parts) < 2:
                raise ValueError("File outside declared mode")
            source = f"skills/{mode}/" + (
                "SKILL.md" if target.parts[1:] == ("guide.md",) else "/".join(target.parts[1:])
            )
            if set(info) != {"source", "source_sha256", "sha256"} or info["source"] != source:
                raise ValueError("Invalid file ownership")
            if target.name == "SKILL.md" or target.parts[1:] == ("agents", "openai.yaml"):
                raise ValueError("Manifest cannot own discovery metadata")
            if any(not re.fullmatch(r"[0-9a-f]{64}", info[key]) for key in ("sha256", "source_sha256")):
                raise ValueError("Invalid digest")
    except (ValueError, TypeError, KeyError, IndexError, AttributeError) as error:
        raise BundleError(f"Invalid ownership manifest {path}: {error}") from error
    return manifest


def build(repo: Path, *, check: bool = False) -> bool:
    output, expected = expected_bundle(repo)
    root = repo / "skills" / "design" / "references"
    manifest_path = safe_path(root, "sources.json")
    previous = read_owned_manifest(manifest_path)
    owned = previous["files"] if previous else {}
    # Admission happens before mkdir/write/unlink. Local drift and unowned
    # collisions are not silently overwritten, even when sources changed too.
    targets = {name: safe_path(root, name) for name in output.keys() | owned.keys()}
    for name, info in owned.items():
        path = targets[name]
        if path.exists() and digest(path.read_bytes()) != info["sha256"]:
            raise BundleError(f"Generated file has local edits: {path}")
    for name, path in targets.items():
        if name in output and name not in owned and path.exists():
            raise BundleError(f"Unowned destination collision: {path}")
    manifest_bytes = (json.dumps(expected, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    current = previous == expected and all(
        targets[name].exists() and targets[name].read_bytes() == data for name, data in output.items()
    )
    if check or current:
        return current
    for name, data in output.items():
        path = targets[name]
        if not path.exists() or path.read_bytes() != data:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
    for name in owned.keys() - output.keys():
        if targets[name].exists():
            targets[name].unlink()
    root.mkdir(parents=True, exist_ok=True)
    manifest_path.write_bytes(manifest_bytes)
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--check", action="store_true", help="Check without writing any files")
    args = parser.parse_args(argv)
    try:
        current = build(args.repo.resolve(), check=args.check)
    except (BundleError, OSError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print("Design references are current." if current else "Design references are stale; run the builder.")
    return 0 if current else 1


if __name__ == "__main__":
    raise SystemExit(main())
