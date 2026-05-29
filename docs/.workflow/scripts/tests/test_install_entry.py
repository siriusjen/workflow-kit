#!/usr/bin/env python3
import subprocess
import tempfile
import unittest
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parents[1]
INSTALL_ENTRY = SCRIPTS_DIR / "install_entry.py"


class InstallEntryTests(unittest.TestCase):
    def run_install(self, target: Path, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["python3", str(INSTALL_ENTRY), "--target", str(target), *args],
            capture_output=True,
            text=True,
        )

    def test_creates_missing_entry_files_from_templates(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)

            result = self.run_install(target)

            self.assertEqual(result.returncode, 0, result.stderr)
            agents = (target / "AGENTS.md").read_text(encoding="utf-8")
            claude = (target / "CLAUDE.md").read_text(encoding="utf-8")
            self.assertIn("<!-- WORKFLOW-KIT:START -->", agents)
            self.assertIn("<!-- WORKFLOW-KIT:END -->", agents)
            self.assertIn("Codex", agents)
            self.assertIn("<!-- WORKFLOW-KIT:START -->", claude)
            self.assertIn("Claude Code", claude)

    def test_appends_block_without_changing_existing_content(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)
            existing = "# Project Rules\n\nKeep this exact text.\n"
            (target / "AGENTS.md").write_text(existing, encoding="utf-8")

            result = self.run_install(target, "--only", "AGENTS.md")

            self.assertEqual(result.returncode, 0, result.stderr)
            actual = (target / "AGENTS.md").read_text(encoding="utf-8")
            self.assertTrue(actual.startswith(existing))
            self.assertEqual(actual.count("<!-- WORKFLOW-KIT:START -->"), 1)
            self.assertIn("<!-- WORKFLOW-KIT:END -->", actual)

    def test_replaces_existing_block_idempotently(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)
            original = (
                "# Project Rules\n\n"
                "<!-- WORKFLOW-KIT:START -->\nold block\n<!-- WORKFLOW-KIT:END -->\n\n"
                "After block.\n"
            )
            (target / "AGENTS.md").write_text(original, encoding="utf-8")

            first = self.run_install(target, "--only", "AGENTS.md")
            after_first = (target / "AGENTS.md").read_text(encoding="utf-8")
            second = self.run_install(target, "--only", "AGENTS.md")
            after_second = (target / "AGENTS.md").read_text(encoding="utf-8")

            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertEqual(after_first, after_second)
            self.assertIn("# Project Rules", after_second)
            self.assertIn("After block.", after_second)
            self.assertNotIn("old block", after_second)
            self.assertEqual(after_second.count("<!-- WORKFLOW-KIT:START -->"), 1)

    def test_replaces_block_without_changing_surrounding_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)
            prefix = "# Project Rules\n\n"
            suffix = "\n\n\nAfter block.\n"
            original = (
                prefix
                + "<!-- WORKFLOW-KIT:START -->\nold block\n<!-- WORKFLOW-KIT:END -->"
                + suffix
            )
            (target / "AGENTS.md").write_text(original, encoding="utf-8")

            result = self.run_install(target, "--only", "AGENTS.md")

            self.assertEqual(result.returncode, 0, result.stderr)
            actual = (target / "AGENTS.md").read_text(encoding="utf-8")
            start = actual.index("<!-- WORKFLOW-KIT:START -->")
            end = actual.index("<!-- WORKFLOW-KIT:END -->") + len("<!-- WORKFLOW-KIT:END -->")
            self.assertEqual(actual[:start], prefix)
            self.assertEqual(actual[end:], suffix)

    def test_dry_run_prints_diff_and_does_not_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)
            target_file = target / "AGENTS.md"
            target_file.write_text("# Existing\n", encoding="utf-8")

            result = self.run_install(target, "--only", "AGENTS.md", "--dry-run")

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("--- AGENTS.md", result.stdout)
            self.assertIn("+++ AGENTS.md", result.stdout)
            self.assertEqual(target_file.read_text(encoding="utf-8"), "# Existing\n")

    def test_rejects_incomplete_target_marker(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)
            (target / "AGENTS.md").write_text(
                "# Existing\n<!-- WORKFLOW-KIT:START -->\n",
                encoding="utf-8",
            )

            result = self.run_install(target, "--only", "AGENTS.md")

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("incomplete WORKFLOW-KIT marker", result.stderr)

    def test_reports_missing_template(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)
            result = subprocess.run(
                [
                    "python3",
                    str(INSTALL_ENTRY),
                    "--target",
                    str(target),
                    "--template-dir",
                    str(target / "missing-templates"),
                ],
                capture_output=True,
                text=True,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("template not found", result.stderr)


if __name__ == "__main__":
    unittest.main()
