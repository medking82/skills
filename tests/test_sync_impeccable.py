from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("sync_impeccable", REPO_ROOT / "scripts/sync-impeccable.py")
assert SPEC and SPEC.loader
sync = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(sync)


class ImpeccableSnapshotTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="impeccable-sync-", dir=REPO_ROOT / "tests")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.repo = self.root / "repo"
        self.source = self.root / "fork"
        self.snapshot = self.repo / "skills/impeccable/upstream"
        for name, content in {
            ".agents/skills/impeccable/SKILL.md": b"---\nname: impeccable\n---\n# Guide\n",
            ".agents/skills/impeccable/reference/craft-floor.md": b"# Craft\n",
            ".agents/skills/impeccable/scripts/VERSION": b"0.1.18\n",
            ".agents/skills/impeccable/scripts/engine-checksums.txt": b"checksum\n",
            ".agents/skills/impeccable/scripts/impeccable.cmd": b"@echo off\n",
            ".agents/skills/impeccable/agents/openai.yaml": b"policy: {}\n",
            "LICENSE": b"Apache License\n",
            "NOTICE.md": b"Third-party attribution\n",
        }.items():
            self.write(name, content)

    def write(self, name: str, content: bytes) -> None:
        target = self.source / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)

    def snapshot_files(self) -> dict[str, bytes]:
        if not self.snapshot.exists():
            return {}
        return {path.relative_to(self.snapshot).as_posix(): path.read_bytes()
                for path in self.snapshot.rglob("*") if path.is_file()}

    def test_snapshot_retains_attribution_without_an_extra_skill_entrypoint(self) -> None:
        self.assertTrue(sync.refresh(self.repo, self.source, "a" * 40))
        self.assertEqual((self.snapshot / "guide.md").read_bytes(),
                         (self.source / ".agents/skills/impeccable/SKILL.md").read_bytes())
        self.assertEqual((self.snapshot / "LICENSE").read_bytes(), b"Apache License\n")
        self.assertEqual(list(self.snapshot.rglob("SKILL.md")), [])
        self.assertEqual(list(self.snapshot.rglob("openai.yaml")), [])
        self.assertEqual(json.loads((self.snapshot / "source.json").read_text())["commit"], "a" * 40)
        self.assertTrue(sync.refresh(self.repo, self.source, "a" * 40, check=True))

    def test_reference_update_is_detected_without_writing_then_refreshed(self) -> None:
        sync.refresh(self.repo, self.source, "a" * 40)
        before = self.snapshot_files()
        self.write(".agents/skills/impeccable/reference/craft-floor.md", b"# Updated\n")
        self.assertFalse(sync.refresh(self.repo, self.source, "b" * 40, check=True))
        self.assertEqual(self.snapshot_files(), before)
        sync.refresh(self.repo, self.source, "b" * 40)
        self.assertEqual((self.snapshot / "reference/craft-floor.md").read_bytes(), b"# Updated\n")

    def test_executable_change_stops_the_whole_update_until_reviewed(self) -> None:
        sync.refresh(self.repo, self.source, "a" * 40)
        before = self.snapshot_files()
        self.write(".agents/skills/impeccable/reference/craft-floor.md", b"# Updated\n")
        self.write(".agents/skills/impeccable/scripts/VERSION", b"0.1.19\n")
        with self.assertRaisesRegex(sync.SnapshotError, "manual review"):
            sync.refresh(self.repo, self.source, "b" * 40)
        self.assertEqual(self.snapshot_files(), before)
        sync.refresh(self.repo, self.source, "b" * 40, allow_code_updates=True)
        self.assertEqual((self.snapshot / "scripts/VERSION").read_bytes(), b"0.1.19\n")

    def test_local_edits_and_unowned_files_are_not_overwritten(self) -> None:
        sync.refresh(self.repo, self.source, "a" * 40)
        (self.snapshot / "my-notes.md").write_bytes(b"Keep this\n")
        before = self.snapshot_files()
        with self.assertRaisesRegex(sync.SnapshotError, "local edits, unowned files"):
            sync.refresh(self.repo, self.source, "b" * 40)
        self.assertEqual(self.snapshot_files(), before)


if __name__ == "__main__":
    unittest.main()
