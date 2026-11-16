from pathlib import Path
import shlex
import sys
from tempfile import TemporaryDirectory
import unittest

from minioj.models import Exercise, ExerciseId, Stage
from minioj.runner import find_case_files, run_exercise, run_stage


def python_command(source, *args):
    return shlex.join([sys.executable, "-c", source, *args])


class RunnerTests(unittest.TestCase):
    def setUp(self):
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)

    def test_arguments_closed_stdin_and_nonzero_output_are_captured(self):
        command = python_command(
            "import sys; print(sys.argv[1]); print(repr(sys.stdin.read())); "
            "print('failure detail', file=sys.stderr); sys.exit(7)",
            "quoted argument with spaces",
        )
        stage = Stage("Run", command)
        result = run_stage(stage, self.directory)
        self.assertEqual(result.stage, stage)
        self.assertEqual(len(result.commands), 1)
        process = result.commands[0]
        self.assertEqual(process.returncode, 7)
        self.assertEqual(process.stdout, "quoted argument with spaces\n''\n")
        self.assertEqual(process.stderr, "failure detail\n")
        self.assertIsNone(process.case_name)

    def test_cases_are_exact_files_in_numeric_order_and_supply_stdin(self):
        for name in ("case10.in", "case2.in", "case1.in", "case2.in.bak", "Case3.in"):
            (self.directory / name).write_text(name, encoding="utf-8")
        (self.directory / "case4.in").mkdir()
        (self.directory / "case.in").touch()
        names = [case.name for case in find_case_files(self.directory)]
        self.assertEqual(names, ["case1.in", "case2.in", "case10.in"])

        result = run_stage(
            Stage("Cases", python_command("import sys; print(sys.stdin.read())"), True),
            self.directory,
        )
        self.assertEqual([case.case_name for case in result.commands], names)
        self.assertEqual([case.stdout for case in result.commands], [f"{n}\n" for n in names])
        self.assertTrue(all(case.returncode == 0 for case in result.commands))

    def test_cased_stage_without_inputs_does_not_run(self):
        marker = self.directory / "unexpected"
        command = python_command("import pathlib, sys; pathlib.Path(sys.argv[1]).touch()", str(marker))
        result = run_stage(Stage("Cases", command, True), self.directory)
        self.assertEqual(result.commands, ())
        self.assertFalse(marker.exists())

    def test_stages_share_working_directory_and_continue_after_nonzero_exit(self):
        marker = self.directory / "stage-output"
        first = Stage("First", python_command(
            "import pathlib, sys; pathlib.Path(sys.argv[1]).write_text('ready'); sys.exit(3)",
            str(marker),
        ))
        second = Stage("Second", python_command(
            "import pathlib, sys; print(pathlib.Path(sys.argv[1]).read_text()); print(pathlib.Path.cwd())",
            str(marker),
        ))
        exercise = Exercise(ExerciseId(1, 1), "Example", self.directory, (first, second))
        results = run_exercise(exercise)
        self.assertEqual([result.stage.name for result in results], ["First", "Second"])
        self.assertEqual([result.commands[0].returncode for result in results], [3, 0])
        self.assertEqual(results[1].commands[0].stdout, f"ready\n{Path.cwd()}\n")

    def test_empty_command_has_clear_error(self):
        with self.assertRaisesRegex(ValueError, "empty command"):
            run_stage(Stage("Empty", "  "), self.directory)
