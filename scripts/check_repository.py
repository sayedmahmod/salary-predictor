#!/usr/bin/env python3
"""Fail when files unsuitable for a public repository are tracked."""
from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN_PREFIXES = ("data/raw/", "data/interim/", "data/processed/")
FORBIDDEN_SUFFIXES = (".parquet", ".feather", ".xlsx", ".xls")
# Reports that quote raw source text, as opposed to reporting aggregate metrics.
FORBIDDEN_FILES = ("reports/title_coverage.json",)
MAX_BYTES = 10 * 1024 * 1024
# Die trainierten Modelle sind absichtlich versioniert und deutlich groesser.
# GitHub weist ab 50 MiB pro Datei einen Warnhinweis aus und lehnt ab 100 MiB ab.
MODEL_PREFIX = "models/"
MODEL_MAX_BYTES = 90 * 1024 * 1024


def tracked_files() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files", "-z"], cwd=ROOT, check=True,
        stdout=subprocess.PIPE,
    )
    return [name for name in result.stdout.decode().split("\0") if name]


def main() -> int:
    problems = []
    files = tracked_files()
    for name in files:
        path = ROOT / name
        if name.startswith("._") or "/._" in name:
            problems.append(f"macOS AppleDouble-Datei: {name}")
        if name.startswith(FORBIDDEN_PREFIXES):
            problems.append(f"Datenartefakt: {name}")
        if path.suffix.lower() in FORBIDDEN_SUFFIXES:
            problems.append(f"binaeres Datenformat: {name}")
        if name in FORBIDDEN_FILES:
            problems.append(f"Report mit Original-Quelltext: {name}")
        if path.is_file():
            limit = (MODEL_MAX_BYTES if name.startswith(MODEL_PREFIX)
                     else MAX_BYTES)
            if path.stat().st_size > limit:
                problems.append(
                    f"groesser als {limit // (1024 * 1024)} MiB: {name}")
    if problems:
        print("Repository-Check fehlgeschlagen:")
        for problem in problems:
            print(f"- {problem}")
        return 1
    print(f"Repository-Check bestanden ({len(files)} Dateien).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
