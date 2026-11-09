#!/usr/bin/env python3
"""Qualify immutable source with the project's pinned shared Linux runner."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile


def gitdir(repo):
    repo = Path(repo).resolve()
    marker = repo / ".git"
    if marker.is_file():
        raw = marker.read_text().strip().removeprefix("gitdir: ")
        if len(raw) > 2 and raw[1] == ":":
            raw = "/mnt/" + raw[0].lower() + "/" + raw[3:].replace("\\", "/")
        return (repo / raw).resolve()
    return marker


def git(repo, *args):
    return subprocess.check_output(["git", "--git-dir=" + str(gitdir(repo)), *args], stderr=subprocess.PIPE)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runner", required=True, type=Path,
                        help="Local hermes-fleet-sync checkout (never fetched or modified)")
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--commit", default="HEAD")
    parser.add_argument("--project", default="offline")
    parser.add_argument("--state", required=True, type=Path)
    parser.add_argument("--class-shards", type=int, default=1)
    parser.add_argument("--timings", type=Path)
    parser.add_argument("--reuse", action="store_true")
    parser.add_argument("--max-age", type=float, default=86400)
    args = parser.parse_args()
    if sys.platform != "linux":
        parser.error("Run this command in WSL/Linux with native Python/Node and Linux state storage")
    repo = args.repo.resolve()
    # Resolve Git metadata for source and runner without changing either checkout.
    def source(*argv):
        return git(repo, *argv)
    commit = source("rev-parse", "--verify", args.commit + "^{commit}").decode().strip()
    manifest_bytes = source("show", commit + ":release-qualification.json")
    manifest = json.loads(manifest_bytes)
    revision = manifest["runnerCommit"]
    if len(revision) != 40 or any(c not in "0123456789abcdef" for c in revision):
        parser.error("runnerCommit must be an immutable full Git SHA")
    selected = manifest["projects"][args.project]
    if args.reuse and not selected.get("localReuse", False):
        parser.error("This lane has mutable/external inputs; local reuse is disabled")
    state = args.state.resolve()
    if str(state).startswith("/mnt/"):
        parser.error("Use a WSL-native state directory, not a mounted Windows directory")
    state.mkdir(parents=True, exist_ok=True)
    # Read exact committed engine blobs. A sibling may have a different HEAD or
    # dirty files in its checkout; neither can affect this pinned execution.
    with tempfile.TemporaryDirectory(prefix="runner-", dir=state) as raw:
        engine = Path(raw)
        for name in ("release_qualification.py", "release_unittest.py"):
            (engine / name).write_bytes(git(args.runner, "show", revision + ":" + name))
        catalog = engine / "manifest.json"
        catalog.write_bytes(manifest_bytes)
        command = [sys.executable, "-B", str(engine / "release_qualification.py"),
                   "--repo", str(repo), "--commit", commit,
                   "--manifest", str(catalog), "--project", args.project,
                   "--state", str(state), "--class-shards", str(args.class_shards),
                   "--max-age", str(args.max_age)]
        if args.timings:
            command.extend(["--timings", str(args.timings.resolve())])
        if args.reuse:
            command.append("--reuse")
        return subprocess.call(command)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
        print("Release qualification failed: " + type(error).__name__, file=sys.stderr)
        raise SystemExit(2)
