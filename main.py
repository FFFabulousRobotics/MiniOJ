import json
import re
import subprocess
from typing import TypedDict

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


def construct_feedback(*sections: tuple[str, str], append_title: str = "") -> str:
    body = "## MiniOJ feedback"
    if append_title:
        body += f" - {append_title}"
    body += "\n\nMade with :heart: by FTC Team FFFabulous 19726.\n\n"
    for sec_title, sec_body in sections:
        body += f"### {sec_title}\n\n"
        body += sec_body
        body += "\n\n"
    return body


class Stage(TypedDict):
    name: str
    command: str
    result: subprocess.CompletedProcess[str] | list[subprocess.CompletedProcess[str]]


def construct_result_feedback(result: subprocess.CompletedProcess[str]):
    body = f"Status: {result.returncode}\n\n"
    body += f"`stdout`:\n\n```\n{result.stdout}\n```\n\n"
    body += f"`stderr`: \n\n```\n{result.stderr}\n```\n\n"
    return body


def construct_stage_feedback(ex_name: str, *stages: Stage) -> list[tuple[str, str]]:
    sections = []
    for stage in stages:
        sec_title = stage["name"]
        sec_body = ""
        if isinstance(stage["result"], list):
            for i, case in enumerate(stage["result"]):
                sec_body += f"#### Case {i}:\n\n"
                sec_body += construct_result_feedback(case)
        else:
            sec_body += construct_result_feedback(stage["result"])
        sections.append((sec_title, sec_body))
    return sections


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

    main_config_path = Path(args.config)

    if not main_config_path.exists() or not main_config_path.is_dir():
        send_comment(
            repo,
            args.pull_request,
            construct_feedback(
                ("OJ config not found", "Contact admins to setup OJ config.")
            ),
            args.token,
        )
        return

    week, ex = parse_ex(args.comment)

    ex_config_path = main_config_path / f"w{week}" / f"ex{ex}"

    if not ex_config_path.exists() or not ex_config_path.is_dir():
        send_comment(
            repo,
            args.pull_request,
            construct_feedback(
                ("Exercise not found", "Check if you typed the right exercise."),
                append_title=f"w{week}/ex{ex}",
            ),
            args.token,
        )
        return

    ex_config_file = ex_config_path / "conf.json"

    if not ex_config_file.exists() or not ex_config_file.is_file():
        send_comment(
            repo,
            args.pull_request,
            construct_feedback(
                ("Exercise config not found", "Contact admins to setup OJ config."),
                append_title=f"w{week}/ex{ex}",
            ),
            args.token,
        )
        return

    with open(ex_config_file, mode="r") as ex_config_fp:
        ex_config = json.load(ex_config_fp)

    if (
        type(ex_config) != dict
        or "stages" not in ex_config
        or type(ex_config["stages"]) != list
    ):
        send_comment(
            repo,
            args.pull_request,
            construct_feedback(
                ("Exercise config error", "Contact admins to setup OJ config."),
                append_title=f"w{week}/ex{ex}",
            ),
            args.token,
        )
        return

    ex_name = (
        ex_config["name"]
        if "name" in ex_config and type(ex_config["name"]) == str
        else f"w{week}/ex{ex}"
    )

    ex_stages = ex_config["stages"]

    stage_results = []

    for stage_index, stage in enumerate(ex_stages):
        if (
            type(stage) != dict
            or "command" not in stage
            or type(stage["command"]) != str
        ):
            continue

        stage_name = f"Stage {stage_index}"
        if "name" in stage and type(stage["name"]) == str:
            stage_name = stage["name"]

        if "cased" in stage and type(stage["cased"]) == True:
            raw_ex_case_in_files = ex_config_path.glob(
                "case[0-9]*.in", case_sensitive=True
            )
            ex_case_in_files = []
            for candidate_file in raw_ex_case_in_files:
                if re.match(r"case[0-9]+\.in", candidate_file.name):
                    ex_case_in_files.append(candidate_file)
            case_results = []
            for case_in in ex_case_in_files:
                with open(case_in, mode="r") as case_in_fp:
                    case_result = subprocess.run(
                        stage["command"],
                        stdin=case_in_fp,
                        capture_output=True,
                        text=True,
                        check=False,
                    )
                    case_results.append(case_result)
            stage_obj = Stage(
                name=stage_name, command=stage["command"], result=case_results
            )
            stage_results.append(stage_obj)

        else:
            result = subprocess.run(
                stage["command"],
                stdin=True,
                capture_output=True,
                text=True,
                check=False,
            )
            stage_obj = Stage(name=stage_name, command=stage["command"], result=result)
            stage_results.append(stage_obj)

    stages_body = construct_stage_feedback(ex_name, *stage_results)
    comment_body = construct_feedback(*stages_body, append_title=ex_name)

    send_comment(repo, args.pull_request, comment_body, args.token)


if __name__ == "__main__":
    main()
