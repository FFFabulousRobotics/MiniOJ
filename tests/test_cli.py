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

import requests

from minioj.cli import main


class CliTests(unittest.TestCase):
    def setUp(self):
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name) / ".minioj"
        self.args = [
            "--repo", "owner/repo", "--pull-request", "42", "--token", "test-token",
            "--comment", "@minioj-bot run w1/ex2", "--config", str(self.root),
        ]

    @patch("minioj.github.requests.post")
    def test_real_config_execution_and_feedback_with_mocked_github(self, post):
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
        response = requests.Response()
        response.status_code = 201
        post.return_value = response
        with redirect_stdout(StringIO()):
            self.assertEqual(main(self.args), 0)
        post.assert_called_once()
        body = post.call_args.kwargs["json"]["body"]
        self.assertTrue(body.startswith("## MiniOJ feedback - Integration"))
        self.assertIn("### Once", body)
        self.assertIn("### Cases", body)
        self.assertEqual(body.count("Status: 0"), 3)
        self.assertIn("```diff\n--- case1.out\n+++ stdout\n@@ -1 +1 @@", body)
        self.assertIn("-expected\n+FIRST\n", body)
        self.assertIn("**Case 1:**", body)
        self.assertIn("```diff\nNo differences.\n```", body)
        self.assertEqual(body.count("</details>\n\nPassed!\n\n"), 1)
        self.assertEqual(body.count("</details>\n\nFailed...\n\n"), 1)

    @patch("minioj.cli.GitHubClient.send_comment")
    def test_missing_root_posts_configuration_feedback(self, send):
        self.assertEqual(main(self.args), 0)
        send.assert_called_once()
        pull_request, body = send.call_args.args
        self.assertEqual(pull_request, 42)
        self.assertTrue(body.startswith("## MiniOJ feedback\n"))
        self.assertIn("### OJ config not found", body)

    @patch("minioj.cli.GitHubClient.send_comment")
    def test_invalid_json_posts_exercise_config_feedback(self, send):
        directory = self.root / "w1" / "ex2"
        directory.mkdir(parents=True)
        (directory / "conf.json").write_text("{", encoding="utf-8")
        self.assertEqual(main(self.args), 0)
        body = send.call_args.args[1]
        self.assertTrue(body.startswith("## MiniOJ feedback - w1/ex2"))
        self.assertIn("### Exercise config error", body)

    @patch("minioj.cli.GitHubClient.send_comment")
    def test_invalid_comment_returns_failure_without_posting(self, send):
        self.args[self.args.index("--comment") + 1] = "@minioj-bot help"
        with redirect_stderr(StringIO()) as error:
            self.assertEqual(main(self.args), 1)
        self.assertIn("No exercise found", error.getvalue())
        send.assert_not_called()

    @patch("minioj.cli.GitHubClient.send_comment", side_effect=requests.Timeout("timed out"))
    def test_network_failure_returns_nonzero(self, send):
        with redirect_stderr(StringIO()) as error:
            self.assertEqual(main(self.args), 1)
        self.assertIn("timed out", error.getvalue())

    def test_checkout_entry_points_accept_help(self):
        root = Path(__file__).resolve().parents[1]
        for arguments in ([str(root / "main.py"), "--help"], ["-m", "minioj", "--help"]):
            with self.subTest(arguments=arguments):
                result = subprocess.run(
                    [sys.executable, *arguments], cwd=root,
                    capture_output=True, text=True, check=True,
                )
                self.assertIn("--pull-request", result.stdout)
                self.assertIn("--config", result.stdout)
