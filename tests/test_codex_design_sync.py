from __future__ import annotations

import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("codex_design_sync", ROOT / "scripts/sync-codex-design.py")
updater = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(updater)
OLD = "1" * 40
NEW = "2" * 40


def package(*modes: str) -> dict[str, bytes]:
    guides = {mode + "/guide.md": ("# " + mode + "\n").encode() for mode in modes}
    manifest = {
        "schema_version": 1,
        "modes": {mode: {"guide": mode + "/guide.md"} for mode in modes},
        "files": {name: {"sha256": hashlib.sha256(data).hexdigest()} for name, data in guides.items()},
    }
    return {
        "SKILL.md": ("---\nname: design\ndescription: Design interfaces\n---\n\n" + "\n".join(
            "[" + mode + "](references/" + mode + "/guide.md)" for mode in modes)).encode(),
        "LICENSE": b"Test license\n",
        "references/sources.json": json.dumps(manifest).encode(),
        **{"references/" + name: data for name, data in guides.items()},
    }


class CodexDesignSyncTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="codex-design-sync-", dir=ROOT / "tests")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.runtime = self.root / "runtime"
        self.runtime.mkdir()
        self.destination = self.root / "skills/design"
        self.old_package = package("animate")
        self.write_package(self.old_package)
        (self.root / "config.toml").write_bytes(b"model = 'preserved'\n")
        (self.root / "skills/other").mkdir()
        (self.root / "skills/other/SKILL.md").write_bytes(b"other skill\n")
        with patch.object(updater, "download_package", return_value=self.old_package):
            result = updater.sync(self.runtime, self.destination, enroll=OLD)
        self.assertEqual(result["status"], "enrolled")

    def write_package(self, files: dict[str, bytes]) -> None:
        for name, data in files.items():
            target = self.destination / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)

    def installed(self) -> dict[str, bytes]:
        return {p.relative_to(self.destination).as_posix(): p.read_bytes()
                for p in self.destination.rglob("*") if p.is_file()}

    def receipt(self) -> bytes:
        return (self.runtime / "state.json").read_bytes()

    def update(self, incoming: dict[str, bytes], **kwargs) -> dict:
        with patch.object(updater, "fetch_head", return_value=NEW), \
                patch.object(updater, "check_ancestry") as ancestry, \
                patch.object(updater, "download_package", return_value=incoming):
            result = updater.sync(self.runtime, self.destination, apply=True, **kwargs)
        ancestry.assert_called_once_with(OLD, NEW)
        return result

    def test_new_modes_and_resources_install_without_updater_inventory_changes(self) -> None:
        incoming = package("animate", "future-mode")
        asset = b"\x00\xffnew binary asset"
        incoming["references/future-mode/assets/example.bin"] = asset
        manifest = json.loads(incoming["references/sources.json"])
        manifest["files"]["future-mode/assets/example.bin"] = {"sha256": hashlib.sha256(asset).hexdigest()}
        incoming["references/sources.json"] = json.dumps(manifest).encode()
        result = self.update(incoming)
        self.assertEqual(result["status"], "updated")
        self.assertEqual(result["modes"], ["animate", "future-mode"])
        self.assertEqual(self.installed(), incoming)
        self.assertEqual(json.loads(self.receipt())["commit"], NEW)
        backup = Path(result["backup"])
        self.assertEqual((backup / "design/SKILL.md").read_bytes(), self.old_package["SKILL.md"])
        self.assertEqual((self.root / "config.toml").read_bytes(), b"model = 'preserved'\n")
        self.assertEqual((self.root / "skills/other/SKILL.md").read_bytes(), b"other skill\n")

    def test_repeat_is_unchanged_and_does_not_download_or_write_receipt(self) -> None:
        before = self.receipt()
        with patch.object(updater, "fetch_head", return_value=OLD), patch.object(updater, "download_package") as fetch:
            result = updater.sync(self.runtime, self.destination, apply=True)
        self.assertEqual(result["status"], "unchanged")
        fetch.assert_not_called()
        self.assertEqual(self.receipt(), before)
        self.assertFalse((self.runtime / "backups").exists())

    def test_docs_only_commit_advances_receipt_without_replacing_package(self) -> None:
        result = self.update(self.old_package)
        self.assertEqual(result["status"], "unchanged")
        self.assertEqual(json.loads(self.receipt())["commit"], NEW)
        self.assertFalse((self.runtime / "backups").exists())

    def test_local_edit_and_unowned_file_prevent_network_or_replacement(self) -> None:
        for name in ("SKILL.md", "notes.md"):
            with self.subTest(name=name):
                self.write_package({name: b"local content"})
                before = self.installed()
                receipt = self.receipt()
                with patch.object(updater, "fetch_head") as fetch, self.assertRaisesRegex(updater.SyncError, "Local design"):
                    updater.sync(self.runtime, self.destination, apply=True)
                fetch.assert_not_called()
                self.assertEqual(self.installed(), before)
                self.assertEqual(self.receipt(), receipt)
                (self.destination / name).unlink()
                self.write_package(self.old_package)

    def test_download_failure_keeps_package_and_receipt(self) -> None:
        before = self.receipt()
        with patch.object(updater, "fetch_head", return_value=NEW), patch.object(updater, "check_ancestry"), \
                patch.object(updater, "download_package", side_effect=OSError("network down")):
            with self.assertRaisesRegex(OSError, "network down"):
                updater.sync(self.runtime, self.destination, apply=True)
        self.assertEqual(self.installed(), self.old_package)
        self.assertEqual(self.receipt(), before)

    def test_invalid_manifest_and_missing_route_leave_installed_version(self) -> None:
        cases = []
        invalid_hash = package("future-mode")
        invalid_hash["references/future-mode/guide.md"] = b"unexpected bytes"
        cases.append(invalid_hash)
        invalid_route = package("future-mode")
        invalid_route["SKILL.md"] = self.old_package["SKILL.md"]
        cases.append(invalid_route)
        for incoming in cases:
            with self.subTest(incoming=incoming["SKILL.md"]), self.assertRaises(updater.SyncError):
                self.update(incoming)
            self.assertEqual(self.installed(), self.old_package)
            self.assertEqual(json.loads(self.receipt())["commit"], OLD)

    def test_edit_during_download_is_preserved(self) -> None:
        def concurrent_edit(commit):
            self.write_package({"SKILL.md": b"concurrent user edit"})
            return package("animate", "future-mode")
        before = self.receipt()
        with patch.object(updater, "fetch_head", return_value=NEW), patch.object(updater, "check_ancestry"), \
                patch.object(updater, "download_package", side_effect=concurrent_edit):
            with self.assertRaisesRegex(updater.SyncError, "changed during download"):
                updater.sync(self.runtime, self.destination, apply=True)
        self.assertEqual((self.destination / "SKILL.md").read_bytes(), b"concurrent user edit")
        self.assertEqual(self.receipt(), before)

    def test_state_write_failure_rolls_back_and_retains_recovery_copy(self) -> None:
        before = self.receipt()
        with patch.object(updater, "atomic_json", side_effect=OSError("state write failed")):
            with self.assertRaisesRegex(OSError, "state write failed"):
                self.update(package("animate", "future-mode"))
        self.assertEqual(self.installed(), self.old_package)
        self.assertEqual(self.receipt(), before)
        self.assertEqual(len(list((self.runtime / "backups").glob("*/failed-design/SKILL.md"))), 1)

    def test_permissions_failure_rolls_back_package_and_receipt(self) -> None:
        before = self.receipt()
        with patch.object(updater, "restore_security", side_effect=updater.SyncError("permissions failed")):
            with self.assertRaisesRegex(updater.SyncError, "permissions failed"):
                self.update(package("animate", "future-mode"))
        self.assertEqual(self.installed(), self.old_package)
        self.assertEqual(self.receipt(), before)
        self.assertEqual(len(list((self.runtime / "backups").glob("*/failed-design/SKILL.md"))), 1)

    def test_update_preserves_existing_permission_entries(self) -> None:
        before = updater.security_snapshot(self.destination)
        self.update(package("animate", "future-mode"))
        after = updater.security_snapshot(self.destination)
        if before is not None:
            for name in before.keys() & after.keys():
                old_owner, _, old_dacl = before[name][0].partition("D:")
                new_owner, _, new_dacl = after[name][0].partition("D:")
                old_flags, _, old_entries = old_dacl.partition("(")
                new_flags, _, new_entries = new_dacl.partition("(")
                self.assertEqual((old_owner, old_flags.replace("AI", ""), old_entries, before[name][1]),
                                 (new_owner, new_flags.replace("AI", ""), new_entries, after[name][1]), name)

    def test_check_only_does_not_replace_package(self) -> None:
        before = self.receipt()
        with patch.object(updater, "fetch_head", return_value=NEW), patch.object(updater, "check_ancestry"), \
                patch.object(updater, "download_package", return_value=package("future-mode")):
            result = updater.sync(self.runtime, self.destination)
        self.assertEqual(result["status"], "available")
        self.assertEqual(self.installed(), self.old_package)
        self.assertEqual(self.receipt(), before)

    def test_enrollment_refuses_overwrite_or_mismatched_installed_bytes(self) -> None:
        before = self.receipt()
        with self.assertRaisesRegex(updater.SyncError, "already enrolled"):
            updater.sync(self.runtime, self.destination, enroll=NEW)
        self.assertEqual(self.receipt(), before)
        (self.runtime / "state.json").unlink()
        with patch.object(updater, "download_package", return_value=package("future-mode")):
            with self.assertRaisesRegex(updater.SyncError, "differs from the enrollment"):
                updater.sync(self.runtime, self.destination, enroll=NEW)
        self.assertFalse((self.runtime / "state.json").exists())
        self.assertEqual(self.installed(), self.old_package)

    def test_rewritten_source_history_is_rejected(self) -> None:
        with patch.object(updater, "request", return_value=b'{"status":"diverged","behind_by":1}'):
            with self.assertRaisesRegex(updater.SyncError, "history was rewritten"):
                updater.check_ancestry(OLD, NEW)

    def test_archive_rejects_escapes_links_duplicates_and_child_entrypoints(self) -> None:
        prefix = "skills-" + NEW + "/skills/design/"
        for unsafe in ("../escape.md", "assets/CON.txt", "assets/bad:name", "references/mode/SKILL.md", "skill.md"):
            with self.subTest(path=unsafe):
                data = io.BytesIO()
                with zipfile.ZipFile(data, "w") as archive:
                    for name, body in package("animate").items():
                        archive.writestr(prefix + name, body)
                    archive.writestr(prefix + unsafe, b"unsafe")
                with self.assertRaises(updater.SyncError):
                    updater.extract_package(data.getvalue(), NEW)
        data = io.BytesIO()
        with zipfile.ZipFile(data, "w") as archive:
            link = zipfile.ZipInfo(prefix + "link")
            link.external_attr = 0o120777 << 16
            archive.writestr(link, b"../../elsewhere")
        with self.assertRaisesRegex(updater.SyncError, "Nonregular"):
            updater.extract_package(data.getvalue(), NEW)

    def test_current_published_package_manifest_is_valid(self) -> None:
        source = ROOT / "skills/design"
        current = {p.relative_to(source).as_posix(): p.read_bytes()
                   for p in source.rglob("*") if p.is_file()}
        self.assertIn("animation-performance", updater.validate_package(current))


if __name__ == "__main__":
    unittest.main()
