"""Read the existing .minioj/wN/exN/conf.json configuration format."""

import json
from pathlib import Path

from .models import Exercise, ExerciseId, Stage


class ConfigurationError(ValueError):
    """A configuration problem that can be reported in PR feedback."""

    def __init__(
        self,
        title: str,
        message: str = "Contact admins to setup OJ config.",
        exercise: ExerciseId | None = None,
    ) -> None:
        super().__init__(message)
        self.title = title
        self.exercise = exercise


def load_exercise(config_root: Path, exercise_id: ExerciseId) -> Exercise:
    if not config_root.is_dir():
        raise ConfigurationError("OJ config not found")

    directory = config_root / str(exercise_id)
    if not directory.is_dir():
        raise ConfigurationError(
            "Exercise not found",
            "Check if you typed the right exercise.",
            exercise_id,
        )

    config_file = directory / "conf.json"
    if not config_file.is_file():
        raise ConfigurationError("Exercise config not found", exercise=exercise_id)

    try:
        with config_file.open(encoding="utf-8") as config_stream:
            config = json.load(config_stream)
    except (OSError, UnicodeError, ValueError) as error:
        raise ConfigurationError(
            "Exercise config error", exercise=exercise_id
        ) from error

    if not isinstance(config, dict) or not isinstance(config.get("stages"), list):
        raise ConfigurationError("Exercise config error", exercise=exercise_id)

    name = config.get("name")
    if not isinstance(name, str):
        name = str(exercise_id)

    stages = []
    for index, raw_stage in enumerate(config["stages"]):
        if not isinstance(raw_stage, dict):
            continue
        command = raw_stage.get("command")
        if not isinstance(command, str):
            continue
        stage_name = raw_stage.get("name")
        if not isinstance(stage_name, str):
            stage_name = f"Stage {index}"
        stages.append(
            Stage(
                name=stage_name,
                command=command,
                cased=raw_stage.get("cased") is True,
            )
        )

    return Exercise(exercise_id, name, directory, tuple(stages))
