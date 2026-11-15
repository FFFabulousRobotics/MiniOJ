import json
import re
import subprocess

import requests


class NoRemoteFoundError(Exception):
    pass


def get_repo(repo_hint: str | None) -> str:
    if repo_hint is not None:
        return repo_hint
    raw_remotes = subprocess.run(
        ["git", "remote"], capture_output=True, text=True, check=True
    )
    remotes = raw_remotes.stdout.split("\n")
    if len(remotes) <= 1:
        raise NoRemoteFoundError()
    raw_remote_url = subprocess.run(
        ["git", "remote", "get-url", remotes[0]],
        capture_output=True,
        text=True,
        check=True,
    )
    remote_url = raw_remote_url.stdout.strip()
    repo_match = re.search(
        r"([a-zA-Z0-9\-]{1,39}/[a-zA-Z0-9\-]{1,100})\.git", remote_url
    )
    if repo_match is None:
        raise NoRemoteFoundError()
    return repo_match.group(1)


class NotAllowedError(Exception):
    pass


class ResourceNotFoundError(Exception):
    pass


def send_comment(repo: str, id: int, body: str, token: str):
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
    }
    post_url = f"https://api.github.com/repos/{repo}/issues/{id}/comments"
    response = requests.post(
        post_url,
        headers=headers,
        data=json.dumps({"body": body}),
    )
    match response.status_code:
        case 403, 422:
            raise NotAllowedError(status_code=response.status_code)
        case 404, 410:
            raise ResourceNotFoundError(status_code=response.status_code)
        case 201:
            print(f"Sent comment to {post_url}")


class ExerciseNotFoundError(Exception):
    pass


def parse_ex(comment: str) -> tuple[int, int]:
    lines = comment.splitlines()
    for line in lines:
        if "@minioj-bot" not in line.lower():
            continue
        ex_match = re.search(r"run w([0-9]+)/ex([0-9]+)", line.lower())
        if ex_match is None:
            continue
        raw_week = ex_match.group(1)
        raw_ex = ex_match.group(2)
        try:
            week = int(raw_week, base=10)
            ex = int(raw_ex, base=10)
            return (week, ex)
        except ValueError:
            continue
    raise ExerciseNotFoundError()


def construct_feedback(*sections: tuple[str, str]):
    body = "## MiniOJ feedback\n\nMade with :heart: by FFFabulous 19726.\n\n"
    for sec_title, sec_body in sections:
        body += f"### {sec_title}\n\n"
        body += sec_body
        body += "\n\n"
    return body


def main():
    from argparse import ArgumentParser

    argparser = ArgumentParser(
        description="Judge a program based on the configuration."
    )

    argparser.add_argument(
        "-c", "--config", help="The config path.", required=False, default=".minioj/"
    )
    argparser.add_argument(
        "-r", "--repo", help="The repo where the triggering PR lives.", required=False
    )
    argparser.add_argument(
        "-x",
        "--comment",
        help="The PR comment body that triggers MiniOJ.",
        required=True,
    )
    argparser.add_argument(
        "-i",
        "--pull-request",
        type=int,
        help="The ID of the PR that triggers MiniOJ.",
        required=True,
    )
    argparser.add_argument(
        "-t", "--token", help="The token for the PR feedback comment.", required=True
    )

    args = argparser.parse_args()

    repo = get_repo(args.repo)

    from pathlib import Path

    config_path = Path(args.config)

    if not config_path.exists():
        send_comment(
            repo,
            args.pull_request,
            construct_feedback(
                ("OJ config not found", "Contact admins to setup OJ config.")
            ),
            args.token,
        )


if __name__ == "__main__":
    main()
