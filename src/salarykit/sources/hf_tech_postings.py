"""HF ``zalizedata/tech-job-postings-salary-dataset`` (Tier L) -> observations.

394k Stellenanzeigen von ATS-Endpunkten, davon 107k mit geparster Gehaltsspanne.
Lizenz CC BY-NC 4.0 - **nicht** kommerziell nutzbar; das steht in jeder Zeile
in ``license``, damit es beim Weiterverarbeiten nicht verloren geht.

Gehaelter kommen als Spanne mit eigener Periode (Stunde/Monat/Jahr). Als
Punktwert wird die Mitte der Spanne genommen (``salary_basis = range_mid``).
"""
from __future__ import annotations

import pandas as pd

from salarykit import paths, schema
from salarykit.money import FxTable, annualize_series, convert_series
from salarykit.sources._common import (attach_titles, coalesce, country_columns,
                                       resolve_locations, stable_id)

SOURCE = "hf_tech_postings"
DATASET = "HF zalizedata/tech-job-postings-salary-dataset (tier L)"
LICENSE = "CC-BY-NC-4.0 (nur nicht-kommerziell)"

COLUMNS = ["company_name", "company_industry", "job_id", "title", "location_raw",
           "country", "city", "is_remote", "employment_type", "salary_min",
           "salary_max", "salary_currency", "salary_period", "posted_at",
           "scraped_at", "url"]

EMPLOYMENT = {"full_time": "full_time", "part_time": "part_time",
              "contract": "contract", "internship": "internship",
              "temporary": "temporary", "freelance": "freelance"}


def load(fx: FxTable, predictor) -> pd.DataFrame:
    path = paths.RAW_HF / "tech_job_postings" / "jobs_L.parquet"
    if not path.exists():
        return pd.DataFrame()

    df = pd.read_parquet(path, columns=COLUMNS)
    df = df.astype({c: "string" for c in df.columns if df[c].dtype == "large_string[pyarrow]"},
                   errors="ignore")
    df = attach_titles(df, "title", predictor)

    posted = pd.to_datetime(df.posted_at, errors="coerce", utc=True, format="mixed")
    scraped = pd.to_datetime(df.scraped_at, errors="coerce", utc=True, format="mixed")
    observed = posted.fillna(scraped)

    out = pd.DataFrame(index=df.index)
    out["obs_id"] = [stable_id(SOURCE, j, i) for i, j in enumerate(df.job_id)]
    out["source"] = SOURCE
    out["source_dataset"] = DATASET
    out["record_type"] = "job_posting"
    out["license"] = LICENSE
    out["year"] = observed.dt.year
    out["observed_at"] = observed.dt.tz_localize(None)

    out["job_title"] = df.title
    for col in ("job_title_clean", "job_title_core", "normalized_job_title",
                "normalized_job_code", "job_family", "norm_method",
                "norm_confidence", "isco08", "soc2018", "kldb2010"):
        out[col] = df[col]

    out["seniority"] = df.title_seniority
    out["seniority_source"] = df.title_seniority.notna().map(
        {True: "title", False: "none"})
    out["employment_type"] = coalesce(
        df.employment_type.astype("string").map(EMPLOYMENT),
        df.title_employment_type)
    remote_field = df.is_remote.map({True: "remote", False: None})
    out["remote_type"] = coalesce(remote_field, df.title_remote_type)

    countries = country_columns(df.country)
    from_field = resolve_locations(df.location_raw.astype("string"),
                                   countries.country_iso2)
    out["location_raw"] = df.location_raw.astype("string")
    out["country_iso2"] = coalesce(countries.country_iso2, from_field.country_iso2,
                                   df.title_country_iso2)
    out["country_name"] = coalesce(countries.country_name, from_field.country_name)
    out["region"] = coalesce(from_field.region, df.title_region)
    out["city"] = coalesce(df.city.astype("string"), from_field.city, df.title_city)
    has_source_location = (df.country.notna() | df.location_raw.notna() |
                           df.city.notna())
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

    out["company_name"] = df.company_name.astype("string")
    out["industry"] = df.company_industry.astype("string")
    out["weight"] = 1.0
    return schema.conform_observations(out)
