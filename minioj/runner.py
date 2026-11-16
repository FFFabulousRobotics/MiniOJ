"""Execute stages in order, optionally once per exercise input file."""

import re
import shlex
import subprocess
from pathlib import Path

from .models import CommandResult, Exercise, Stage, StageResult


def find_case_files(directory: Path) -> tuple[Path, ...]:
    cases = [
        candidate
        for candidate in directory.iterdir()
        if candidate.is_file() and re.fullmatch(r"case[0-9]+\.in", candidate.name)
    ]
    return tuple(sorted(cases, key=lambda case: (int(case.stem[4:]), case.name)))


def run_stage(stage: Stage, directory: Path) -> StageResult:
    # Commands use shell-style quoting for arguments, but do not start a shell.
    command = shlex.split(stage.command)
    if not command:
        raise ValueError(f"Stage {stage.name!r} has an empty command.")

    results = []
    if stage.cased:
        for case_file in find_case_files(directory):
            with case_file.open(encoding="utf-8") as case_input:
                process = subprocess.run(
                    command,
                    stdin=case_input,
                    capture_output=True,
                    text=True,
                    check=False,
                )
            results.append(
                CommandResult(
                    process.returncode, process.stdout, process.stderr, case_file.name
                )
            )
    else:
        process = subprocess.run(
            command,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            check=False,
        )
        results.append(
            CommandResult(process.returncode, process.stdout, process.stderr)
        )

    return StageResult(stage, tuple(results))


def run_exercise(exercise: Exercise) -> tuple[StageResult, ...]:
    return tuple(run_stage(stage, exercise.directory) for stage in exercise.stages)
