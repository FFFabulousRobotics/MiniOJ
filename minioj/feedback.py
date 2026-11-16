"""Render model objects as Markdown without performing I/O."""

from difflib import unified_diff
from pathlib import Path

from .models import CommandResult, StageResult


def construct_feedback(*sections: tuple[str, str], append_title: str = "") -> str:
    body = "## MiniOJ feedback"
    if append_title:
        body += f" - {append_title}"
    body += "\n\nMade with :heart: by FTC Team FFFabulous 19726.\n\n"
    for title, section_body in sections:
        body += f"### {title}\n\n{section_body}\n\n"
    return body


def construct_output_diff(expected: str, actual: str, expected_name: str) -> str:
    lines = unified_diff(
        expected.splitlines(keepends=True),
        actual.splitlines(keepends=True),
        fromfile=expected_name,
        tofile="stdout",
    )
    # difflib leaves unterminated lines as-is; separate them and mark the missing
    # newline just as diff -u does, so a trailing-newline mismatch is visible.
    return "".join(
        line if line.endswith("\n") else f"{line}\n\\ No newline at end of file\n"
        for line in lines
    )


def construct_result_feedback(result: CommandResult) -> str:
    stdout = result.stdout
    language = ""
    note = ""
    if result.case_name is not None:
        expected_name = Path(result.case_name).with_suffix(".out").name
        if result.expected_stdout is None:
            note = (
                f"Expected output missing: `{expected_name}`. "
                "Comparison unavailable.\n\n"
            )
        else:
            language = "diff"
            stdout = construct_output_diff(
                result.expected_stdout, result.stdout, expected_name
            ) or "No differences."
    return (
        f"Status: {result.returncode}\n\n"
        f"<details><summary>Details:</summary>\n\n"
        f"`stdout`:\n\n{note}```{language}\n{stdout}\n```\n\n"
        f"`stderr`: \n\n```\n{result.stderr}\n```\n\n"
        f"</details>\n\n"
    )


def construct_stage_feedback(*stages: StageResult) -> list[tuple[str, str]]:
    sections = []
    for result in stages:
        body = ""
        for index, command in enumerate(result.commands):
            if result.stage.cased:
                body += f"**Case {index}:**\n\n"
            body += construct_result_feedback(command)
            if result.stage.cased:
                passed = command.returncode == 0 and command.output_matches is True
                verdict = "Passed!" if passed else "Failed..."
                body += f"{verdict}\n\n"
        sections.append((result.stage.name, body))
    return sections
