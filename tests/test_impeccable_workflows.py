"""Execute the drafted workflow shell against offline, disposable Git fixtures.

Fork coverage uses IMPECCABLE_FORK_WORKFLOW or the canonical sibling checkout.
It is explicitly skipped when that workflow is unavailable (e.g. skills-only CI).
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUNDLE = ROOT / ".github/workflows/sync-impeccable.yml"
FORK = Path(os.environ.get("IMPECCABLE_FORK_WORKFLOW", str(
    ROOT.parent / "impeccable/.github/workflows/sync-personal-fork.yml")))
BASH = (str(Path(shutil.which("git") or "").parent.parent / "bin/bash.exe")
        if os.name == "nt" else shutil.which("bash"))
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def block(path: Path, key: str) -> str:
    """Read one literal YAML block without adding a test dependency on PyYAML."""
    lines = path.read_text(encoding="utf-8").splitlines()
    index = next(i for i, line in enumerate(lines) if line.strip() == key + ": |")
    indent = len(lines[index]) - len(lines[index].lstrip()) + 2
    output = []
    for line in lines[index + 1:]:
        if line.strip() and len(line) - len(line.lstrip()) < indent:
            break
        output.append(line[indent:])
    return "\n".join(output).rstrip() + "\n"


def step_run(path: Path, name: str) -> str:
    text = path.read_text(encoding="utf-8")
    step = text.split("- name: " + name + "\n", 1)[1].split("\n      - name:", 1)[0]
    literal = re.search(r"^        run: \|\n((?:          .*\n|\n)*)", step, re.M)
    if literal is None:
        raise AssertionError(f"Missing literal run block: {name}")
    return "\n".join(line[10:] for line in literal[1].splitlines()) + "\n"


class WorkflowFixtures(unittest.TestCase):
    def setUp(self) -> None:
        # Synthetic test repositories stay within the authorized test-artifact scope.
        self.temp = tempfile.TemporaryDirectory(prefix="workflow-fixture-", dir=ROOT / "tests")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.env = os.environ.copy()
        for key in list(self.env):
            if key.startswith(("GIT_", "GITHUB_")) or key in {"GH_TOKEN", "GH_ENTERPRISE_TOKEN"}:
                self.env.pop(key)
        self.env.update(GIT_CONFIG_GLOBAL=str(self.root / "gitconfig"),
                        GIT_CONFIG_NOSYSTEM="1", GIT_TERMINAL_PROMPT="0",
                        GIT_AUTHOR_NAME="Workflow test", GIT_COMMITTER_NAME="Workflow test",
                        GIT_AUTHOR_EMAIL="test@example.invalid", GIT_COMMITTER_EMAIL="test@example.invalid",
                        GITHUB_OUTPUT=str(self.root / "output"), GIT_ALLOW_PROTOCOL="file")
        self.source = self.root / "source"
        self.git(self.root, "init", "-b", "main", str(self.source))
        self.write(self.source, "README.md", "base\n")
        self.write(self.source, ".github/workflows/inherited.yml", "name: Existing\n")
        self.commit(self.source)

    def run_command(self, argv, cwd=None, check=True, **kwargs):
        result = subprocess.run(argv, cwd=cwd or self.root, env=self.env,
                                capture_output=True, text=True, encoding="utf-8",
                                creationflags=NO_WINDOW, **kwargs)
        if check and result.returncode:
            self.fail(result.stdout + result.stderr)
        return result

    def git(self, repo, *args, check=True):
        return self.run_command(["git", "-C", str(repo), *args], check=check)

    def write(self, repo, path, text):
        target = repo / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(text.encode("utf-8"))

    def commit(self, repo):
        self.git(repo, "add", "-A")
        self.git(repo, "commit", "-m", "fixture")
        return self.head(repo)

    def head(self, repo):
        return self.git(repo, "rev-parse", "HEAD").stdout.strip()

    def shell(self, script, cwd, check=True):
        if not BASH or not Path(BASH).is_file():
            self.skipTest("Native Git Bash/bash is required for workflow shell validation")
        return self.run_command([BASH, "--noprofile", "--norc", "-e", "-o", "pipefail", "-c", script],
                                cwd=cwd, check=check)


class SparseCheckoutTests(WorkflowFixtures):
    def test_noncone_patterns_materialize_complete_skill_and_root_attribution(self):
        expected = {".gitattributes", ".agents/skills/impeccable/SKILL.md",
                    ".agents/skills/impeccable/reference/deep/nested.md",
                    ".agents/skills/impeccable/scripts/impeccable.cmd",
                    ".agents/skills/impeccable/agents/openai.yaml", "LICENSE", "NOTICE.md"}
        for path in expected | {"other/LICENSE", "other/NOTICE.md", ".agents/skills/other/SKILL.md"}:
            self.write(self.source, path, path + "\n")
        self.write(self.source, ".gitattributes", "*.cmd text eol=crlf\n")
        self.commit(self.source)
        checkout = self.root / "sparse"
        self.git(self.root, "clone", "--no-checkout", "--depth=1", self.source.as_uri(), str(checkout))
        patterns = block(BUNDLE, "sparse-checkout")
        self.run_command(["git", "-C", str(checkout), "sparse-checkout", "set", "--no-cone", "--stdin"], input=patterns)
        self.git(checkout, "checkout", "main")
        actual = {p.relative_to(checkout).as_posix() for p in checkout.rglob("*")
                  if p.is_file() and ".git" not in p.relative_to(checkout).parts}
        self.assertEqual(actual, expected)
        self.assertIn(b"\r\n", (checkout / ".agents/skills/impeccable/scripts/impeccable.cmd").read_bytes())
        self.assertNotIn(b"\r\n", (checkout / ".agents/skills/impeccable/SKILL.md").read_bytes())
        self.assertEqual(self.git(checkout, "rev-parse", "--is-shallow-repository").stdout.strip(), "true")


@unittest.skipUnless(FORK.is_file(), "Personal fork workflow unavailable; set IMPECCABLE_FORK_WORKFLOW")
class ForkMergeTests(WorkflowFixtures):
    def setUp(self):
        super().setUp()
        self.remote = self.root / "remote.git"
        self.fork = self.root / "fork"
        self.git(self.root, "clone", "--bare", str(self.source), str(self.remote))
        self.git(self.root, "clone", str(self.remote), str(self.fork))
        self.write(self.fork, ".github/workflows/sync-personal-fork.yml", FORK.read_text(encoding="utf-8"))
        self.initial = self.commit(self.fork)
        self.git(self.fork, "push", "origin", "main")
        self.git(self.fork, "config", "--global", f"url.{self.source.as_uri()}.insteadOf",
                 "https://github.com/pbakaus/impeccable.git")
        self.script = step_run(FORK, "Merge upstream without rewriting fork history")

    def sync(self, check=True):
        (self.root / "output").write_text("", encoding="utf-8")
        return self.shell(self.script, self.fork, check=check)

    def test_merge_preserves_fork_history_and_repeat_is_noop(self):
        self.write(self.source, "reference/new.md", "upstream\n")
        upstream = self.commit(self.source)
        self.sync()
        merged = self.head(self.fork)
        self.assertEqual(self.git(self.fork, "show", "-s", "--format=%P").stdout.split(), [self.initial, upstream])
        self.assertEqual((self.fork / ".github/workflows/sync-personal-fork.yml").read_text(), FORK.read_text())
        self.assertIn("changed=true", (self.root / "output").read_text())
        self.sync()
        self.assertEqual(merged, self.head(self.fork))
        self.assertIn("changed=false", (self.root / "output").read_text())

    def test_fast_forward_preserves_existing_history(self):
        self.git(self.fork, "reset", "--hard", "HEAD^")
        self.write(self.source, "reference/new.md", "upstream\n")
        upstream = self.commit(self.source)
        self.sync()
        self.assertEqual(self.head(self.fork), upstream)

    def test_workflow_add_edit_delete_and_rename_stop_before_merge(self):
        base = self.head(self.source)
        for operation in ("add", "edit", "delete", "rename"):
            with self.subTest(operation=operation):
                self.git(self.source, "reset", "--hard", base)
                if operation == "add":
                    self.write(self.source, ".github/workflows/new.yml", "name: New\n")
                elif operation == "edit":
                    self.write(self.source, ".github/workflows/inherited.yml", "name: Changed\n")
                elif operation == "delete":
                    self.git(self.source, "rm", ".github/workflows/inherited.yml")
                else:
                    self.git(self.source, "mv", ".github/workflows/inherited.yml", "moved.yml")
                self.commit(self.source)
                result = self.sync(check=False)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("workflow changes need review", result.stderr)
                self.assertEqual(self.head(self.fork), self.initial)
                self.assertEqual(self.head(self.remote), self.initial)
                self.assertEqual(self.git(self.fork, "status", "--porcelain").stdout, "")

    def test_conflict_aborts_without_publishing(self):
        self.write(self.fork, "README.md", "fork\n")
        before = self.commit(self.fork)
        self.write(self.source, "README.md", "upstream\n")
        self.commit(self.source)
        self.assertNotEqual(self.sync(check=False).returncode, 0)
        self.assertEqual(self.head(self.fork), before)
        self.assertEqual(self.head(self.remote), self.initial)
        self.assertEqual(self.git(self.fork, "status", "--porcelain").stdout, "")
        self.assertNotEqual(self.git(self.fork, "rev-parse", "--verify", "MERGE_HEAD", check=False).returncode, 0)

    def test_normal_push_rejects_concurrent_change(self):
        self.write(self.source, "reference/new.md", "upstream\n")
        self.commit(self.source)
        self.sync()
        concurrent = self.root / "concurrent"
        self.git(self.root, "clone", str(self.remote), str(concurrent))
        self.write(concurrent, "concurrent.md", "concurrent\n")
        latest = self.commit(concurrent)
        self.git(concurrent, "push", "origin", "main")
        publish = step_run(FORK, "Publish the merge")
        # Only authentication is stubbed: the workflow's real push targets a local bare remote.
        result = self.shell("gh() { return 0; }\n" + publish, self.fork, check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.head(self.remote), latest)


class BundleWorkflowTests(WorkflowFixtures):
    def test_ancestry_gate_accepts_only_forward_or_identical_and_fails_on_api_error(self):
        self.git(self.root, "clone", str(self.source), str(self.source / "impeccable-source"))
        self.write(self.source, "skills/impeccable/upstream/source.json", '{"commit": "' + self.head(self.source) + '"}')
        script = step_run(BUNDLE, "Check source ancestry")
        for status, code, accepted in (("ahead:0", 0, True), ("identical:0", 0, True),
                                       ("behind:1", 0, False), ("diverged:1", 0, False),
                                       ("ahead:1", 0, False), ("", 1, False)):
            with self.subTest(status=status, code=code):
                self.env["TEST_COMPARISON"] = status
                self.env["TEST_API_EXIT"] = str(code)
                result = self.shell('gh() { printf "%s" "$TEST_COMPARISON"; return "$TEST_API_EXIT"; }\n' + script,
                                    self.source, check=False)
                self.assertEqual(result.returncode == 0, accepted)

    def test_prepare_commits_only_snapshot_and_repeat_is_noop(self):
        paths = ("skills/impeccable/upstream/source.json", "skills/design/references/impeccable/guide.md",
                 "skills/design/references/sources.json", "skills/design/references/animate/guide.md")
        for path in paths:
            self.write(self.source, path, "initial\n")
        self.commit(self.source)
        script = step_run(BUNDLE, "Prepare the verified snapshot")
        self.shell(script, self.source)
        self.assertIn("changed=false", (self.root / "output").read_text())
        for path in paths:
            self.write(self.source, path, "updated\n")
        self.write(self.source, "unrelated.md", "preserve\n")
        self.shell(script, self.source)
        self.assertIn("changed=true", (self.root / "output").read_text())
        self.assertEqual(set(self.git(self.source, "diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD").stdout.splitlines()), set(paths))
        self.assertEqual(self.git(self.source, "status", "--porcelain").stdout, "?? unrelated.md\n")
        current = self.head(self.source)
        (self.root / "output").write_text("")
        self.shell(script, self.source)
        self.assertEqual(self.head(self.source), current)
        self.assertIn("changed=false", (self.root / "output").read_text())


class WorkflowPolicyTests(unittest.TestCase):
    def test_credentials_permissions_and_publication_boundaries(self):
        for path in (BUNDLE, FORK):
            if not path.is_file():
                continue
            with self.subTest(path=path.name):
                text = path.read_text(encoding="utf-8")
                self.assertIn("permissions: {}", text)
                self.assertIn("github.ref == 'refs/heads/main'", text)
                self.assertNotRegex(text, r"secrets\.|--force|git push[^\n]*\+|set -[^\n]*x|pull_request_target:")
                self.assertEqual(text.count("uses: actions/checkout@"), text.count("persist-credentials: false"))
                self.assertIn("git push origin HEAD:refs/heads/main", text)
                self.assertRegex(text, r"if: steps\.\w+\.outputs\.changed == 'true'")
        self.assertIn("group: sync-upstream-main", BUNDLE.read_text())
        self.assertIn("group: sync-upstream-main", (ROOT / ".github/workflows/sync-upstream.yml").read_text())
        for step in BUNDLE.read_text().split("      - name: ")[1:]:
            if "GH_TOKEN:" in step:
                self.assertIn(step.splitlines()[0], {"Check source ancestry", "Publish the verified snapshot"})


if __name__ == "__main__":
    unittest.main()
