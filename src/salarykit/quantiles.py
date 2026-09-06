"""Empirische Gehaltsquantile aus den vereinheitlichten Beobachtungen.

Die Rohzeilen bleiben immer erhalten. Fuer Quantile werden nur positive,
plausible Jahresgehaelter mit bekanntem Taxonomie-Code verwendet. Eine Zeile
bekommt die spezifischste ausreichend grosse Vergleichsgruppe; kleine Gruppen
fallen schrittweise auf Land/Jahr beziehungsweise nur den Jobtitel zurueck.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from salarykit import schema

MIN_ANNUAL_EUR = 1_000.0
MAX_ANNUAL_EUR = 2_000_000.0


@dataclass(frozen=True)
class GroupSpec:
    name: str
    columns: tuple[str, ...]
    min_n: int


def group_specs(min_group_size: int = 10) -> list[GroupSpec]:
    """Vergleichsgruppen, von spezifisch nach allgemein."""
    return [
        GroupSpec("title_country_year_seniority",
                  ("normalized_job_code", "country_iso2", "year", "seniority"),
                  min_group_size),
        GroupSpec("title_country_year",
                  ("normalized_job_code", "country_iso2", "year"), min_group_size),
        GroupSpec("title_country", ("normalized_job_code", "country_iso2"),
                  max(20, min_group_size)),
        GroupSpec("title_year", ("normalized_job_code", "year"),
                  max(20, min_group_size)),
        GroupSpec("title", ("normalized_job_code",), max(30, min_group_size)),
    ]


def eligible_mask(observations: pd.DataFrame,
                  min_annual_eur: float = MIN_ANNUAL_EUR,
                  max_annual_eur: float = MAX_ANNUAL_EUR) -> pd.Series:
    salary = pd.to_numeric(observations["salary_annual_eur"], errors="coerce")
    code = observations["normalized_job_code"].astype("string")
    return (salary.between(min_annual_eur, max_annual_eur, inclusive="both") &
            code.notna() & (code != "") & (code != "other.unknown"))


def _complete_rows(df: pd.DataFrame, columns: tuple[str, ...]) -> pd.Series:
    mask = pd.Series(True, index=df.index)
    for col in columns:
        values = df[col]
        mask &= values.notna()
        if isinstance(values.dtype, pd.StringDtype):
            mask &= values != ""
    return mask


def attach_salary_quantiles(observations: pd.DataFrame, *,
                            min_group_size: int = 10,
                            min_annual_eur: float = MIN_ANNUAL_EUR,
                            max_annual_eur: float = MAX_ANNUAL_EUR
                            ) -> pd.DataFrame:
    """Empirischen Rang 0..1 an jede auswertbare Beobachtung haengen."""
    out = observations.copy()
    out["salary_quantile"] = pd.Series(pd.NA, index=out.index, dtype="Float32")
    out["salary_quantile_group"] = pd.Series(pd.NA, index=out.index, dtype="string")
    out["salary_quantile_n"] = pd.Series(pd.NA, index=out.index, dtype="Int32")
    eligible = eligible_mask(out, min_annual_eur, max_annual_eur)
    unassigned = eligible.copy()

    for spec in group_specs(min_group_size):
        candidates = unassigned & _complete_rows(out, spec.columns)
        if not candidates.any():
            continue
        frame = out.loc[candidates, [*spec.columns, "salary_annual_eur"]]
        grouped = frame.groupby(list(spec.columns), dropna=False, observed=True)
        counts = grouped["salary_annual_eur"].transform("size")
        accepted = counts >= spec.min_n
        if not accepted.any():
            continue
        ranks = grouped["salary_annual_eur"].rank(method="average")
        # Mittelpunkt-Rang: auch Minimum/Maximum bleiben innerhalb (0, 1).
        percentiles = (ranks - 0.5) / counts
        idx = frame.index[accepted]
        out.loc[idx, "salary_quantile"] = percentiles.loc[idx].astype("float32")
        out.loc[idx, "salary_quantile_group"] = spec.name
        out.loc[idx, "salary_quantile_n"] = counts.loc[idx].astype("int32")
        unassigned.loc[idx] = False

    return schema.conform_observations(out)


def _key_part(value) -> str:
    if value is None or pd.isna(value):
        return "*"
    return str(value).replace("|", "/")


def build_quantile_table(observations: pd.DataFrame, *,
                         min_group_size: int = 10,
                         min_annual_eur: float = MIN_ANNUAL_EUR,
                         max_annual_eur: float = MAX_ANNUAL_EUR
                         ) -> pd.DataFrame:
    """Eine kompakte Quantiltabelle fuer alle belastbaren Gruppen bauen."""
    eligible = observations.loc[
        eligible_mask(observations, min_annual_eur, max_annual_eur)
    ].copy()
    if eligible.empty:
        return schema.conform_quantiles(pd.DataFrame())

    frames: list[pd.DataFrame] = []
    quantile_names = {0.10: "p10_annual_eur", 0.25: "p25_annual_eur",
                      0.50: "p50_annual_eur", 0.75: "p75_annual_eur",
                      0.90: "p90_annual_eur"}
    for spec in group_specs(min_group_size):
        data = eligible.loc[_complete_rows(eligible, spec.columns)]
        if data.empty:
            continue
        grouped = data.groupby(list(spec.columns), dropna=False, observed=True,
                               sort=False)
        sizes = grouped.size().rename("n")
        keep = sizes[sizes >= spec.min_n].index
        if len(keep) == 0:
            continue
        summary = grouped["salary_annual_eur"].agg(
            mean_annual_eur="mean").join(sizes)
        qs = grouped["salary_annual_eur"].quantile(list(quantile_names)).unstack()
        qs = qs.rename(columns=quantile_names)
        usd50 = grouped["salary_annual_usd"].quantile(0.5).rename("p50_annual_usd")
        n_sources = grouped["source"].nunique().rename("n_sources")
        sources = grouped["source"].agg(
            lambda s: "|".join(sorted(set(str(v) for v in s.dropna())))).rename("sources")
        summary = summary.join([qs, usd50, n_sources, sources]).loc[keep].reset_index()
        summary["grouping"] = spec.name
        summary["group_key"] = summary.apply(
            lambda row: "|".join([spec.name] + [_key_part(row[c]) for c in spec.columns]),
            axis=1)
        frames.append(summary)

    if not frames:
        return schema.conform_quantiles(pd.DataFrame())
    out = pd.concat(frames, ignore_index=True)
    lookup = observations[["normalized_job_code", "normalized_job_title",
                           "job_family"]].drop_duplicates("normalized_job_code")
    out = out.merge(lookup, on="normalized_job_code", how="left")
    return schema.conform_quantiles(out)
