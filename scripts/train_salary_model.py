#!/usr/bin/env python3
"""Trainiert die fuenf Gehalts-Quantilmodelle aus observations.parquet."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pandas as pd  # noqa: E402

from salarykit import paths  # noqa: E402
from salarykit.money import FxTable, build_fx_table  # noqa: E402
from salarykit.salary.model import (MODEL_FILENAME, TITLE_EMBEDDING_DIMS,  # noqa: E402
                                    SalaryModel, write_report)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--observations", type=Path,
                        default=paths.PROCESSED / "observations.parquet")
    parser.add_argument("--output", type=Path,
                        default=paths.MODELS / MODEL_FILENAME)
    parser.add_argument("--test-size", type=float, default=0.20)
    parser.add_argument("--aggregates", type=Path,
                        default=paths.PROCESSED / "aggregates.parquet",
                        help="Amtliche Aggregate als Prior; fehlt die Datei, "
                             "trainiert das Modell ohne sie.")
    parser.add_argument("--max-iter", type=int, default=400)
    parser.add_argument("--learning-rate", type=float, default=0.05)
    parser.add_argument("--max-leaf-nodes", type=int, default=63)
    parser.add_argument("--title-dims", type=int, default=TITLE_EMBEDDING_DIMS)
    parser.add_argument("--seed", type=int, default=13)
    args = parser.parse_args(argv)
    if not args.observations.exists():
        raise FileNotFoundError(
            f"{args.observations} fehlt. Erst scripts/build_dataset.py ausfuehren."
        )
    observations = pd.read_parquet(args.observations)
    aggregates = (pd.read_parquet(args.aggregates) if args.aggregates.exists()
                  else None)
    fx_path = args.observations.parent / "fx_rates.json"
    fx = FxTable.load(fx_path) if fx_path.exists() else build_fx_table()
    max_year = pd.to_numeric(observations.year, errors="coerce").max()
    usd_per_eur = fx.usd_per_eur(int(max_year) if pd.notna(max_year) else None)
    print(f"Trainiere auf {len(observations):,} vereinheitlichten Zeilen ...", flush=True)
    if aggregates is not None:
        print(f"  amtliche Aggregate als Prior: {len(aggregates):,} Zeilen", flush=True)
    model, report = SalaryModel.train(
        observations, aggregates=aggregates, test_size=args.test_size,
        random_state=args.seed, max_iter=args.max_iter,
        learning_rate=args.learning_rate, max_leaf_nodes=args.max_leaf_nodes,
        title_dims=args.title_dims, usd_per_eur=usd_per_eur,
    )
    model.save(args.output)
    report_path = paths.REPORTS / "salary_model.json"
    write_report(report, report_path)
    print(json.dumps(report.to_dict(), indent=2, ensure_ascii=False))
    print(f"Modell: {args.output}\nBericht: {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
