"""Data shared by configuration, execution, and feedback."""

import re
from dataclasses import dataclass
from pathlib import Path


class ExerciseNotFoundError(ValueError):
    """The triggering comment does not identify an exercise."""


@dataclass(frozen=True)
class ExerciseId:
    week: int
    exercise: int

    def __str__(self) -> str:
        return f"w{self.week}/ex{self.exercise}"

    @classmethod
    def from_comment(cls, comment: str) -> "ExerciseId":
        for line in comment.lower().splitlines():
            if "@minioj-bot" not in line:
                continue
            match = re.search(r"run w([0-9]+)/ex([0-9]+)", line)
            if match is not None:
                return cls(week=int(match[1]), exercise=int(match[2]))
        raise ExerciseNotFoundError(
            "No exercise found; mention @minioj-bot and use 'run w1/ex1'."
        )


@dataclass(frozen=True)
class Stage:
    name: str
    command: str
    cased: bool = False


@dataclass(frozen=True)
class Exercise:
    id: ExerciseId
    name: str
    directory: Path
    stages: tuple[Stage, ...]


@dataclass(frozen=True)
class CommandResult:
    returncode: int
    stdout: str
    stderr: str
    case_name: str | None = None


@dataclass(frozen=True)
class StageResult:
    stage: Stage
    commands: tuple[CommandResult, ...]
