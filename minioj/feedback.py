"""Render model objects as Markdown without performing I/O."""

from .models import CommandResult, StageResult


def construct_feedback(*sections: tuple[str, str], append_title: str = "") -> str:
    body = "## MiniOJ feedback"
    if append_title:
        body += f" - {append_title}"
    body += "\n\nMade with :heart: by FTC Team FFFabulous 19726.\n\n"
    for title, section_body in sections:
        body += f"### {title}\n\n{section_body}\n\n"
    return body


def construct_result_feedback(result: CommandResult) -> str:
    return (
        f"Status: {result.returncode}\n\n"
        f"<details><summary>Details:</summary>\n\n"
        f"`stdout`:\n\n```\n{result.stdout}\n```\n\n"
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
        sections.append((result.stage.name, body))
    return sections
