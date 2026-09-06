"""HF ``Aramente/eu-tech-jobs`` -> observations.

Tages-Snapshot aktiver EU-Tech-Stellen. Im gespeicherten Snapshot ist **keine
einzige** Gehaltsangabe gefuellt - die Zeilen kommen trotzdem mit, weil sie
Titel, Ort, Seniority und Rollenfamilie liefern und damit die Titelabdeckung
stuetzen. Fuer die Gehaltsauswertung fallen sie mangels Betrag automatisch raus.
"""
from __future__ import annotations

import pandas as pd

from salarykit import paths, schema
from salarykit.money import FxTable, annualize_series, convert_series
from salarykit.sources._common import (attach_titles, coalesce, resolve_locations,
                                       stable_id)

SOURCE = "hf_eu_tech_jobs"
DATASET = "HF Aramente/eu-tech-jobs (latest snapshot)"
LICENSE = "CC-BY-4.0"

COLUMNS = ["id", "company_slug", "title", "location", "countries", "remote_policy",
           "seniority", "salary_min", "salary_max", "salary_currency",
           "salary_period", "posted_at", "scraped_at", "source"]

SENIORITY = {"intern": "intern", "junior": "junior", "mid": "mid",
             "senior": "senior", "staff": "staff", "principal": "principal",
             "exec": "executive"}
REMOTE = {"onsite": "onsite", "hybrid": "hybrid", "remote": "remote",
          "remote-eu": "remote", "remote-global": "remote"}


def load(fx: FxTable, predictor) -> pd.DataFrame:
    path = paths.RAW_HF / "eu_tech_jobs" / "jobs.parquet"
    if not path.exists():
        return pd.DataFrame()

    df = pd.read_parquet(path, columns=COLUMNS)
    df = attach_titles(df, "title", predictor)

    first_country = df.countries.map(
        lambda v: v[0] if isinstance(v, (list, tuple)) and len(v) else None)
    first_country = pd.Series(first_country, index=df.index, dtype="string")
    first_country = first_country.where(first_country != "XX")

    observed = pd.to_datetime(df.posted_at, errors="coerce", utc=True).fillna(
        pd.to_datetime(df.scraped_at, errors="coerce", utc=True))

    out = pd.DataFrame(index=df.index)
    out["obs_id"] = df.id.map(lambda v: stable_id(SOURCE, v))
    out["source"] = SOURCE
    out["source_dataset"] = DATASET
    out["record_type"] = "job_posting"
    out["license"] = LICENSE
    out["year"] = observed.dt.year
    out["observed_at"] = observed.dt.tz_localize(None)

    out["job_title"] = df.title.astype("string")
    for col in ("job_title_clean", "job_title_core", "normalized_job_title",
                "normalized_job_code", "job_family", "norm_method",
                "norm_confidence", "isco08", "soc2018", "kldb2010"):
        out[col] = df[col]

    field_seniority = df.seniority.astype("string").map(SENIORITY)
    out["seniority"] = coalesce(field_seniority, df.title_seniority)
    out["seniority_source"] = "none"
    out.loc[df.title_seniority.notna(), "seniority_source"] = "title"
    out.loc[field_seniority.notna(), "seniority_source"] = "source_field"
    out["employment_type"] = df.title_employment_type
    out["remote_type"] = coalesce(df.remote_policy.astype("string").map(REMOTE),
                                  df.title_remote_type)

    places = resolve_locations(df.location.astype("string"), first_country)
    out["location_raw"] = df.location.astype("string")
    out["country_iso2"] = coalesce(first_country, places.country_iso2,
                                   df.title_country_iso2)
    out["country_name"] = places.country_name
    out["region"] = coalesce(places.region, df.title_region)
    out["city"] = coalesce(places.city, df.title_city)
    has_source_location = (df.location.astype("string").fillna("") != "") | first_country.notna()
    has_title_location = (df.title_country_iso2.notna() | df.title_region.notna() |
                          df.title_city.notna())
    out["location_source"] = "none"
    out.loc[has_title_location, "location_source"] = "title"
    out.loc[has_source_location, "location_source"] = "source_field"

    lo = pd.to_numeric(df.salary_min, errors="coerce")
    hi = pd.to_numeric(df.salary_max, errors="coerce")
    point = (lo + hi) / 2
    point = point.where(point.notna(), lo.where(lo.notna(), hi))
    out["salary_min_raw"] = lo
    out["salary_max_raw"] = hi
    out["salary_raw"] = point
    out["salary_currency"] = df.salary_currency.astype("string")
    out["salary_period"] = df.salary_period.astype("string")
    out["salary_basis"] = (lo.notna() & hi.notna()).map(
        {True: "range_mid", False: "point"}).where(point.notna())
    out["salary_annual_local"] = annualize_series(point, df.salary_period)
    converted = convert_series(out["salary_annual_local"], out["salary_currency"],
                               out["year"], fx)
    for col in converted.columns:
        out[col] = converted[col]

    out["company_name"] = df.company_slug.astype("string")
    out["weight"] = 1.0
    return schema.conform_observations(out)
