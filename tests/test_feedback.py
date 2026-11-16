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
            "Status: 1\n\n"
            "<details><summary>Details:</summary>\n\n"
            "`stdout`:\n\n```\nout\n```\n\n"
            "`stderr`: \n\n```\nerr\n```\n\n"
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
        self.assertIn("**Case 0:**\n\nStatus: 0", body)
        self.assertIn("**Case 1:**\n\nStatus: 2", body)
        self.assertIn("```diff\n--- case1.out\n+++ stdout\n@@ -1 +1 @@", body)
        self.assertIn("```diff\n--- case2.out\n+++ stdout\n@@ -1 +1 @@", body)
        self.assertIn("-expected first\n+first\n", body)
        self.assertIn("`stderr`: \n\n```\nerror\n```", body)
        self.assertLess(body.index("first"), body.index("second"))
        cases = body.split("**Case ")[1:]
        self.assertEqual(len(cases), 5)
        for case, verdict in zip(cases, (
            "Failed...", "Failed...", "Passed!", "Failed...", "Failed...",
        )):
            with self.subTest(case=case.splitlines()[0]):
                self.assertTrue(case.endswith(f"</details>\n\n{verdict}\n\n"))

    def test_matching_outputs_including_empty_output_show_no_differences(self):
        for stdout in ("", "same\n"):
            with self.subTest(stdout=stdout):
                result = CommandResult(0, stdout, "", "case1.in", stdout)
                body = construct_result_feedback(result)
                self.assertIn("`stdout`:\n\n```diff\nNo differences.\n```", body)
                self.assertIs(result.output_matches, True)

    def test_missing_expected_output_is_explicit_and_retains_raw_stdout(self):
        body = construct_result_feedback(CommandResult(0, "actual", "", "case1.in"))
        self.assertIn("Expected output missing: `case1.out`.", body)
        self.assertIn("Comparison unavailable.", body)
        self.assertIn("```\nactual\n```", body)
        self.assertNotIn("No differences.", body)

    def test_unified_diff_shows_context_whitespace_and_missing_newlines(self):
        diff = construct_output_diff("before\nexpected\nafter\n", "before\nactual\nafter\n", "case1.out")
        self.assertEqual(diff, (
            "--- case1.out\n+++ stdout\n@@ -1,3 +1,3 @@\n"
            " before\n-expected\n+actual\n after\n"
        ))
        for expected, actual, tail in (
            ("same\n", "same", "-same\n+same\n\\ No newline at end of file\n"),
            ("same", "same\n", "-same\n\\ No newline at end of file\n+same\n"),
            ("same \n", "same\n", "-same \n+same\n"),
        ):
            with self.subTest(expected=expected, actual=actual):
                diff = construct_output_diff(expected, actual, "case1.out")
                self.assertEqual(diff, "--- case1.out\n+++ stdout\n@@ -1 +1 @@\n" + tail)

    def test_empty_stages_and_error_feedback(self):
        self.assertEqual(construct_stage_feedback(), [])
        body = construct_feedback(("OJ config not found", "Contact admins."))
        self.assertTrue(body.startswith("## MiniOJ feedback\n"))
        self.assertIn("### OJ config not found\n\nContact admins.", body)
