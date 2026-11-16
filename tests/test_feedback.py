import unittest

from minioj.feedback import (
    construct_feedback,
    construct_output_diff,
    construct_result_feedback,
    construct_stage_feedback,
)
from minioj.models import CommandResult, Stage, StageResult


class FeedbackTests(unittest.TestCase):
    def test_markdown_matches_existing_single_run_format(self):
        result = StageResult(Stage("Compile", "cc"), (CommandResult(1, "out", "err"),))
        body = construct_feedback(*construct_stage_feedback(result), append_title="Example")
        self.assertEqual(body, (
            "## MiniOJ feedback - Example\n\n"
            "Made with :heart: by FTC Team FFFabulous 19726.\n\n"
            "### Compile\n\n"
            "<details><summary>Details</summary>\n\n"
            "Exit status: `1`\n\n"
            "File `stdout`:\n\n```\nout\n```\n\n"
            "File `stderr`: \n\n```\nerr\n```\n\n"
            "</details>\n\n\n\n"
        ))

    def test_cased_results_have_independent_numbered_sections(self):
        result = StageResult(Stage("Run", "./solution", True), (
            CommandResult(0, "first\n", "", "case1.in", "expected first\n"),
            CommandResult(2, "second\n", "error", "case2.in", "expected second\n"),
            CommandResult(0, "same\n", "", "case3.in", "same\n"),
            CommandResult(1, "same\n", "error", "case4.in", "same\n"),
            CommandResult(0, "output", "", "case5.in"),
        ))
        sections = construct_stage_feedback(result)
        self.assertEqual(sections[0][0], "Run")
        body = sections[0][1]
        self.assertIn("#### Case 0 - Failed\n\n", body)
        self.assertIn("#### Case 1 - Failed\n\n", body)
        self.assertIn("Exit status: `0`", body)
        self.assertIn("Exit status: `2`", body)
        self.assertIn("```diff\n-expected first\n+first\n", body)
        self.assertIn("```diff\n-expected second\n+second\n", body)
        self.assertIn("File `stderr`: \n\n```\nerror\n```", body)
        self.assertLess(body.index("first"), body.index("second"))
        cases = body.split("#### Case ")[1:]
        self.assertEqual(len(cases), 5)
        for case, verdict in zip(cases, (
            "Failed", "Failed", "Passed", "Failed", "Failed",
        )):
            with self.subTest(case=case.splitlines()[0]):
                self.assertEqual(case.splitlines()[0].split(" - ", 1)[1], verdict)
                self.assertTrue(case.endswith("</details>\n\n"))

    def test_matching_outputs_including_empty_output_show_plain_stdout(self):
        for stdout in ("", "same\n", "same"):
            with self.subTest(stdout=stdout):
                result = CommandResult(0, stdout, "", "case1.in", stdout)
                body = construct_result_feedback(result)
                self.assertIn(f"File `stdout`:\n\n```\n{stdout}\n```", body)
                self.assertNotIn("```diff", body)
                self.assertNotIn("No differences.", body)
                self.assertIs(result.output_matches, True)

    def test_missing_expected_output_is_explicit_and_retains_raw_stdout(self):
        body = construct_result_feedback(CommandResult(0, "actual", "", "case1.in"))
        self.assertIn("Expected output missing: `case1.out`.", body)
        self.assertIn("Comparison unavailable.", body)
        self.assertIn("```\nactual\n```", body)
        self.assertNotIn("No differences.", body)

    def test_diff_shows_context_whitespace_and_missing_newlines_without_headers(self):
        diff = construct_output_diff("before\nexpected\nafter\n", "before\nactual\nafter\n")
        self.assertEqual(diff, (
            " before\n-expected\n+actual\n after\n"
        ))
        for expected, actual, tail in (
            ("same\n", "same", "-same\n+same\n\\ No newline at end of file\n"),
            ("same", "same\n", "-same\n\\ No newline at end of file\n+same\n"),
            ("same \n", "same\n", "-same \n+same\n"),
        ):
            with self.subTest(expected=expected, actual=actual):
                diff = construct_output_diff(expected, actual)
                self.assertEqual(diff, tail)

    def test_missing_line_in_200_line_output_keeps_all_other_lines(self):
        expected_lines = [f"line {number}\n" for number in range(1, 201)]
        actual_lines = expected_lines[:150] + expected_lines[151:]
        body = construct_result_feedback(CommandResult(
            0, "".join(actual_lines), "", "case1.in", "".join(expected_lines),
        ))
        diff = body.split("```diff\n", 1)[1].split("\n```", 1)[0]
        self.assertEqual(diff.splitlines(), [
            ("-" if number == 151 else " ") + f"line {number}"
            for number in range(1, 201)
        ])

    def test_distant_changes_keep_the_entire_output(self):
        expected_lines = [f"line {number}\n" for number in range(1, 201)]
        actual_lines = ["first\n", *expected_lines[1:-1], "last\n"]
        diff = construct_output_diff("".join(expected_lines), "".join(actual_lines))
        self.assertEqual(diff, (
            "-line 1\n+first\n"
            + "".join(" " + line for line in expected_lines[1:-1])
            + "-line 200\n+last\n"
        ))

    def test_long_repeated_output_only_marks_the_missing_line(self):
        actual = "repeat\n" * 200
        expected = "repeat\n" * 150 + "missing\n" + "repeat\n" * 50
        diff = construct_output_diff(expected, actual)
        self.assertEqual(diff, " repeat\n" * 150 + "-missing\n" + " repeat\n" * 50)

    def test_completely_missing_or_extra_output_shows_every_line(self):
        self.assertEqual(construct_output_diff("first\nlast\n", ""), "-first\n-last\n")
        self.assertEqual(construct_output_diff("", "first\nlast\n"), "+first\n+last\n")

    def test_empty_stages_and_error_feedback(self):
        self.assertEqual(construct_stage_feedback(), [])
        body = construct_feedback(("OJ config not found", "Contact admins."))
        self.assertTrue(body.startswith("## MiniOJ feedback\n"))
        self.assertIn("### OJ config not found\n\nContact admins.", body)
