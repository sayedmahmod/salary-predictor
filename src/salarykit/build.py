"""Reproduzierbarer Build aller Rohquellen in das gemeinsame Schema."""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from salarykit import paths, schema
from salarykit.money import build_fx_table
from salarykit.quantiles import (MAX_ANNUAL_EUR, MIN_ANNUAL_EUR,
                                 attach_salary_quantiles, build_quantile_table)
from salarykit.sources import (aijobs, ba_entgelt, bls_oews, destatis_earnings,
                               eurostat_ses, hf_data_professions,
                               hf_eu_tech_jobs, hf_german_job_postings,
                               hf_tech_postings, it_salary_eu, stackoverflow,
                               stackoverflow_history)
from salarykit.titles.predict import JobTitlePredictor
from salarykit.titles.taxonomy import FAMILIES, ROLES

OBSERVATION_SOURCES = {
    module.SOURCE: module for module in
    (stackoverflow, stackoverflow_history, it_salary_eu, aijobs,
     hf_tech_postings, hf_eu_tech_jobs, hf_data_professions,
     hf_german_job_postings)
}
AGGREGATE_SOURCES = {
    module.SOURCE: module for module in
    (bls_oews, ba_entgelt, eurostat_ses, destatis_earnings)
}
ALL_SOURCES = {**OBSERVATION_SOURCES, **AGGREGATE_SOURCES}


@dataclass
class BuildResult:
    observations: pd.DataFrame
    aggregates: pd.DataFrame
    quantiles: pd.DataFrame
    manifest: dict


def _write_parquet_atomic(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    frame.to_parquet(temporary, index=False, compression="zstd")
    temporary.replace(path)


def _taxonomy_frame() -> pd.DataFrame:
    return pd.DataFrame([{
        "normalized_job_code": r.code,
        "normalized_job_title": r.label,
        "job_family": r.family,
        "job_family_label": FAMILIES.get(r.family, r.family),
        "isco08": r.isco08,
        "soc2018": r.soc2018,
        "kldb2010": r.kldb2010,
        "aliases": "|".join(r.aliases),
    } for r in ROLES])


def _validate(observations: pd.DataFrame, aggregates: pd.DataFrame,
              quantiles: pd.DataFrame) -> list[str]:
    errors: list[str] = []
    for name, frame, columns in (
        ("observations", observations, schema.OBSERVATION_ORDER),
        ("aggregates", aggregates, schema.AGGREGATE_ORDER),
        ("quantiles", quantiles, schema.QUANTILE_ORDER),
    ):
        if list(frame.columns) != columns:
            errors.append(f"{name}: Spalten entsprechen nicht dem Schema")
    if observations.obs_id.duplicated().any():
        errors.append("observations: obs_id ist nicht eindeutig")
    if not aggregates.empty and aggregates.agg_id.duplicated().any():
        errors.append("aggregates: agg_id ist nicht eindeutig")
    if not quantiles.empty and quantiles.group_key.duplicated().any():
        errors.append("quantiles: group_key ist nicht eindeutig")
    ranked = observations.salary_quantile.dropna()
    if not ranked.between(0, 1).all():
        errors.append("observations: salary_quantile ausserhalb 0..1")
    for _, row in quantiles.iterrows():
        values = [row[c] for c in ("p10_annual_eur", "p25_annual_eur",
                                   "p50_annual_eur", "p75_annual_eur",
                                   "p90_annual_eur") if pd.notna(row[c])]
        if values != sorted(values):
            errors.append(f"quantiles: nicht monotone Quantile in {row.group_key}")
            break
    return errors


def build(*, output_dir: str | Path | None = None,
          sources: list[str] | None = None, min_group_size: int = 10,
          write: bool = True) -> BuildResult:
    """Alle gewaehlten Quellen laden, normalisieren, pruefen und schreiben."""
    paths.ensure_dirs()
    selected = set(sources or ALL_SOURCES)
    unknown = selected - set(ALL_SOURCES)
    if unknown:
        raise ValueError(f"Unbekannte Quellen: {', '.join(sorted(unknown))}")

    fx = build_fx_table()
    predictor = JobTitlePredictor()
    observation_frames = [OBSERVATION_SOURCES[name].load(fx, predictor)
                          for name in OBSERVATION_SOURCES if name in selected]
    observation_frames = [f for f in observation_frames if not f.empty]
    observations = (schema.conform_observations(pd.concat(observation_frames,
                                                          ignore_index=True))
                    if observation_frames else schema.conform_observations(pd.DataFrame()))
    observations = attach_salary_quantiles(observations,
                                            min_group_size=min_group_size)

    aggregate_frames = [AGGREGATE_SOURCES[name].load(fx, predictor)
                        for name in AGGREGATE_SOURCES if name in selected]
    aggregate_frames = [f for f in aggregate_frames if not f.empty]
    aggregates = (schema.conform_aggregates(pd.concat(aggregate_frames,
                                                      ignore_index=True))
                  if aggregate_frames else schema.conform_aggregates(pd.DataFrame()))
    quantiles = build_quantile_table(observations,
                                     min_group_size=min_group_size)
    errors = _validate(observations, aggregates, quantiles)
    if errors:
        raise ValueError("Build-Validierung fehlgeschlagen:\n- " + "\n- ".join(errors))

    source_rows = {
        name: int((observations.source == name).sum() + (aggregates.source == name).sum())
        for name in selected
    }
    manifest = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "schema_version": "1.0",
        "selected_sources": sorted(selected),
        "source_rows": dict(sorted(source_rows.items())),
        "observations": int(len(observations)),
        "observations_with_salary_eur": int(observations.salary_annual_eur.notna().sum()),
        "observations_with_quantile": int(observations.salary_quantile.notna().sum()),
        "aggregates": int(len(aggregates)),
        "quantile_groups": int(len(quantiles)),
        "title_methods": {str(k): int(v) for k, v in
                          observations.norm_method.value_counts(dropna=False).items()},
        "salary_eligibility_eur": {"min": MIN_ANNUAL_EUR, "max": MAX_ANNUAL_EUR},
        "min_group_size": min_group_size,
        "model_loaded": predictor.has_model,
        "validation_errors": errors,
    }

    if write:
        target = Path(output_dir) if output_dir else paths.PROCESSED
        target.mkdir(parents=True, exist_ok=True)
        _write_parquet_atomic(observations, target / "observations.parquet")
        _write_parquet_atomic(aggregates, target / "aggregates.parquet")
        _write_parquet_atomic(quantiles, target / "quantiles.parquet")
        _write_parquet_atomic(_taxonomy_frame(), target / "job_title_taxonomy.parquet")
        fx.save(target / "fx_rates.json")
        (target / "manifest.json").write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False))
    return BuildResult(observations, aggregates, quantiles, manifest)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=paths.PROCESSED)
    parser.add_argument("--source", action="append", choices=sorted(ALL_SOURCES),
                        help="Quelle auswaehlen; mehrfach angebbar (Standard: alle)")
    parser.add_argument("--min-group-size", type=int, default=10)
    args = parser.parse_args(argv)
    result = build(output_dir=args.output_dir, sources=args.source,
                   min_group_size=args.min_group_size)
    print(json.dumps(result.manifest, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
