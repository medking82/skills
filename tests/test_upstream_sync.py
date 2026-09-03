from __future__ import annotations

import contextlib
import importlib.util
import io
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("sync_upstream", REPO_ROOT / "scripts" / "sync-upstream.py")
assert SPEC is not None and SPEC.loader is not None
sync = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(sync)
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


class UpstreamSyncTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="skills-upstream-sync-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.upstream = self.root / "upstream"
        self.fork = self.root / "fork"
        self.remote = self.root / "fork.git"
        self.git(self.root, "init", "--initial-branch=main", str(self.upstream))
        self.write(self.upstream, "README.md", "# Skills\n")
        self.write(self.upstream, "skills/example/SKILL.md", "---\nname: example\ndescription: Example skill.\n---\n")
        self.write(self.upstream, "tests/test_skill_metadata.py", (REPO_ROOT / "tests" / "test_skill_metadata.py").read_text(encoding="utf-8"))
        self.commit(self.upstream, "base")
        self.git(self.root, "init", "--bare", "--initial-branch=main", str(self.remote))
        self.git(self.root, "clone", str(self.upstream), str(self.fork))
        self.git(self.fork, "remote", "set-url", "origin", str(self.remote))
        self.write(self.fork, "fork-customization.md", "Keep the fork's local customization.\n")
        self.commit(self.fork, "fork customization")
        self.git(self.fork, "push", "--set-upstream", "origin", "main")
        self.initial = self.git(self.fork, "rev-parse", "HEAD").stdout.strip()

    def git(self, repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", "-C", str(repo), "-c", "user.name=Sync test", "-c", "user.email=sync-test@example.invalid", *args],
            capture_output=True, text=True, encoding="utf-8", check=check,
            stdin=subprocess.DEVNULL, creationflags=NO_WINDOW,
        )

    def write(self, repo: Path, path: str, content: str) -> None:
        target = repo / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")

    def commit(self, repo: Path, message: str) -> str:
        self.git(repo, "add", "--all")
        self.git(repo, "commit", "-m", message)
        return self.git(repo, "rev-parse", "HEAD").stdout.strip()

    def prepare(self) -> bool:
        with contextlib.redirect_stdout(io.StringIO()):
            return sync.prepare_sync(self.fork, str(self.upstream))

    def assert_restored(self) -> None:
        self.assertEqual(self.git(self.fork, "rev-parse", "HEAD").stdout.strip(), self.initial)
        self.assertEqual(self.git(self.remote, "rev-parse", "main").stdout.strip(), self.initial)
        self.assertEqual(self.git(self.fork, "status", "--porcelain").stdout, "")
        self.assertNotEqual(self.git(self.fork, "rev-parse", "--verify", "-q", "MERGE_HEAD", check=False).returncode, 0)

    def test_merge_preserves_fork_and_repeated_sync_is_noop(self) -> None:
        self.write(self.upstream, "skills/new-skill/SKILL.md", "---\nname: new-skill\ndescription: New upstream skill.\n---\n")
        upstream_commit = self.commit(self.upstream, "new skill")
        self.assertTrue(self.prepare())
        self.assertEqual((self.fork / "fork-customization.md").read_text(), "Keep the fork's local customization.\n")
        self.assertTrue((self.fork / "skills/new-skill/SKILL.md").exists())
        self.git(self.fork, "merge-base", "--is-ancestor", self.initial, "HEAD")
        self.git(self.fork, "merge-base", "--is-ancestor", upstream_commit, "HEAD")
        self.git(self.fork, "push", "origin", "HEAD:refs/heads/main")
        merged = self.git(self.fork, "rev-parse", "HEAD").stdout.strip()
        self.assertEqual(self.git(self.remote, "rev-parse", "main").stdout.strip(), merged)
        self.assertFalse(self.prepare())
        self.assertEqual(self.git(self.fork, "rev-parse", "HEAD").stdout.strip(), merged)
        self.assertEqual(self.git(self.fork, "status", "--porcelain").stdout, "")

    def test_conflict_restores_fork(self) -> None:
        self.write(self.fork, "README.md", "# Customized skills\n")
        self.initial = self.commit(self.fork, "customize README")
        self.git(self.fork, "push", "origin", "main")
        self.write(self.upstream, "README.md", "# Updated upstream skills\n")
        self.commit(self.upstream, "update README")
        with self.assertRaises(sync.SyncError):
            self.prepare()
        self.assert_restored()
        self.assertEqual((self.fork / "README.md").read_text(), "# Customized skills\n")

    def test_invalid_metadata_restores_fork(self) -> None:
        self.write(self.upstream, "skills/example/SKILL.md", "---\nname: example\ndescription: Example.\ndisable-model-invocation: true\n---\n")
        self.commit(self.upstream, "unsupported metadata")
        with self.assertRaisesRegex(sync.SyncError, "metadata failed validation"):
            self.prepare()
        self.assert_restored()

    def test_upstream_cannot_replace_executed_validation_or_workflow(self) -> None:
        self.write(self.upstream, "tests/test_skill_metadata.py", "from pathlib import Path\nPath('executed.txt').touch()\n")
        self.write(self.upstream, ".github/workflows/new.yml", "name: Unreviewed workflow\n")
        self.commit(self.upstream, "change automation")
        with self.assertRaisesRegex(sync.SyncError, "outside skill content require manual review"):
            self.prepare()
        self.assertFalse((self.fork / "executed.txt").exists())
        self.assert_restored()

    def test_dirty_checkout_is_preserved(self) -> None:
        self.write(self.fork, "notes.txt", "Uncommitted user work.\n")
        with self.assertRaisesRegex(sync.SyncError, "clean checkout"):
            self.prepare()
        self.assertEqual((self.fork / "notes.txt").read_text(), "Uncommitted user work.\n")
        self.assertEqual(self.git(self.fork, "rev-parse", "HEAD").stdout.strip(), self.initial)

    def test_non_main_branch_is_preserved(self) -> None:
        self.git(self.fork, "switch", "--create", "feature")
        with self.assertRaisesRegex(sync.SyncError, "main checkout"):
            self.prepare()
        self.assertEqual(self.git(self.fork, "branch", "--show-current").stdout.strip(), "feature")
        self.assert_restored()

    def test_normal_push_rejects_concurrent_remote_change(self) -> None:
        self.write(self.upstream, "README.md", "# Updated skills\n")
        self.commit(self.upstream, "upstream update")
        self.assertTrue(self.prepare())
        concurrent = self.root / "concurrent"
        self.git(self.root, "clone", str(self.remote), str(concurrent))
        self.write(concurrent, "concurrent.txt", "Another contributor's update.\n")
        remote_commit = self.commit(concurrent, "concurrent update")
        self.git(concurrent, "push", "origin", "main")
        result = self.git(self.fork, "push", "origin", "HEAD:refs/heads/main", check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.git(self.remote, "rev-parse", "main").stdout.strip(), remote_commit)
