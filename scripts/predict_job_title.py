#!/usr/bin/env python3
"""Projektlokaler Einstiegspunkt fuer die Jobtitel-CLI."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from salarykit.titles.cli import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
