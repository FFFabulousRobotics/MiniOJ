# MiniOJ

MiniOJ reads an exercise configuration, runs its stages, and posts the captured
exit statuses, stdout, and stderr to a GitHub pull request.

## Install and run

Python 3.10 or newer is required. From this checkout:

```sh
python -m pip install -e .
minioj --repo owner/repository --pull-request 123 \
  --comment '@minioj-bot run w1/ex1' --token "$GITHUB_TOKEN"
```

`python -m minioj` and `python main.py` accept the same arguments. `--config`
defaults to `.minioj/`. When `--repo` is omitted, MiniOJ uses the first Git remote
in the current working directory.

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
zero and shows a unified diff in each case's `stdout` block: `-` lines are expected
output and `+` lines are actual output. Matching output displays `No differences.`
Whitespace and trailing newlines matter. If the expected file is missing,
feedback marks comparison as unavailable and shows the raw stdout instead.
Process exit status and stderr are reported independently of the comparison.
Each case ends with `Passed!` or `Failed...` outside its details block. Passing
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
| `minioj/feedback.py` | Markdown feedback and unified output diffs |
| `minioj/github.py` | Repository discovery and GitHub comments |
| `minioj/cli.py` | Arguments and orchestration |

The data models are immutable dataclasses. Config parsing produces `Exercise`
and `Stage` objects; execution produces `StageResult` objects containing
`CommandResult` objects. Feedback formatting consumes those results without
performing network or process I/O.

## Tests

```sh
python -m unittest discover -s tests -v
```

Tests use temporary exercise directories and local subprocesses. GitHub requests
are mocked; running the test suite does not publish comments.

## License

MIT. See [LICENSE](LICENSE).
