from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
import json
from pathlib import Path
import shlex
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from minioj.cli import main


class CliTests(unittest.TestCase):
    def setUp(self):
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name) / ".minioj"
        self.args = [
            "--comment", "@minioj-bot run w1/ex2", "--config", str(self.root),
        ]

    def test_real_config_execution_emits_only_feedback_markdown(self):
        directory = self.root / "w1" / "ex2"
        directory.mkdir(parents=True)
        command = shlex.join([sys.executable, "-c", "import sys; print(sys.stdin.read().upper())"])
        config = {"name": "Integration", "stages": [
            {"name": "Once", "command": command},
            {"name": "Cases", "command": command, "cased": True},
        ]}
        (directory / "conf.json").write_text(json.dumps(config), encoding="utf-8")
        (directory / "case2.in").write_text("second", encoding="utf-8")
        (directory / "case1.in").write_text("first", encoding="utf-8")
        (directory / "case2.out").write_text("SECOND\n", encoding="utf-8")
        (directory / "case1.out").write_text("expected\n", encoding="utf-8")
        with redirect_stdout(StringIO()) as output, redirect_stderr(StringIO()) as error:
            self.assertEqual(main(self.args), 0)
        body = output.getvalue()
        self.assertEqual(error.getvalue(), "")
        self.assertTrue(body.startswith("## MiniOJ feedback - Integration"))
        self.assertIn("### Once", body)
        self.assertIn("### Cases", body)
        self.assertEqual(body.count("Exit status: `0`"), 3)
        self.assertIn("```diff\n-expected\n+FIRST\n", body)
        self.assertIn("#### Case 1 - Passed", body)
        self.assertIn("```\nSECOND\n\n```", body)
        self.assertNotIn("No differences.", body)
        self.assertIn("#### Case 0 - Failed", body)

    def test_missing_root_emits_configuration_feedback(self):
        with redirect_stdout(StringIO()) as output:
            self.assertEqual(main(self.args), 0)
        body = output.getvalue()
        self.assertTrue(body.startswith("## MiniOJ feedback\n"))
        self.assertIn("### OJ config not found", body)

    def test_invalid_json_emits_exercise_config_feedback(self):
        directory = self.root / "w1" / "ex2"
        directory.mkdir(parents=True)
        (directory / "conf.json").write_text("{", encoding="utf-8")
        with redirect_stdout(StringIO()) as output:
            self.assertEqual(main(self.args), 0)
        body = output.getvalue()
        self.assertTrue(body.startswith("## MiniOJ feedback - w1/ex2"))
        self.assertIn("### Exercise config error", body)

    def test_invalid_comment_returns_failure_with_markdown(self):
        self.args[self.args.index("--comment") + 1] = "@minioj-bot help"
        with redirect_stdout(StringIO()) as output, redirect_stderr(StringIO()) as error:
            self.assertEqual(main(self.args), 1)
        self.assertIn("### Unable to judge", output.getvalue())
        self.assertIn("No exercise found", output.getvalue())
        self.assertEqual(error.getvalue(), "")

    @patch("minioj.cli.judge", side_effect=OSError("command not found"))
    def test_execution_failure_returns_nonzero_with_markdown(self, judge):
        with redirect_stdout(StringIO()) as output:
            self.assertEqual(main(self.args), 1)
        self.assertIn("command not found", output.getvalue())

    @patch("socket.socket", side_effect=AssertionError("network access is forbidden"))
    def test_feedback_requires_neither_network_nor_git(self, socket):
        with redirect_stdout(StringIO()) as output:
            self.assertEqual(main(self.args), 0)
        self.assertIn("OJ config not found", output.getvalue())
        socket.assert_not_called()

    def test_legacy_github_arguments_are_rejected(self):
        with redirect_stderr(StringIO()):
            with self.assertRaises(SystemExit) as error:
                main(self.args + ["--token", "unused"])
        self.assertEqual(error.exception.code, 2)

    def test_output_file_contains_the_same_markdown_as_stdout(self):
        output_file = self.root.parent / "feedback.md"
        with redirect_stdout(StringIO()) as output:
            self.assertEqual(main(self.args), 0)
        expected = output.getvalue()
        with redirect_stdout(StringIO()) as output:
            self.assertEqual(main(self.args + ["--output", str(output_file)]), 0)
        self.assertEqual(output.getvalue(), "")
        self.assertEqual(output_file.read_text(encoding="utf-8"), expected)

    def test_output_file_is_written_for_an_invalid_comment(self):
        output_file = self.root.parent / "failure.md"
        self.args[self.args.index("--comment") + 1] = "@minioj-bot help"
        with redirect_stdout(StringIO()) as output:
            self.assertEqual(main(self.args + ["-o", str(output_file)]), 1)
        self.assertEqual(output.getvalue(), "")
        self.assertIn("No exercise found", output_file.read_text(encoding="utf-8"))

    def test_output_file_errors_are_reported_on_stderr(self):
        output_file = self.root.parent / "missing" / "feedback.md"
        with redirect_stdout(StringIO()) as output, redirect_stderr(StringIO()) as error:
            self.assertEqual(main(self.args + ["--output", str(output_file)]), 1)
        self.assertEqual(output.getvalue(), "")
        self.assertIn("cannot write feedback", error.getvalue())

    def test_checkout_entry_points_accept_help(self):
        root = Path(__file__).resolve().parents[1]
        for arguments in ([str(root / "main.py"), "--help"], ["-m", "minioj", "--help"]):
            with self.subTest(arguments=arguments):
                result = subprocess.run(
                    [sys.executable, *arguments], cwd=root,
                    capture_output=True, text=True, check=True,
                )
                self.assertIn("--comment", result.stdout)
                self.assertIn("--config", result.stdout)
                self.assertIn("--output", result.stdout)
                self.assertNotIn("--token", result.stdout)
