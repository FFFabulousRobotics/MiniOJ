"""Command-line parsing and orchestration for a single judge run."""

import subprocess
import sys
from argparse import ArgumentParser
from collections.abc import Sequence
from pathlib import Path

from .feedback import construct_feedback
from .judge import judge
from .models import ExerciseId


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(
        description="Run an exercise and write feedback Markdown to stdout."
    )
    parser.add_argument("-c", "--config", help="The config path.", default=".minioj/")
    parser.add_argument(
        "-o", "--output", type=Path,
        help="Write feedback Markdown to this file instead of stdout.",
    )
    parser.add_argument(
        "-x",
        "--comment",
        help="The PR comment body that triggers MiniOJ.",
        required=True,
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    status = 0
    try:
        exercise_id = ExerciseId.from_comment(args.comment)
        body = judge(Path(args.config), exercise_id)
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        body = construct_feedback(("Unable to judge", str(error)))
        status = 1
    if args.output is None:
        sys.stdout.write(body)
    else:
        try:
            args.output.write_text(body, encoding="utf-8")
        except OSError as error:
            print(f"MiniOJ: cannot write feedback: {error}", file=sys.stderr)
            return 1
    return status
