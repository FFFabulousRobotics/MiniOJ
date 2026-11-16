"""Backward-compatible entry point for running MiniOJ from a checkout."""

from minioj.cli import main


if __name__ == "__main__":
    raise SystemExit(main())
