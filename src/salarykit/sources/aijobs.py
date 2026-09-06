"""aijobs.net Salary Index -> observations.

Einzelne, anonym gemeldete AI/ML/Data-Gehaelter, 2020-2025, CC0. Die Quelle
liefert ``salary_in_usd`` bereits umgerechnet - der Wert wird uebernommen und
nicht neu berechnet, damit unsere Zahlen zur Quelle passen.
"""
from __future__ import annotations

import pandas as pd

from salarykit import paths, schema
from salarykit.money import FxTable
from salarykit.sources._common import attach_titles, iso2_to_name, stable_id

SOURCE = "aijobs"
DATASET = "aijobs.net Salary Index"
LICENSE = "CC0-1.0"

EXPERIENCE = {"EN": "entry", "MI": "mid", "SE": "senior", "EX": "executive"}
EMPLOYMENT = {"FT": "full_time", "PT": "part_time", "CT": "contract", "FL": "freelance"}
REMOTE = {0: "onsite", 50: "hybrid", 100: "remote"}
COMPANY_SIZE = {"S": "small (<50)", "M": "medium (50-250)", "L": "large (>250)"}


def load(fx: FxTable, predictor) -> pd.DataFrame:
    path = paths.RAW_AIJOBS / "salaries.csv"
    if not path.exists():
        return pd.DataFrame()

    df = pd.read_csv(path)
    df = attach_titles(df, "job_title", predictor)

    out = pd.DataFrame(index=df.index)
    out["obs_id"] = [stable_id(SOURCE, i) for i in range(len(df))]
    out["source"] = SOURCE
    out["source_dataset"] = DATASET
    out["record_type"] = "survey_response"
    out["license"] = LICENSE
    out["year"] = pd.to_numeric(df.work_year, errors="coerce")
    out["observed_at"] = pd.to_datetime(df.work_year.astype(str) + "-12-31",
                                        errors="coerce")

    out["job_title"] = df.job_title
    for col in ("job_title_clean", "job_title_core", "normalized_job_title",
                "normalized_job_code", "job_family", "norm_method",
                "norm_confidence", "isco08", "soc2018", "kldb2010"):
        out[col] = df[col]

    # Das Erfahrungsfeld der Quelle ist verlaesslicher als der Titel.
    out["seniority"] = df.experience_level.map(EXPERIENCE).fillna(df.title_seniority)
    out["seniority_source"] = df.experience_level.map(EXPERIENCE).notna().map(
        {True: "source_field", False: "title"})
    out["employment_type"] = df.employment_type.map(EMPLOYMENT)
    out["remote_type"] = df.remote_ratio.map(REMOTE)

    # Der Arbeitsort des Beschaeftigten schlaegt den Firmensitz.
    iso = df.employee_residence.where(df.employee_residence.notna(),
                                      df.company_location).astype("string")
    out["location_raw"] = df.employee_residence.astype("string")
    out["country_iso2"] = iso
    out["country_name"] = iso2_to_name(iso)
    out["location_source"] = iso.notna().map(
        {True: "source_field", False: "none"})

    out["salary_raw"] = pd.to_numeric(df.salary, errors="coerce")
    out["salary_currency"] = df.salary_currency.astype("string")
    out["salary_period"] = "year"
    out["salary_basis"] = "point"
    out["salary_annual_local"] = out["salary_raw"]
    out["salary_annual_usd"] = pd.to_numeric(df.salary_in_usd, errors="coerce")
    usd_per_eur = out["year"].map(lambda y: fx.usd_per_eur(int(y) if pd.notna(y) else None))
    out["salary_annual_eur"] = out["salary_annual_usd"] / usd_per_eur
    out["fx_rate_usd_per_unit"] = out["salary_annual_usd"] / out["salary_raw"]
    out["fx_source"] = "source_provided"

    out["company_size"] = df.company_size.map(COMPANY_SIZE)
    out["weight"] = 1.0
    return schema.conform_observations(out)
