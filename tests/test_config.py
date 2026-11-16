import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from minioj.config import ConfigurationError, load_exercise
from minioj.models import ExerciseId, ExerciseNotFoundError, Stage


class ExerciseIdTests(unittest.TestCase):
    def test_parse_first_matching_line_case_insensitively(self):
        exercise = ExerciseId.from_comment(
            "run w9/ex9\n@minioj-bot help\n@MiniOJ-Bot RUN W02/EX03\n"
            "@minioj-bot run w4/ex5"
        )
        self.assertEqual(exercise, ExerciseId(2, 3))
        self.assertEqual(str(exercise), "w2/ex3")

    def test_require_mention_and_command_on_same_line(self):
        for comment in ("run w1/ex2", "@minioj-bot\nrun w1/ex2", "@minioj-bot help"):
            with self.subTest(comment=comment):
                with self.assertRaises(ExerciseNotFoundError):
                    ExerciseId.from_comment(comment)


class ConfigurationTests(unittest.TestCase):
    def setUp(self):
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name) / ".minioj"
        self.directory = self.root / "w1" / "ex2"
        self.directory.mkdir(parents=True)
        self.config_file = self.directory / "conf.json"
        self.exercise_id = ExerciseId(1, 2)

    def write_config(self, config):
        self.config_file.write_text(json.dumps(config), encoding="utf-8")

    def test_load_named_exercise_and_stages(self):
        self.write_config({
            "name": "Hello",
            "stages": [
                {"name": "Compile", "command": "cc main.c -o solution"},
                {"name": "Run", "command": "./solution", "cased": True},
            ],
        })
        exercise = load_exercise(self.root, self.exercise_id)
        self.assertEqual(exercise.id, self.exercise_id)
        self.assertEqual(exercise.name, "Hello")
        self.assertEqual(exercise.directory, self.directory)
        self.assertEqual(exercise.stages, (
            Stage("Compile", "cc main.c -o solution"),
            Stage("Run", "./solution", cased=True),
        ))

    def test_defaults_and_skipped_entries_preserve_original_indexes(self):
        self.write_config({
            "name": 7,
            "stages": [None, {}, {"command": 1}, {"command": "echo", "name": 7}],
        })
        exercise = load_exercise(self.root, self.exercise_id)
        self.assertEqual(exercise.name, "w1/ex2")
        self.assertEqual(exercise.stages, (Stage("Stage 3", "echo"),))

    def test_only_boolean_true_enables_cases(self):
        for value in (False, None, 1, "true", []):
            with self.subTest(value=value):
                self.write_config({"stages": [{"command": "echo", "cased": value}]})
                exercise = load_exercise(self.root, self.exercise_id)
                self.assertFalse(exercise.stages[0].cased)

    def test_missing_paths_have_distinct_feedback(self):
        for root, exercise_id, title, context in (
            (self.root / "missing", self.exercise_id, "OJ config not found", None),
            (self.root, ExerciseId(9, 9), "Exercise not found", ExerciseId(9, 9)),
            (self.root, self.exercise_id, "Exercise config not found", self.exercise_id),
        ):
            with self.subTest(title=title):
                with self.assertRaises(ConfigurationError) as raised:
                    load_exercise(root, exercise_id)
                self.assertEqual(raised.exception.title, title)
                self.assertEqual(raised.exception.exercise, context)

    def test_malformed_json_and_invalid_structure_are_config_errors(self):
        for contents in ("{", "[]", "null", "{}", '{"stages": {}}'):
            with self.subTest(contents=contents):
                self.config_file.write_text(contents, encoding="utf-8")
                with self.assertRaises(ConfigurationError) as raised:
                    load_exercise(self.root, self.exercise_id)
                self.assertEqual(raised.exception.title, "Exercise config error")
                self.assertEqual(raised.exception.exercise, self.exercise_id)
