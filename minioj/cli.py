"""Command-line parsing and orchestration for a single judge run."""

import subprocess
import sys
from argparse import ArgumentParser
from collections.abc import Sequence
from pathlib import Path

import requests

from .config import ConfigurationError, load_exercise
from .feedback import construct_feedback, construct_stage_feedback
from .github import GitHubClient, GitHubError, get_repo
from .models import ExerciseId
from .runner import run_exercise


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(description="Judge a program based on the configuration.")
    parser.add_argument("-c", "--config", help="The config path.", default=".minioj/")
    parser.add_argument("-r", "--repo", help="The repo where the triggering PR lives.")
    parser.add_argument(
        "-x",
        "--comment",
        help="The PR comment body that triggers MiniOJ.",
        required=True,
    )
    parser.add_argument(
        "-i",
        "--pull-request",
        type=int,
        help="The ID of the PR that triggers MiniOJ.",
        required=True,
    )
    parser.add_argument(
        "-t", "--token", help="The token for the PR feedback comment.", required=True
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        client = GitHubClient(get_repo(args.repo), args.token)
        exercise_id = ExerciseId.from_comment(args.comment)
        try:
            exercise = load_exercise(Path(args.config), exercise_id)
        except ConfigurationError as error:
            body = construct_feedback(
                (error.title, str(error)),
                append_title=str(error.exercise) if error.exercise is not None else "",
            )
        else:
            results = run_exercise(exercise)
            body = construct_feedback(
                *construct_stage_feedback(*results), append_title=exercise.name
            )
        client.send_comment(args.pull_request, body)
    except (
        OSError,
        ValueError,
        subprocess.SubprocessError,
        requests.RequestException,
        GitHubError,
    ) as error:
        print(f"MiniOJ: {error}", file=sys.stderr)
        return 1
    return 0
