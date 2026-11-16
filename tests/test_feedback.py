import unittest

from minioj.feedback import construct_feedback, construct_stage_feedback
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
            "`stdout`:\n\n```\nout\n```\n\n"
            "`stderr`: \n\n```\nerr\n```\n\n\n\n"
        ))

    def test_cased_results_have_independent_numbered_sections(self):
        result = StageResult(Stage("Run", "./solution", True), (
            CommandResult(0, "first", "", "case1.in"),
            CommandResult(2, "second", "error", "case2.in"),
        ))
        sections = construct_stage_feedback(result)
        self.assertEqual(sections[0][0], "Run")
        body = sections[0][1]
        self.assertIn("#### Case 0:\n\nStatus: 0", body)
        self.assertIn("#### Case 1:\n\nStatus: 2", body)
        self.assertLess(body.index("first"), body.index("second"))

    def test_empty_stages_and_error_feedback(self):
        self.assertEqual(construct_stage_feedback(), [])
        body = construct_feedback(("OJ config not found", "Contact admins."))
        self.assertTrue(body.startswith("## MiniOJ feedback\n"))
        self.assertIn("### OJ config not found\n\nContact admins.", body)
