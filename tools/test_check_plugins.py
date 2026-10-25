"""Regression checks for the public plugin surface, without installing a host."""

import tempfile
import unittest
from pathlib import Path

from check_plugins import check_plugin_layout


class PluginLayoutTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.plugin = Path(self.temporary.name)
        self.main = self.plugin / "skills/example/SKILL.md"
        self.main.parent.mkdir(parents=True)
        self.main.write_text("---\nname: example\ndescription: Example\n---\n")

    def check(self):
        return check_plugin_layout("example", self.plugin)

    def test_internal_workflow_is_allowed(self):
        workflow = self.main.parent / "references/workflows/setup.md"
        workflow.parent.mkdir(parents=True)
        workflow.write_text("# Setup\n")
        self.main.write_text(
            self.main.read_text() + "[Setup](references/workflows/setup.md)\n"
        )
        self.assertEqual(self.check(), [])

    def test_additional_or_nested_skill_is_rejected(self):
        for relative in ["skills/setup/SKILL.md", "skills/example/references/SKILL.md"]:
            with self.subTest(relative=relative):
                extra = self.plugin / relative
                extra.parent.mkdir(parents=True, exist_ok=True)
                extra.write_text("---\nname: setup\ndescription: Setup\n---\n")
                self.assertTrue(self.check())
                extra.unlink()

    def test_legacy_claude_command_is_rejected(self):
        command = self.plugin / "commands/setup.md"
        command.parent.mkdir()
        command.write_text("# Setup\n")
        self.assertTrue(self.check())

    def test_missing_main_is_rejected(self):
        self.main.unlink()
        self.assertTrue(self.check())

    def test_broken_or_external_workflow_is_rejected(self):
        for target in ["references/workflows/missing.md", "../../../../outside.md"]:
            with self.subTest(target=target):
                self.main.write_text(
                    "---\nname: example\n---\n" + f"[Setup]({target})\n"
                )
                self.assertTrue(self.check())


if __name__ == "__main__":
    unittest.main()
