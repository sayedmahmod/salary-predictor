"""Stellen-Atlas: deutsche BA-Anzeigen mit konservativ validierten Gehaeltern.

Im Snapshot sind viele Monats- oder Stundenbetraege irrtuemlich als ``year``
markiert. Ein Jahreswert wird deshalb nur akzeptiert, wenn der bereits
annualisierte Mittelpunkt im plausiblen Bereich liegt. Die verworfenen
Anzeigen bleiben in der Rohdatei und koennen spaeter neu geparst werden.
"""
from __future__ import annotations

import pandas as pd

from salarykit import paths, schema
from salarykit.money import FxTable, annualize_series
from salarykit.sources._common import attach_titles, stable_id

SOURCE = "hf_german_job_postings"
DATASET = "mischeiwiller/german-job-postings (salary subset)"
LICENSE = "CC-BY-4.0"


def _range_part(value, key):
    return value.get(key) if isinstance(value, dict) else None


def load(fx: FxTable, predictor) -> pd.DataFrame:
    path = paths.RAW_HF / "german_job_postings" / "german-job-postings.parquet"
    if not path.exists():
        return pd.DataFrame()
    df = pd.read_parquet(path)
    df = df[df["salary_range"].notna()].copy()
    if df.empty:
        return pd.DataFrame()

    for col in ("min_eur", "max_eur", "period"):
        df[col] = df["salary_range"].map(lambda value, c=col: _range_part(value, c))
    df["min_eur"] = pd.to_numeric(df["min_eur"], errors="coerce")
    df["max_eur"] = pd.to_numeric(df["max_eur"], errors="coerce")
    df["salary_mid"] = df[["min_eur", "max_eur"]].mean(axis=1)
    df["annual_eur"] = annualize_series(df["salary_mid"], df["period"])
    # Die allgemeine Trainingseignung liegt bei 1k..2m. Hier strenger: ein
    # Vollzeit-Jahresgehalt unter 10k ist fast immer eine falsch erkannte
    # Monats-/Stundenangabe; darueber bleiben 351 nachvollziehbare Zeilen.
    df = df[df["annual_eur"].between(10_000, 2_000_000)].copy()
    if df.empty:
        return pd.DataFrame()
    df = attach_titles(df, "title", predictor)

    dates = pd.to_datetime(df["posted_date"], errors="coerce", utc=True).dt.tz_localize(None)
    out = pd.DataFrame(index=df.index)
    out["obs_id"] = df["id"].map(lambda value: stable_id(SOURCE, value))
    out["source"] = SOURCE
    out["source_dataset"] = DATASET
    out["record_type"] = "job_posting"
    out["license"] = LICENSE
    out["year"] = dates.dt.year
    out["observed_at"] = dates
    out["job_title"] = df["title"]
    for col in ("job_title_clean", "job_title_core", "normalized_job_title",
                "normalized_job_code", "job_family", "norm_method",
                "norm_confidence", "isco08", "soc2018", "kldb2010"):
        out[col] = df[col]
    sourced_seniority = df["seniority"].astype("string").str.lower().replace(
        {"unknown": pd.NA, "middle": "mid"})
    out["seniority"] = sourced_seniority.fillna(df["title_seniority"])
    out["seniority_source"] = sourced_seniority.notna().map(
        {True: "source_field", False: "title"})
    out["employment_type"] = df["title_employment_type"]
    out["remote_type"] = df["title_remote_type"]
    out["location_raw"] = df["region"]
    out["country_iso2"] = "DE"
    out["country_name"] = "Germany"
    out["region"] = df["region"]
    out["location_source"] = "source_field"
    out["salary_min_raw"] = df["min_eur"]
    out["salary_max_raw"] = df["max_eur"]
    out["salary_raw"] = df["salary_mid"]
    out["salary_currency"] = "EUR"
    out["salary_period"] = df["period"]
    out["salary_basis"] = "range_mid"
    out["salary_annual_local"] = df["annual_eur"]
    out["salary_annual_eur"] = df["annual_eur"]
    usd_per_eur = out["year"].map(lambda year: fx.usd_per_eur(int(year)))
    out["salary_annual_usd"] = out["salary_annual_eur"] * usd_per_eur
    out["fx_rate_usd_per_unit"] = usd_per_eur
    out["fx_source"] = "identity"
    out["company_name"] = df["employer"]
    # Kleine, bewusst gesetzte Vertrauensgewichtung: Die Gehaelter wurden aus
    # Anzeigentiteln extrahiert und nicht in einem strukturierten Feld gemeldet.
    out["weight"] = 0.25
    return schema.conform_observations(out)
