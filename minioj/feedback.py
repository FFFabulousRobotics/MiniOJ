"""Render model objects as Markdown without performing I/O."""

from difflib import SequenceMatcher
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


def construct_output_diff(expected: str, actual: str) -> str:
    if expected == actual:
        return ""
    expected_lines = expected.splitlines(keepends=True)
    actual_lines = actual.splitlines(keepends=True)
    # Keep every matching line, including repeated lines in long outputs.
    matcher = SequenceMatcher(None, expected_lines, actual_lines, autojunk=False)
    lines = []
    for (
        tag,
        expected_start,
        expected_end,
        actual_start,
        actual_end,
    ) in matcher.get_opcodes():
        if tag == "equal":
            lines.extend(
                " " + line for line in expected_lines[expected_start:expected_end]
            )
        if tag in ("delete", "replace"):
            lines.extend(
                "-" + line for line in expected_lines[expected_start:expected_end]
            )
        if tag in ("insert", "replace"):
            lines.extend("+" + line for line in actual_lines[actual_start:actual_end])
    # Separate unterminated lines and mark the missing newline just as diff -u
    # does, so a trailing-newline mismatch is visible.
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
        elif not result.output_matches:
            language = "diff"
            stdout = construct_output_diff(result.expected_stdout, result.stdout)
    return (
        f"<details><summary>Details</summary>\n\n"
        f"Exit status: `{result.returncode}`\n\n"
        f"File `stdout`:\n\n{note}```{language}\n{stdout}\n```\n\n"
        f"File `stderr`: \n\n```\n{result.stderr}\n```\n\n"
        f"</details>\n\n"
    )


def construct_stage_feedback(*stages: StageResult) -> list[tuple[str, str]]:
    sections = []
    for result in stages:
        body = ""
        for index, command in enumerate(result.commands):
            if result.stage.cased:
                passed = command.returncode == 0 and command.output_matches is True
                verdict = "Passed" if passed else "Failed"
                body += f"#### Case {index} - {verdict}\n\n"
            body += construct_result_feedback(command)
        sections.append((result.stage.name, body))
    return sections
