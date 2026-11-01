from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("sync_hallmark", REPO_ROOT / "scripts/sync-hallmark.py")
assert SPEC and SPEC.loader
sync = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(sync)
COMMIT = "a" * 40


class HallmarkSnapshotTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="hallmark-sync-", dir=REPO_ROOT / "tests")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.repo = self.root / "repo"
        self.source = self.root / "upstream"
        self.snapshot = self.repo / "skills/hallmark/upstream"
        for name, content in {
            "SKILL.md": b"---\nname: hallmark\n---\n# Guide\n",
            "LICENSE": b"MIT License\n",
            "references/gates.md": b"# Gates\n",
            "references/themes/index.json": b"{\"themes\": []}\n",
            "references/themes/dusk.jpg": b"\xff\xd8\xff\xe0binary\r\n",
            "scripts/sloplint.mjs": b"// lint\n",
            "scripts/theme.mjs": b"// theme\n",
            "scripts/photos.json": b"[]\n",
            "scripts/imagegen.mjs": b"fetch('https://api.together.xyz')\n",
            "scripts/install-hook.mjs": b"// writes ~/.claude/settings.json\n",
            "scripts/fixtures/slopped.html": b"<p>fixture</p>\n",
            "agents/openai.yaml": b"policy: {}\n",
        }.items():
            self.write(name, content)

    def write(self, name: str, content: bytes) -> None:
        target = self.source / "skills/hallmark" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)

    def test_snapshot_drops_paid_generation_installers_hooks_and_fixtures(self) -> None:
        self.assertTrue(sync.refresh(self.repo, self.source, COMMIT))
        files = {p.relative_to(self.snapshot).as_posix() for p in self.snapshot.rglob("*") if p.is_file()}
        self.assertIn("guide.md", files)
        self.assertNotIn("SKILL.md", files)
        for name in ("scripts/imagegen.mjs", "scripts/install-hook.mjs", "scripts/fixtures/slopped.html",
                     "agents/openai.yaml"):
            self.assertNotIn(name, files)
        info = json.loads((self.snapshot / "source.json").read_text(encoding="utf-8"))
        self.assertEqual(info["commit"], COMMIT)
        self.assertIn("scripts/imagegen.mjs", info["excluded"])

    def test_binary_assets_keep_exact_bytes_and_text_is_lf(self) -> None:
        self.write("references/gates.md", b"# Gates\r\nline\r\n")
        sync.refresh(self.repo, self.source, COMMIT)
        self.assertEqual((self.snapshot / "references/themes/dusk.jpg").read_bytes(), b"\xff\xd8\xff\xe0binary\r\n")
        self.assertEqual((self.snapshot / "references/gates.md").read_bytes(), b"# Gates\nline\n")

    def test_check_detects_a_reference_update_without_writing(self) -> None:
        sync.refresh(self.repo, self.source, COMMIT)
        self.write("references/gates.md", b"# Gates v2\n")
        self.assertFalse(sync.refresh(self.repo, self.source, "b" * 40, check=True))
        self.assertEqual((self.snapshot / "references/gates.md").read_bytes(), b"# Gates\n")
        self.assertTrue(sync.refresh(self.repo, self.source, "b" * 40))

    def test_script_change_stops_until_reviewed(self) -> None:
        sync.refresh(self.repo, self.source, COMMIT)
        self.write("scripts/sloplint.mjs", b"// changed\n")
        with self.assertRaisesRegex(sync.SnapshotError, "manual review"):
            sync.refresh(self.repo, self.source, "b" * 40)
        self.assertTrue(sync.refresh(self.repo, self.source, "b" * 40, allow_code_updates=True))

    def test_local_edits_are_not_overwritten(self) -> None:
        sync.refresh(self.repo, self.source, COMMIT)
        (self.snapshot / "references/gates.md").write_bytes(b"local edit\n")
        with self.assertRaisesRegex(sync.SnapshotError, "local edits"):
            sync.refresh(self.repo, self.source, COMMIT)

    def test_missing_required_files_fail_before_any_write(self) -> None:
        (self.source / "skills/hallmark/scripts/sloplint.mjs").unlink()
        with self.assertRaisesRegex(sync.SnapshotError, "Incomplete"):
            sync.refresh(self.repo, self.source, COMMIT)
        self.assertFalse(self.snapshot.exists())


if __name__ == "__main__":
    unittest.main()
