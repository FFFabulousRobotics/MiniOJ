from contextlib import redirect_stdout
from io import StringIO
import subprocess
import unittest
from unittest.mock import patch

import requests

from minioj.github import (
    GitHubClient,
    GitHubError,
    NoRemoteFoundError,
    NotAllowedError,
    ResourceNotFoundError,
    get_repo,
)


class RepositoryTests(unittest.TestCase):
    @patch("minioj.github.subprocess.run")
    def test_explicit_repo_does_not_invoke_git(self, run):
        self.assertEqual(get_repo("owner/repo"), "owner/repo")
        run.assert_not_called()

    @patch("minioj.github.subprocess.run")
    def test_https_and_ssh_remotes_with_optional_suffix(self, run):
        for url in (
            "https://github.com/owner/repo.name_with-dashes.git",
            "git@github.com:owner/repo.name_with-dashes.git",
            "ssh://git@github.com/owner/repo.name_with-dashes.git",
            "https://github.com/owner/repo.name_with-dashes",
            "https://github.com/owner/repo.name_with-dashes/",
        ):
            with self.subTest(url=url):
                run.side_effect = [
                    subprocess.CompletedProcess([], 0, "origin\nupstream\n"),
                    subprocess.CompletedProcess([], 0, url + "\n"),
                ]
                self.assertEqual(get_repo(None), "owner/repo.name_with-dashes")
                self.assertEqual(run.call_args.args[0], ["git", "remote", "get-url", "origin"])

    @patch("minioj.github.subprocess.run")
    def test_missing_or_unparseable_remote(self, run):
        for outputs in (("",), ("origin\n", "not-a-remote")):
            with self.subTest(outputs=outputs):
                run.side_effect = [subprocess.CompletedProcess([], 0, out) for out in outputs]
                with self.assertRaises(NoRemoteFoundError):
                    get_repo(None)


class GitHubClientTests(unittest.TestCase):
    @patch("minioj.github.requests.post")
    def test_success_posts_json_and_authentication_with_timeout(self, post):
        response = requests.Response()
        response.status_code = 201
        post.return_value = response
        with redirect_stdout(StringIO()) as output:
            GitHubClient("owner/repo", "test-token").send_comment(42, "feedback")
        post.assert_called_once_with(
            "https://api.github.com/repos/owner/repo/issues/42/comments",
            headers={"Accept": "application/vnd.github+json", "Authorization": "Bearer test-token"},
            json={"body": "feedback"},
            timeout=30,
        )
        self.assertIn("Sent comment", output.getvalue())

    @patch("minioj.github.requests.post")
    def test_known_statuses_raise_specific_errors(self, post):
        for status, expected in (
            (403, NotAllowedError), (422, NotAllowedError),
            (404, ResourceNotFoundError), (410, ResourceNotFoundError),
        ):
            with self.subTest(status=status):
                response = requests.Response()
                response.status_code = status
                post.return_value = response
                with self.assertRaises(expected) as raised:
                    GitHubClient("owner/repo", "test-token").send_comment(42, "feedback")
                self.assertEqual(raised.exception.status_code, status)

    @patch("minioj.github.requests.post")
    def test_other_failures_and_unexpected_success_are_not_silent(self, post):
        for status, expected in ((401, requests.HTTPError), (500, requests.HTTPError), (200, GitHubError)):
            with self.subTest(status=status):
                response = requests.Response()
                response.status_code = status
                post.return_value = response
                with self.assertRaises(expected):
                    GitHubClient("owner/repo", "test-token").send_comment(42, "feedback")
