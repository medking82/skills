from __future__ import annotations

import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("design_bundle", REPO_ROOT / "scripts/build-design-skill.py")
assert SPEC is not None and SPEC.loader is not None
bundle = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(bundle)


class DesignBundleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="design-bundle-", dir=REPO_ROOT / "tests")
        self.addCleanup(self.temporary.cleanup)
        self.repo = Path(self.temporary.name)
        self.root = self.repo / "skills/design/references"
        self.write("skills/design/SKILL.md", "# Design\n" + "\n".join(
            f"[{mode}](references/{mode}/guide.md)" for mode in bundle.MODES
        ))
        for mode in bundle.MODES:
            self.write(f"skills/{mode}/SKILL.md", (
                f"---\nname: {mode}\ndescription: Test mode\n---\n\n"
                "# Mode\n\nRead [detail](references/detail.md).\n"
            ))
            self.write(f"skills/{mode}/references/detail.md", "# Detail\n\nRead [asset](../assets/data.bin).\n")
            self.write(f"skills/{mode}/assets/data.bin", b"\x00\xff\r\nasset")
            self.write(f"skills/{mode}/agents/openai.yaml", "policy:\n  allow_implicit_invocation: false\n")
            self.write(f"skills/{mode}/examples/nested/SKILL.md", "not a discovery entrypoint\n")

    def write(self, relative: str, content: str | bytes) -> None:
        target = self.repo / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content.encode("utf-8") if isinstance(content, str) else content)

    def snapshot(self) -> dict[str, bytes]:
        return {p.relative_to(self.repo).as_posix(): p.read_bytes()
                for p in self.repo.rglob("*") if p.is_file()}

    def test_all_modes_preserve_body_binary_assets_and_relative_resources(self) -> None:
        self.assertTrue(bundle.build(self.repo))
        manifest = json.loads((self.root / "sources.json").read_text())
        self.assertEqual(set(manifest["modes"]), set(bundle.MODES))
        self.assertEqual(len(manifest["modes"]), 13)
        for mode in bundle.MODES:
            source = self.repo / "skills" / mode
            destination = self.root / mode
            self.assertEqual((destination / "guide.md").read_bytes(),
                             bundle.without_frontmatter((source / "SKILL.md").read_bytes(), source / "SKILL.md"))
            self.assertEqual((destination / "assets/data.bin").read_bytes(), b"\x00\xff\r\nasset")
            self.assertEqual((destination / "references/detail.md").read_bytes(),
                             (source / "references/detail.md").read_bytes())
            self.assertTrue((destination / "references/detail.md").is_file())
            self.assertTrue((destination / "references/../assets/data.bin").is_file())
            self.assertEqual(manifest["modes"][mode]["source_sha256"],
                             bundle.digest((source / "SKILL.md").read_bytes()))
        self.assertEqual(list(self.root.rglob("SKILL.md")), [])
        self.assertEqual(list(self.root.rglob("openai.yaml")), [])
        before = self.snapshot()
        self.assertTrue(bundle.build(self.repo, check=True))
        self.assertTrue(bundle.build(self.repo))
        self.assertEqual(self.snapshot(), before)

    def test_stale_source_check_has_no_mutations_and_build_refreshes(self) -> None:
        bundle.build(self.repo)
        self.write("skills/animate/references/detail.md", "New detail\n")
        before = self.snapshot()
        self.assertFalse(bundle.build(self.repo, check=True))
        self.assertEqual(self.snapshot(), before)
        bundle.build(self.repo)
        self.assertEqual((self.root / "animate/references/detail.md").read_text(), "New detail\n")
        self.assertTrue(bundle.build(self.repo, check=True))

    def test_missing_bundle_check_does_not_create_destination(self) -> None:
        before = self.snapshot()
        self.assertFalse(bundle.build(self.repo, check=True))
        self.assertFalse(self.root.exists())
        self.assertEqual(self.snapshot(), before)

    def test_only_previous_manifest_owned_obsolete_files_are_removed(self) -> None:
        bundle.build(self.repo)
        self.write("skills/design/references/animate/notes.md", "Keep my notes\n")
        (self.repo / "skills/animate/assets/data.bin").unlink()
        self.assertFalse(bundle.build(self.repo, check=True))
        bundle.build(self.repo)
        self.assertFalse((self.root / "animate/assets/data.bin").exists())
        self.assertEqual((self.root / "animate/notes.md").read_text(), "Keep my notes\n")

    def test_unowned_collision_fails_before_any_write(self) -> None:
        self.write("skills/design/references/write-swift/guide.md", "User guide\n")
        before = self.snapshot()
        with self.assertRaisesRegex(bundle.BundleError, "Unowned destination"):
            bundle.build(self.repo)
        self.assertEqual(self.snapshot(), before)

    def test_generated_local_edits_fail_before_other_stale_files_are_updated(self) -> None:
        bundle.build(self.repo)
        self.write("skills/animate/references/detail.md", "New source\n")
        self.write("skills/design/references/write-swift/guide.md", "Local override\n")
        before = self.snapshot()
        with self.assertRaisesRegex(bundle.BundleError, "local edits"):
            bundle.build(self.repo)
        self.assertEqual(self.snapshot(), before)

    def test_manifest_path_escape_fails_without_mutation(self) -> None:
        bundle.build(self.repo)
        path = self.root / "sources.json"
        manifest = json.loads(path.read_text())
        manifest["files"]["animate/../../escape.md"] = {
            "source": "skills/animate/../../escape.md", "sha256": "0" * 64, "source_sha256": "0" * 64,
        }
        path.write_text(json.dumps(manifest))
        before = self.snapshot()
        with self.assertRaisesRegex(bundle.BundleError, "Unsafe generated path"):
            bundle.build(self.repo)
        self.assertEqual(self.snapshot(), before)

    def test_source_inventory_and_router_must_be_explicitly_updated(self) -> None:
        self.write("skills/new-mode/SKILL.md", "---\nname: new-mode\n---\n# New\n")
        before = self.snapshot()
        with self.assertRaisesRegex(bundle.BundleError, "Mode inventory changed"):
            bundle.build(self.repo)
        self.assertEqual(self.snapshot(), before)
        (self.repo / "skills/new-mode/SKILL.md").unlink()
        self.write("skills/design/SKILL.md", "# No routes\n")
        before = self.snapshot()
        with self.assertRaisesRegex(bundle.BundleError, "router must link"):
            bundle.build(self.repo)
        self.assertEqual(self.snapshot(), before)

    def test_invalid_source_frontmatter_fails_before_mutation(self) -> None:
        self.write("skills/write-swift/SKILL.md", "# Missing frontmatter\n")
        before = self.snapshot()
        with self.assertRaisesRegex(bundle.BundleError, "Missing frontmatter"):
            bundle.build(self.repo)
        self.assertEqual(self.snapshot(), before)

    def test_missing_owned_output_is_detected_and_recreated(self) -> None:
        bundle.build(self.repo)
        path = self.root / "animate/guide.md"
        expected = path.read_bytes()
        path.unlink()
        before = self.snapshot()
        self.assertFalse(bundle.build(self.repo, check=True))
        self.assertEqual(self.snapshot(), before)
        bundle.build(self.repo)
        self.assertEqual(path.read_bytes(), expected)

    def test_case_insensitive_generated_collision_is_rejected(self) -> None:
        self.write("skills/animate/Guide.md", "Conflicts with generated guide\n")
        before = self.snapshot()
        with self.assertRaisesRegex(bundle.BundleError, "case-insensitive"):
            bundle.build(self.repo)
        self.assertEqual(self.snapshot(), before)

    def git(self, *args: str, autocrlf: str = "false", eol: str = "lf") -> None:
        result = subprocess.run(
            ["git", "-C", str(self.repo), "-c", f"core.autocrlf={autocrlf}",
             "-c", f"core.eol={eol}", "-c", "core.safecrlf=false", *args],
            capture_output=True, text=True, encoding="utf-8", stdin=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_unprotected_git_checkout_reproduces_byte_hash_drift(self) -> None:
        bundle.build(self.repo)
        source = self.repo / "skills/animate/SKILL.md"
        original = source.read_bytes()
        self.git("init")
        self.git("add", "--all")
        # Force materialization from the index rather than reusing up-to-date
        # working files; this models a fresh checkout under the target policy.
        for path in (self.repo / "skills").rglob("*"):
            if path.is_file():
                path.unlink()
        self.git("checkout-index", "--force", "--all", autocrlf="true", eol="crlf")
        self.assertNotEqual(source.read_bytes(), original)
        self.assertIn(b"\r\n", source.read_bytes())
        with self.assertRaisesRegex(bundle.BundleError, "local edits"):
            bundle.build(self.repo, check=True)

    def test_repository_attributes_preserve_bundle_across_checkout_eol_policies(self) -> None:
        self.write(".gitattributes", (REPO_ROOT / ".gitattributes").read_bytes())
        self.write("skills/animate/assets/crlf.txt", b"Text asset\r\nSecond line\r\n")
        bundle.build(self.repo)
        before = {p.relative_to(self.repo).as_posix(): p.read_bytes()
                  for p in (self.repo / "skills").rglob("*") if p.is_file()}
        self.git("init")
        self.git("add", "--all")
        for autocrlf, eol in (("true", "crlf"), ("false", "lf"), ("input", "lf")):
            with self.subTest(autocrlf=autocrlf, eol=eol):
                for relative in before:
                    (self.repo / relative).unlink()
                self.git("checkout-index", "--force", "--all", autocrlf=autocrlf, eol=eol)
                actual = {p.relative_to(self.repo).as_posix(): p.read_bytes()
                          for p in (self.repo / "skills").rglob("*") if p.is_file()}
                self.assertEqual(actual, before, "Git altered source/bundle bytes during checkout")
                self.assertTrue(bundle.build(self.repo, check=True))


if __name__ == "__main__":
    unittest.main()
