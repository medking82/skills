from __future__ import annotations

import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SKILLS_ROOT = REPO_ROOT / "skills"

SUPPORTED_FRONTMATTER_KEYS = {
    "allowed-tools",
    "description",
    "license",
    "metadata",
    "name",
}
CLAUDE_ONLY_KEYS = {
    "disable-model-invocation",
    "disable_model_invocation",
}
EXPLICIT_ONLY_SKILLS = {
    "pick-ui-library",
    "prototype",
    "review-animations",
}
SKILL_NAME_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
TOP_LEVEL_KEY_PATTERN = re.compile(r"^([A-Za-z0-9_-]+):(?:\s*(.*))?$")


def parse_frontmatter(skill_file: Path) -> dict[str, str]:
    lines = skill_file.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0].strip() != "---":
        raise AssertionError(f"{skill_file}: missing opening YAML frontmatter delimiter")

    try:
        closing_index = next(
            index for index, line in enumerate(lines[1:], start=1) if line.strip() == "---"
        )
    except StopIteration as error:
        raise AssertionError(
            f"{skill_file}: missing closing YAML frontmatter delimiter"
        ) from error

    fields: dict[str, str] = {}
    for line_number, line in enumerate(lines[1:closing_index], start=2):
        if not line or line[0].isspace() or line.lstrip().startswith("#"):
            continue

        match = TOP_LEVEL_KEY_PATTERN.fullmatch(line)
        if match is None:
            raise AssertionError(
                f"{skill_file}:{line_number}: unsupported top-level YAML syntax"
            )

        key, value = match.group(1), (match.group(2) or "").strip()
        if key in fields:
            raise AssertionError(f"{skill_file}:{line_number}: duplicate key {key!r}")
        fields[key] = value

    return fields


def unquote_scalar(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def read_implicit_invocation_policy(metadata_file: Path) -> bool | None:
    lines = metadata_file.read_text(encoding="utf-8").splitlines()
    policy_index: int | None = None

    for index, line in enumerate(lines):
        if line.strip() == "policy:" and not line.startswith((" ", "\t")):
            policy_index = index
            break

    if policy_index is None:
        return None

    for line_number, line in enumerate(lines[policy_index + 1 :], start=policy_index + 2):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if not line.startswith((" ", "\t")):
            break

        match = re.fullmatch(r"\s+allow_implicit_invocation:\s*(true|false)\s*", line)
        if match:
            return match.group(1) == "true"
        if "allow_implicit_invocation:" in line:
            raise AssertionError(
                f"{metadata_file}:{line_number}: allow_implicit_invocation must be true or false"
            )

    raise AssertionError(
        f"{metadata_file}: policy must declare allow_implicit_invocation as a boolean"
    )


class SkillMetadataTests(unittest.TestCase):
    def test_skill_metadata_is_codex_compatible(self) -> None:
        skill_files = sorted(SKILLS_ROOT.glob("*/SKILL.md"))
        self.assertTrue(skill_files, f"no skills found under {SKILLS_ROOT}")

        for skill_file in skill_files:
            with self.subTest(skill=skill_file.parent.name):
                fields = parse_frontmatter(skill_file)
                unsupported = set(fields) - SUPPORTED_FRONTMATTER_KEYS
                claude_only = set(fields) & CLAUDE_ONLY_KEYS

                self.assertFalse(
                    claude_only,
                    f"{skill_file}: move Claude-only invocation settings to agents/openai.yaml",
                )
                self.assertFalse(
                    unsupported,
                    f"{skill_file}: unsupported frontmatter keys: {sorted(unsupported)}",
                )

                for required_field in ("name", "description"):
                    self.assertTrue(
                        fields.get(required_field),
                        f"{skill_file}: {required_field} must be a non-empty scalar",
                    )

                skill_name = unquote_scalar(fields["name"])
                self.assertRegex(skill_name, SKILL_NAME_PATTERN)
                self.assertEqual(skill_name, skill_file.parent.name)

                metadata_file = skill_file.parent / "agents" / "openai.yaml"
                if metadata_file.exists():
                    read_implicit_invocation_policy(metadata_file)

                if skill_name in EXPLICIT_ONLY_SKILLS:
                    self.assertTrue(
                        metadata_file.exists(),
                        f"{skill_file}: explicit-only skill needs agents/openai.yaml",
                    )
                    self.assertIs(
                        read_implicit_invocation_policy(metadata_file),
                        False,
                        f"{metadata_file}: explicit-only skill must disable implicit invocation",
                    )


if __name__ == "__main__":
    unittest.main()
