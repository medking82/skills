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
    "animate", "animate-expo", "animation-performance", "animation-vocabulary", "apple-design", "ask-sonner", "break-ui",
    "emil-design-eng", "find-animation-opportunities", "impeccable", "improve-animations", "mobile-native",
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


def mode_metadata(entrypoint: Path, content: bytes) -> tuple[str, bool]:
    """Expose routing metadata while retaining each source's invocation policy."""
    try:
        lines = content.decode("utf-8").splitlines()
    except UnicodeDecodeError as error:
        raise BundleError(f"Invalid UTF-8 metadata: {entrypoint}") from error
    end = next((i for i, line in enumerate(lines[1:], 1) if line.strip() == "---"), None)
    if end is None:
        raise BundleError(f"Unclosed frontmatter: {entrypoint}")
    descriptions = [(i, line.partition(":")[2].strip()) for i, line in enumerate(lines[1:end], 1)
                    if line.startswith("description:")]
    if len(descriptions) != 1:
        raise BundleError(f"Missing or duplicate description: {entrypoint}")
    index, description = descriptions[0]
    if description in {">", ">-", "|", "|-"}:
        parts = []
        for line in lines[index + 1:end]:
            if line and not line[0].isspace():
                break
            parts.append(line.strip())
        description = " ".join(part for part in parts if part)
    elif len(description) >= 2 and description[0] == description[-1] and description[0] in "\"'":
        if description[0] == '"':
            try:
                description = json.loads(description)
            except ValueError as error:
                raise BundleError(f"Invalid description: {entrypoint}") from error
        else:
            description = description[1:-1].replace("''", "'")
    if not isinstance(description, str) or not description.strip() or len(description) > 4096:
        raise BundleError(f"Invalid description: {entrypoint}")
    metadata = entrypoint.parent / "agents/openai.yaml"
    if metadata.is_symlink():
        raise BundleError(f"Symlink invocation metadata: {metadata}")
    implicit = True
    if metadata.exists():
        lines = metadata.read_text(encoding="utf-8").splitlines()
        starts = [i for i, line in enumerate(lines) if line.strip() == "policy:" and not line[0].isspace()]
        if len(starts) > 1:
            raise BundleError(f"Duplicate invocation policy: {metadata}")
        if starts:
            values = []
            for line in lines[starts[0] + 1:]:
                if line.strip() and not line[0].isspace() and not line.lstrip().startswith("#"):
                    break
                if re.match(r"\s+allow_implicit_invocation\s*:", line):
                    match = re.fullmatch(r"\s+allow_implicit_invocation:\s*(true|false)\s*", line)
                    if not match:
                        raise BundleError(f"Invalid invocation policy: {metadata}")
                    values.append(match.group(1) == "true")
            if len(values) != 1:
                raise BundleError(f"Invalid invocation policy: {metadata}")
            implicit = values[0]
    return description.strip(), implicit


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
    if not set(MODES).issubset(discovered):
        raise BundleError(
            "Mode inventory changed; required modes are missing: " + str(sorted(set(MODES) - discovered))
        )
    router = skills / "design" / "SKILL.md"
    if not router.is_file() or router.is_symlink():
        raise BundleError(f"Missing design router: {router}")
    router_text = router.read_text(encoding="utf-8")
    routed = set(re.findall(r"\]\(references/([a-z0-9-]+)/guide\.md\)", router_text))
    if not set(MODES).issubset(routed) or not routed.issubset(discovered):
        raise BundleError("Design router must link every core mode guide, and no unknown modes")
    if discovered - routed and "references/sources.json" not in router_text:
        raise BundleError("Design router must expose the full mode inventory")
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
        description, implicit = mode_metadata(entrypoint, content)
        manifest["modes"][mode.name] = {
            "entrypoint": entrypoint.relative_to(repo).as_posix(),
            "source_sha256": digest(content), "guide": guide,
            "description": description, "allow_implicit_invocation": implicit,
        }
        manifest["files"][guide] = {
            "source": entrypoint.relative_to(repo).as_posix(),
            "source_sha256": digest(content), "sha256": digest(output[guide]),
        }
        for source in sorted(mode.rglob("*"), key=lambda path: path.relative_to(mode).as_posix()):
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
            base = {"entrypoint", "source_sha256", "guide"}
            if (not MODE_PATTERN.fullmatch(mode) or set(info) not in
                    (base, base | {"description", "allow_implicit_invocation"})
                    or info["entrypoint"] != f"skills/{mode}/SKILL.md"
                    or info["guide"] != f"{mode}/guide.md"
                    or not re.fullmatch(r"[0-9a-f]{64}", info["source_sha256"])
                    or ("description" in info and (not isinstance(info["description"], str)
                        or not info["description"].strip() or len(info["description"]) > 4096
                        or type(info["allow_implicit_invocation"]) is not bool))):
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
