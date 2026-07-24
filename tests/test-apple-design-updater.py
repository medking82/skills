#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
UPDATER = REPO_ROOT / "scripts" / "sync-apple-design.py"
TIMER_INSTALLER = REPO_ROOT / "scripts" / "install-apple-design-update-timer.sh"
SCOPE_NAMES = ("WslCodex", "WslClaude", "WindowsCodex", "WindowsClaude")


def tree_digest(root: Path) -> str:
    entries = []
    for file_path in sorted(path for path in root.rglob("*") if path.is_file()):
        data = file_path.read_bytes()
        entries.append(
            {
                "path": file_path.relative_to(root).as_posix(),
                "length": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
            }
        )
    payload: object = entries[0] if len(entries) == 1 else entries
    manifest = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(manifest.encode("utf-8")).hexdigest()


class AppleDesignUpdaterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(
            prefix="apple-design-updater-test-"
        )
        self.root = Path(self.temporary.name)
        self.source = self.root / "source"
        self.scopes_parent = self.root / "scopes"
        self.scopes_parent.mkdir()
        self.scope_roots = {
            name: self.scopes_parent / name for name in SCOPE_NAMES
        }
        self.lock_file = self.root / "update.lock"
        self.write_skill("one", with_reference=True)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def write_skill(
        self,
        version: str,
        *,
        valid: bool = True,
        with_reference: bool = False,
    ) -> None:
        shutil.rmtree(self.source, ignore_errors=True)
        self.source.mkdir()
        name = "apple-design" if valid else "wrong-name"
        (self.source / "SKILL.md").write_text(
            f"---\nname: {name}\ndescription: test fixture\n---\n\n"
            f"# Apple Design\n\nversion: {version}\n",
            encoding="utf-8",
        )
        if with_reference:
            references = self.source / "references"
            references.mkdir()
            (references / "motion.md").write_text(
                f"# Motion\n\nversion: {version}\n", encoding="utf-8"
            )

    def invoke(
        self,
        mode: str,
        *,
        expected: str | None = None,
        fail_after_swaps: int | None = None,
        custom_scopes: bool = True,
        extra_args: list[str] | None = None,
        env: dict[str, str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        args = [
            sys.executable,
            str(UPDATER),
            "--mode",
            mode,
            "--test-source-path",
            str(self.source),
            "--test-lock-file",
            str(self.lock_file),
        ]
        if custom_scopes:
            for name, root in self.scope_roots.items():
                args.extend(["--test-scope", f"{name}={root}"])
        if expected is not None:
            args.extend(["--expected-source-sha256", expected])
        if fail_after_swaps is not None:
            args.extend(["--test-fail-after-swaps", str(fail_after_swaps)])
        if extra_args:
            args.extend(extra_args)
        return subprocess.run(
            args,
            text=True,
            capture_output=True,
            check=False,
            env=env,
        )

    @staticmethod
    def reported_digest(result: subprocess.CompletedProcess[str]) -> str:
        match = re.search(r"source_sha256=([0-9a-f]{64})", result.stdout)
        if not match:
            raise AssertionError(
                f"missing source digest\nstdout={result.stdout}\nstderr={result.stderr}"
            )
        return match.group(1)

    def assert_no_scope_roots(self) -> None:
        self.assertTrue(all(not root.exists() for root in self.scope_roots.values()))

    def assert_all_scope_digests(self, expected: str) -> None:
        for root in self.scope_roots.values():
            self.assertEqual(expected, tree_digest(root / "apple-design"))

    def test_check_is_zero_write_and_manifest_matches_powershell_shape(self) -> None:
        result = self.invoke("Check")
        self.assertEqual(3, result.returncode, result.stderr)
        self.assert_no_scope_roots()
        self.assertEqual(tree_digest(self.source), self.reported_digest(result))
        for name in SCOPE_NAMES:
            self.assertIn(f"scope={name} status=missing", result.stdout)

    def test_apply_requires_matching_digest_before_destination_writes(self) -> None:
        result = self.invoke("Apply")
        self.assertEqual(1, result.returncode)
        self.assertIn("requires --expected-source-sha256", result.stderr)
        self.assert_no_scope_roots()

        result = self.invoke("Apply", expected="0" * 64)
        self.assertEqual(1, result.returncode)
        self.assertIn("does not match canonical manifest", result.stderr)
        self.assert_no_scope_roots()

    def test_apply_installs_four_independent_snapshots_and_is_idempotent(self) -> None:
        check = self.invoke("Check")
        digest = self.reported_digest(check)
        result = self.invoke("Apply", expected=digest)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assert_all_scope_digests(digest)
        for name in SCOPE_NAMES:
            self.assertIn(f"scope={name} status=applied", result.stdout)

        result = self.invoke("Apply", expected=digest)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertNotIn("status=applied", result.stdout)
        self.assertEqual(0, self.invoke("Check").returncode)

    def test_check_detects_drift_and_explicit_apply_repairs_it(self) -> None:
        digest = self.reported_digest(self.invoke("Check"))
        self.assertEqual(0, self.invoke("Apply", expected=digest).returncode)
        target = self.scope_roots["WslCodex"] / "apple-design" / "SKILL.md"
        target.write_text(target.read_text(encoding="utf-8") + "\nlocal edit\n")

        result = self.invoke("Check")
        self.assertEqual(3, result.returncode)
        self.assertIn("scope=WslCodex status=drifted", result.stdout)
        self.assertIn("scope=WslClaude status=current", result.stdout)
        self.assertEqual(0, self.invoke("Apply", expected=digest).returncode)
        self.assert_all_scope_digests(digest)

    def test_invalid_source_and_symlink_fail_closed(self) -> None:
        digest = self.reported_digest(self.invoke("Check"))
        self.assertEqual(0, self.invoke("Apply", expected=digest).returncode)
        stable = {
            name: tree_digest(root / "apple-design")
            for name, root in self.scope_roots.items()
        }

        self.write_skill("invalid", valid=False)
        result = self.invoke("Apply", expected=digest)
        self.assertEqual(1, result.returncode)
        self.assertIn("must declare name: apple-design", result.stderr)
        for name, root in self.scope_roots.items():
            self.assertEqual(stable[name], tree_digest(root / "apple-design"))

        self.write_skill("linked")
        os.symlink("SKILL.md", self.source / "linked-skill.md")
        result = self.invoke("Check")
        self.assertEqual(1, result.returncode)
        self.assertIn("Symlinks are not allowed", result.stderr)

    def test_failure_after_two_swaps_restores_all_prior_snapshots(self) -> None:
        original_digest = self.reported_digest(self.invoke("Check"))
        self.assertEqual(
            0, self.invoke("Apply", expected=original_digest).returncode
        )
        self.write_skill("two", with_reference=True)
        replacement_digest = self.reported_digest(self.invoke("Check"))

        result = self.invoke(
            "Apply", expected=replacement_digest, fail_after_swaps=2
        )
        self.assertEqual(1, result.returncode)
        self.assertIn("Injected failure after 2 scope swap", result.stderr)
        self.assert_all_scope_digests(original_digest)
        leftovers = [
            path
            for root in self.scope_roots.values()
            for path in root.glob(".apple-design.*")
        ]
        self.assertEqual([], leftovers)

    def test_missing_windows_profile_fails_before_wsl_destination_writes(self) -> None:
        if (
            not sys.platform.startswith("linux")
            or "microsoft"
            not in Path("/proc/sys/kernel/osrelease").read_text(encoding="utf-8").lower()
            or not Path("/mnt/c").is_mount()
        ):
            self.skipTest("requires a real WSL Windows mount at /mnt/c")
        fake_home = self.root / "fake-home"
        (fake_home / ".agents").mkdir(parents=True)
        (fake_home / ".claude").mkdir()
        env = os.environ.copy()
        env["HOME"] = str(fake_home)
        result = self.invoke(
            "Check",
            custom_scopes=False,
            extra_args=[
                "--test-windows-profile",
                str(self.root / "missing-windows-profile"),
            ],
            env=env,
        )
        self.assertEqual(1, result.returncode)
        self.assertIn("Windows profile is missing", result.stderr)
        self.assertFalse((fake_home / ".agents" / "skills").exists())
        self.assertFalse((fake_home / ".claude" / "skills").exists())

    def test_timer_installer_is_preview_first_and_check_only(self) -> None:
        fake_home = self.root / "timer-home"
        config_root = self.root / "timer-config"
        fake_home.mkdir()
        env = os.environ.copy()
        env.update({"HOME": str(fake_home), "XDG_CONFIG_HOME": str(config_root)})
        result = subprocess.run(
            ["bash", str(TIMER_INSTALLER)],
            text=True,
            capture_output=True,
            check=False,
            env=env,
        )
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("mode=Check", result.stdout)
        self.assertIn("apply=never-scheduled", result.stdout)
        self.assertIn("status=preview-only", result.stdout)
        self.assertFalse(config_root.exists())

        installer = TIMER_INSTALLER.read_text(encoding="utf-8")
        self.assertIn("--mode Check", installer)
        self.assertIn("SuccessExitStatus=3", installer)
        self.assertIn("WorkingDirectory=$escaped_repo", installer)
        self.assertNotIn('WorkingDirectory="$escaped_repo"', installer)
        self.assertNotIn("--mode Apply", installer)


if __name__ == "__main__":
    unittest.main(verbosity=2)
