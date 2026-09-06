"""Kommandozeile fuer die Jobtitel-Normalisierung."""
from __future__ import annotations

import argparse
import json
import sys

from salarykit.titles.predict import JobTitlePredictor


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Jobtitel bereinigen und auf die salarykit-Taxonomie klassifizieren")
    parser.add_argument("titles", nargs="*", help="Jobtitel; ohne Argumente wird stdin gelesen")
    parser.add_argument("--no-model", action="store_true", help="Nur deterministische Regeln")
    parser.add_argument("--pretty", action="store_true", help="Eingeruecktes JSON statt JSONL")
    args = parser.parse_args(argv)
    titles = args.titles or [line.strip() for line in sys.stdin if line.strip()]
    predictor = JobTitlePredictor(use_model=not args.no_model)
    rows = [prediction.to_dict() for prediction in predictor.predict_many(titles)]
    if args.pretty:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
    else:
        for row in rows:
            print(json.dumps(row, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
