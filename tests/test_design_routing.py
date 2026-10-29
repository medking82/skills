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
        expected = {name: f"references/impeccable/upstream/reference/{name}.md"
                    for name in ("layout", "typeset", "distill", "polish", "critique")}
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
        self.assertIn("not the full set", self.section)
        self.assertIn("upstream/guide.md#commands", self.section)
        self.assertIn("does not start them", self.section)

    def test_jev_receipt_and_fail_open_contract_are_visible(self):
        section = self.router.split("## Jev-Assisted Mode Selection\n", 1)[1].split("\n## ", 1)[0]
        for rule in ("Reuse a design-mode recommendation already supplied by the",
                     "two or more modes plausibly fit", "no\nextra routing call",
                     "`mode`, `source`, and `requests` when present", "not evidence that this turn called Jev",
                     "minimal non-sensitive context", "without retrying", "main LLM selects the applicable Impeccable playbooks",
                     "does not expand task scope"):
            with self.subTest(rule=rule):
                self.assertIn(rule, section)

    def test_scope_reading_and_fallback_boundaries_are_present(self):
        for rule in ("Explicit user selections take", "A negated playbook",
                     "Only\nsay a playbook was loaded after its file was successfully read",
                     "missing or unreadable", "clearly identified fallback",
                     "authorization to edit", "does not automatically start a browser"):
            with self.subTest(rule=rule):
                self.assertIn(rule, self.section)
        self.assertIn("[review-animations](references/review-animations/guide.md)", self.router)


if __name__ == "__main__":
    unittest.main()
