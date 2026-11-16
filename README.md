# MiniOJ

MiniOJ reads an exercise configuration, runs its stages, and returns the captured
exit statuses, stdout, and stderr as Markdown. It does not access GitHub or need
a repository, PR number, or token.

## Install and run

Python 3.10 or newer is required. Install the PyPI release:

```sh
python -m pip install minioj==0.3.0
minioj --config .minioj --comment '@minioj-bot run w1/ex1' --output feedback.md
```

Omit `--output` to write the Markdown to stdout instead. `-o` is the short form.
The output file is UTF-8; its parent directory must already exist. The same
option saves configuration and execution error feedback. A file write error is
reported on stderr and returns exit status 1.

`python -m minioj` and `python main.py` accept the same arguments. `--config`
defaults to `.minioj/`. For development, install this checkout with
`python -m pip install -e .`.

Exit status 0 means the run produced feedback, including feedback about failed
cases or missing/invalid exercise configuration. An invalid triggering comment
or an execution infrastructure error produces error Markdown and exit status 1.
Argument syntax errors return status 2. Case verdicts appear in the Markdown;
the CLI status is not an aggregate pass/fail result.

MiniOJ does not accept `--repo`, `--pull-request`, or `--token`. Publishing feedback
belongs to the caller, for example a separate GitHub Actions job running
`gh pr comment "$PR_NUMBER" --body-file feedback.md`.

## Exercise configuration

Store each exercise at `.minioj/w<week>/ex<exercise>/conf.json`:

```json
{
  "name": "Week 1: Hello world",
  "stages": [
    {"name": "Compile", "command": "cc main.c -o solution"},
    {"name": "Run", "command": "./solution", "cased": true}
  ]
}
```

An exercise name defaults to `w<week>/ex<exercise>`, and stage names default to
`Stage <index>` starting at zero. As in the original format, stage entries without
a string `command` are skipped. Only the JSON boolean `true` enables `cased`.

Commands support quoted arguments and run directly without a shell. Pipes,
redirection, and shell variable expansion require explicitly invoking a shell
(for example, `sh -c 'echo hello > output.txt'`). Run MiniOJ from the submission
directory: all stages inherit that working directory and run in config order,
including stages after a nonzero exit status.

A stage normally runs once with closed standard input. A `cased` stage runs once
for each `case<number>.in` file in the exercise directory, in numeric order. Each
file supplies stdin, and its matching `case<number>.out` supplies expected stdout
(for example, `case2.in` pairs with `case2.out`). Feedback numbers the cases from
zero and shows matching stdout as plain text. When output differs, the `stdout`
block shows the complete output with diff highlighting: `-` lines are missing or
replaced expected output, `+` lines are extra or replacement actual output, and
unchanged lines appear once with a space prefix. No lines are omitted, and no
filename or line-number headers are shown. Whitespace and trailing newlines
matter. If the expected file is missing,
feedback marks comparison as unavailable and shows the raw stdout instead.
Process exit status and stderr are reported independently of the comparison.
Each case's heading includes `Passed` or `Failed` above its details block. Passing
requires a zero exit status and matching expected output; missing expected output
counts as a failure.

Configuration commands execute with the permissions of the MiniOJ process. Use
a separate sandbox when running submissions that you do not trust; this project
does not implement execution isolation or resource limits.

## Project layout

| Module | Responsibility |
| --- | --- |
| `minioj/models.py` | Exercise IDs, exercise and stage definitions, command and stage results |
| `minioj/config.py` | JSON loading, defaults, and configuration errors |
| `minioj/runner.py` | Case discovery and subprocess execution |
| `minioj/feedback.py` | Markdown feedback and full output diffs |
| `minioj/judge.py` | Run one configured exercise and return Markdown |
| `minioj/cli.py` | Arguments, stdout, and optional output file |

The data models are immutable dataclasses. Config parsing produces `Exercise`
and `Stage` objects; execution produces `StageResult` objects containing
`CommandResult` objects. Feedback formatting consumes those results without
performing network or process I/O.

The Python API also returns Markdown:

```python
from pathlib import Path
from minioj.judge import judge
from minioj.models import ExerciseId

markdown = judge(Path('.minioj'), ExerciseId(1, 1))
```

## Package for PyPI

```sh
python -m pip install build
python -m build
```

This produces the wheel and source distribution in `dist/`. The package has no
third-party runtime dependencies. Publish the 0.3.0 artifacts before enabling a
consumer pinned to that version; building a wheel locally does not publish it.

## Tests

```sh
python -m unittest discover -s tests -v
```

Tests use temporary exercise directories and local subprocesses. They cover
stdout and file output, configuration errors, and offline use of the CLI.

## License

MIT. See [LICENSE](LICENSE).
