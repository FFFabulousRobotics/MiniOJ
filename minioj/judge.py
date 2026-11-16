"""Run one configured exercise and return its feedback as Markdown."""

from pathlib import Path

from .config import ConfigurationError, load_exercise
from .feedback import construct_feedback, construct_stage_feedback
from .models import ExerciseId
from .runner import run_exercise


def judge(config_root: Path, exercise_id: ExerciseId) -> str:
    """Return feedback without resolving a repository or contacting GitHub."""
    try:
        exercise = load_exercise(config_root, exercise_id)
    except ConfigurationError as error:
        return construct_feedback(
            (error.title, str(error)),
            append_title=str(error.exercise) if error.exercise is not None else "",
        )
    results = run_exercise(exercise)
    return construct_feedback(
        *construct_stage_feedback(*results), append_title=exercise.name,
    )
