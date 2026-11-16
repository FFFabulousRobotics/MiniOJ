"""Resolve the target repository and publish feedback through GitHub."""

import re
import subprocess

import requests


class NoRemoteFoundError(ValueError):
    """No repository could be inferred from Git remotes."""


class GitHubError(RuntimeError):
    def __init__(self, status_code: int) -> None:
        super().__init__(f"GitHub rejected the feedback comment (HTTP {status_code}).")
        self.status_code = status_code


class NotAllowedError(GitHubError):
    pass


class ResourceNotFoundError(GitHubError):
    pass


def get_repo(repo_hint: str | None) -> str:
    if repo_hint is not None:
        return repo_hint
    remotes = subprocess.run(
        ["git", "remote"], capture_output=True, text=True, check=True
    ).stdout.splitlines()
    if not remotes:
        raise NoRemoteFoundError("No Git remote found; supply --repo owner/repository.")
    remote_url = subprocess.run(
        ["git", "remote", "get-url", remotes[0]],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    match = re.search(r"[:/]([^/:]+/[^/]+?)(?:\.git)?/?$", remote_url)
    if match is None:
        raise NoRemoteFoundError(
            "Cannot determine the repository from Git; supply --repo owner/repository."
        )
    return match[1]


class GitHubClient:
    def __init__(self, repo: str, token: str) -> None:
        self.repo = repo
        self._token = token

    def send_comment(self, pull_request: int, body: str) -> None:
        url = f"https://api.github.com/repos/{self.repo}/issues/{pull_request}/comments"
        response = requests.post(
            url,
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {self._token}",
            },
            json={"body": body},
            timeout=30,
        )
        if response.status_code in (403, 422):
            raise NotAllowedError(response.status_code)
        if response.status_code in (404, 410):
            raise ResourceNotFoundError(response.status_code)
        response.raise_for_status()
        if response.status_code != 201:
            raise GitHubError(response.status_code)
        print(f"Sent comment to {url}")
