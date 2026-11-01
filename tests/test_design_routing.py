"""Verify routing resources and documented bilingual intent boundaries."""

import hashlib
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DESIGN = ROOT / "skills" / "design"


class DesignRoutingTests(unittest.TestCase):
    def setUp(self):
        self.router = (DESIGN / "SKILL.md").read_text(encoding="utf-8")
        self.section = self.router.split("## Impeccable playbook selection\n", 1)[1].split("\n## ", 1)[0]

    def test_playbook_table_resolves_to_owned_manifest_files(self):
        entries = re.findall(r"^\| `([a-z]+)` \| .*? \| \[([a-z]+)\]\(([^)]+)\) \|$", self.section, re.MULTILINE)
        # Every current upstream command is listed and linked directly; `craft` is a deprecated alias.
        commands = json.loads((DESIGN / "references/impeccable/upstream/scripts/command-metadata.json")
                              .read_text(encoding="utf-8"))
        expected = {name: f"references/impeccable/upstream/reference/{name}.md"
                    for name in commands if name != "craft"}
        self.assertEqual(len(entries), len(expected))
        self.assertEqual({name: path for name, label, path in entries if name == label}, expected)
        manifest = json.loads((DESIGN / "references" / "sources.json").read_text(encoding="utf-8"))
        for name, relative in expected.items():
            with self.subTest(playbook=name):
                data = (DESIGN / relative).read_bytes()
                self.assertTrue(data.strip())
                record = manifest["files"][relative.removeprefix("references/")]
                self.assertEqual(hashlib.sha256(data).hexdigest(), record["sha256"])

    def test_bilingual_single_mixed_and_negative_examples_are_documented(self):
        examples = (
            '“调整间距和布局” → `layout`', '“Improve the type scale” → `typeset`',
            '“能帮我调整间距吗？” is an action request → `layout` with implementation',
            '“精简设置页并优化字号” → `distill` + `typeset`',
            '“Review this design, then polish the issues” → `critique` then `polish`',
            '“让配色更有活力” → `colorize`', '“改善新用户引导” → `onboard`',
            '“修复手机页面的触控和布局” may combine `adapt` with `mobile-native`',
            '“不要改字体，只调整间距” selects `layout`, not `typeset`',
            '“Review the animation” uses the explicit motion-review mode',
            'A non-UI backend request does not invoke these playbooks',
        )
        for example in examples:
            with self.subTest(example=example):
                self.assertIn(example, self.section)
        self.assertIn("does not edit", self.section)

    def test_upstream_commands_remain_discoverable_and_have_owned_guides(self):
        upstream = DESIGN / "references/impeccable/upstream"
        commands = json.loads((upstream / "scripts/command-metadata.json").read_text(encoding="utf-8"))
        guide = (upstream / "guide.md").read_text(encoding="utf-8")
        rows = {}
        for line in guide.splitlines():
            match = re.match(r"^\| `([a-z]+)(?: [^`]*)?` \|", line)
            if match:
                rows[match.group(1)] = re.findall(r"\]\((reference/[^)]+\.md)\)", line)
        self.assertEqual(set(commands), set(rows))
        manifest = json.loads((DESIGN / "references/sources.json").read_text(encoding="utf-8"))
        for name, paths in rows.items():
            with self.subTest(command=name):
                self.assertTrue(paths, f"{name} has no guide")
                for relative in paths:
                    target = upstream / relative
                    self.assertTrue(target.is_file(), relative)
                    record = manifest["files"]["impeccable/upstream/" + relative]
                    self.assertEqual(hashlib.sha256(target.read_bytes()).hexdigest(), record["sha256"])
        self.assertIn("lists every current Impeccable command", self.section)
        self.assertIn("upstream/guide.md#commands", self.section)
        self.assertIn("does not start them", self.section)

    def test_ambiguous_mode_selection_is_owned_by_the_main_llm(self):
        section = self.router.split("## Ambiguous Mode Selection\n", 1)[1].split("\n## ", 1)[0]
        for rule in ("two or more modes plausibly fit", "the main LLM chooses the mode itself",
                     "No external routing helper or second opinion is involved",
                     "no\nextra routing deliberation", "no-match outcome",
                     "name the chosen mode and\nwhy it fits",
                     "main LLM selects both the mode guides and the applicable Impeccable\nplaybooks",
                     "does not expand task scope", "a playbook selection does not suppress that choice"):
            with self.subTest(rule=rule):
                self.assertIn(rule, section)

    def test_retired_jev_routing_is_absent_from_owned_design_sources(self):
        # Jev was retired on 2026-11-01; owned routing text must not reintroduce it.
        for path in (DESIGN / "SKILL.md", DESIGN / "references/impeccable/guide.md",
                     ROOT / "skills/impeccable/SKILL.md"):
            with self.subTest(path=path.relative_to(ROOT).as_posix()):
                self.assertNotRegex(path.read_text(encoding="utf-8"), r"(?i)\bjev\b")

    def test_scope_reading_and_fallback_boundaries_are_present(self):
        for rule in ("Explicit user selections take", "A negated playbook",
                     "Only\nsay a playbook was loaded after its file was successfully read",
                     "missing or unreadable", "clearly identified fallback",
                     "authorization to edit", "does not automatically start a browser"):
            with self.subTest(rule=rule):
                self.assertIn(rule, self.section)
        self.assertIn("[review-animations](references/review-animations/guide.md)", self.router)

    def test_hallmark_is_scoped_to_new_web_pages_and_ai_tell_audits(self):
        self.assertIn("[hallmark](references/hallmark/guide.md)", self.router)
        for rule in ("app UI such as dashboards, admin screens, editors and tools stays with\n`impeccable`",
                     "Hallmark never takes over an existing design unless the user names it"):
            with self.subTest(rule=rule):
                self.assertIn(rule, self.router)
        wrapper = (ROOT / "skills/hallmark/SKILL.md").read_text(encoding="utf-8")
        for rule in ("Never touch an existing design unless the user names", "Floor item 15",
                     "Skip\n  the comp step", "never add an edit hook",
                     "Do not run `theme.mjs index` or `theme.mjs scaffold`",
                     "An audit reports findings and proposed fixes and stops"):
            with self.subTest(rule=rule):
                self.assertIn(rule, wrapper)
        source = json.loads((ROOT / "skills/hallmark/upstream/source.json").read_text(encoding="utf-8"))
        for excluded in ("scripts/imagegen.mjs", "scripts/install.mjs", "scripts/install-hook.mjs"):
            with self.subTest(excluded=excluded):
                self.assertIn(excluded, source["excluded"])
                self.assertNotIn(excluded, source["files"])
                self.assertFalse((DESIGN / "references/hallmark/upstream" / excluded).exists())


if __name__ == "__main__":
    unittest.main()
