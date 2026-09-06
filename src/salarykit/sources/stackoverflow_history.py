"""Deutsche Stack-Overflow-Gehaltsantworten 2018--2024.

Die Feldnamen der offiziellen Jahresarchive wechseln mehrfach. Dieser Adapter
zieht sie auf dieselbe Semantik wie der 2025-Adapter und behandelt alle Jahre
als *eine* Quelle. So bekommt nicht jedes Survey-Jahr beim source-balancing ein
eigenes Vollgewicht.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from salarykit import paths, schema
from salarykit.money import FxTable, annualize_series
from salarykit.sources._common import attach_titles, country_columns, stable_id
from salarykit.sources.stackoverflow import DEVTYPE_TO_CODE
from salarykit.titles.taxonomy import role

SOURCE = "so_history"
DATASET = "Stack Overflow Developer Survey 2018-2024 (Germany subset)"
LICENSE = "ODbL-1.0"

_CONVERTED = {2018: "ConvertedSalary", 2019: "ConvertedComp",
              2020: "ConvertedComp", 2021: "ConvertedCompYearly",
              2022: "ConvertedCompYearly", 2023: "ConvertedCompYearly",
              2024: "ConvertedCompYearly"}
_ID = {2018: "Respondent", 2019: "Respondent", 2020: "Respondent"}
_PERIOD = {"Yearly": "year", "Monthly": "month", "Weekly": "week",
           "Daily": "day", "Hourly": "hour", "Year": "year",
           "Month": "month", "Week": "week"}


def _first_existing(df: pd.DataFrame, *names: str) -> pd.Series:
    for name in names:
        if name in df:
            return df[name]
    return pd.Series(pd.NA, index=df.index)


def _years(values: pd.Series) -> pd.Series:
    text = values.astype("string")
    result = pd.to_numeric(text, errors="coerce").astype("float64")
    result = result.mask(text.str.contains("Less than 1", case=False, na=False), 0.5)
    result = result.mask(text.str.contains("More than 50", case=False, na=False), 51)
    return result


def _employment(values: pd.Series) -> pd.Series:
    text = values.astype("string").str.lower()
    out = pd.Series(pd.NA, index=values.index, dtype="string")
    out = out.mask(text.str.contains("full-time|employed, full", na=False), "full_time")
    out = out.mask(text.str.contains("part-time|employed, part", na=False), "part_time")
    out = out.mask(text.str.contains("independent contractor|freelanc|self-employed", na=False),
                   "freelance")
    out = out.mask(text.str.contains("student", na=False), "internship")
    return out


def _remote(values: pd.Series) -> pd.Series:
    text = values.astype("string").str.lower()
    out = pd.Series(pd.NA, index=values.index, dtype="string")
    out = out.mask(text.str.contains("remote", na=False), "remote")
    out = out.mask(text.str.contains("hybrid", na=False), "hybrid")
    out = out.mask(text.str.contains("in-person|office", na=False), "onsite")
    return out


def _mapped_devtype(value) -> str | None:
    if pd.isna(value):
        return None
    choices = [part.strip() for part in str(value).split(";")]
    for choice in choices:
        if choice in DEVTYPE_TO_CODE:
            return DEVTYPE_TO_CODE[choice]
    return None


def _load_year(path: Path, year: int, fx: FxTable, predictor) -> pd.DataFrame:
    header = pd.read_csv(path, nrows=0).columns.tolist()
    wanted = {
        "Respondent", "ResponseId", "Country", "DevType", "Employment",
        "EdLevel", "FormalEducation", "OrgSize", "CompanySize", "Industry",
        "WorkExp", "YearsCodePro", "RemoteWork", "WorkRemote", "Currency",
        "CurrencySymbol", "CompTotal", "Salary", "CompFreq", "SalaryType",
        _CONVERTED[year],
    }
    df = pd.read_csv(path, usecols=[c for c in header if c in wanted], low_memory=False)
    df = df[df["Country"].astype("string") == "Germany"].copy()
    if df.empty:
        return pd.DataFrame()

    df = attach_titles(df, "DevType", predictor)
    mapped = df["DevType"].map(_mapped_devtype).astype("string")
    mapped_mask = mapped.notna()

    out = pd.DataFrame(index=df.index)
    ids = _first_existing(df, _ID.get(year, "ResponseId"), "ResponseId", "Respondent")
    out["obs_id"] = [stable_id(SOURCE, year, item) for item in ids]
    out["source"] = SOURCE
    out["source_dataset"] = DATASET
    out["record_type"] = "survey_response"
    out["license"] = LICENSE
    out["year"] = year
    out["observed_at"] = pd.Timestamp(f"{year}-06-30")

    out["job_title"] = df["DevType"]
    for col in ("job_title_clean", "job_title_core", "normalized_job_code",
                "normalized_job_title", "job_family", "norm_method",
                "norm_confidence", "isco08", "soc2018", "kldb2010"):
        out[col] = df[col]
    out.loc[mapped_mask, "normalized_job_code"] = mapped[mapped_mask]
    out.loc[mapped_mask, "normalized_job_title"] = mapped[mapped_mask].map(
        lambda code: role(code).label)
    out.loc[mapped_mask, "job_family"] = mapped[mapped_mask].map(
        lambda code: role(code).family)
    out.loc[mapped_mask, "norm_method"] = "source_field"
    out.loc[mapped_mask, "norm_confidence"] = 1.0
    out.loc[mapped_mask, "isco08"] = mapped[mapped_mask].map(lambda code: role(code).isco08)
    out.loc[mapped_mask, "soc2018"] = mapped[mapped_mask].map(lambda code: role(code).soc2018)
    out.loc[mapped_mask, "kldb2010"] = mapped[mapped_mask].map(lambda code: role(code).kldb2010)

    out["seniority"] = df["title_seniority"]
    out["seniority_source"] = out["seniority"].notna().map(
        {True: "title", False: "none"})
    out["employment_type"] = _employment(_first_existing(df, "Employment"))
    out["remote_type"] = _remote(_first_existing(df, "RemoteWork", "WorkRemote"))

    countries = country_columns(df["Country"])
    out["location_raw"] = df["Country"]
    out["country_iso2"] = countries.country_iso2
    out["country_name"] = countries.country_name
    out["location_source"] = "source_field"

    raw = pd.to_numeric(_first_existing(df, "CompTotal", "Salary"), errors="coerce")
    period = _first_existing(df, "CompFreq", "SalaryType").astype("string").map(_PERIOD)
    annual_local = annualize_series(raw, period)
    annual_usd = pd.to_numeric(df[_CONVERTED[year]], errors="coerce")
    out["salary_raw"] = raw
    out["salary_currency"] = _first_existing(df, "Currency", "CurrencySymbol").astype(
        "string").str.slice(0, 3).str.upper()
    out["salary_period"] = period.fillna("year")
    out["salary_basis"] = "point"
    out["salary_annual_local"] = annual_local
    out["salary_annual_usd"] = annual_usd
    out["salary_annual_eur"] = annual_usd / fx.usd_per_eur(year)
    out["fx_rate_usd_per_unit"] = annual_usd / annual_local.replace(0, np.nan)
    out["fx_source"] = "source_provided"

    out["experience_years"] = _years(_first_existing(df, "WorkExp", "YearsCodePro"))
    out["company_size"] = _first_existing(df, "OrgSize", "CompanySize")
    out["industry"] = _first_existing(df, "Industry")
    out["education_level"] = _first_existing(df, "EdLevel", "FormalEducation")
    # Alte nominale Gehaelter bleiben dank ``year`` modellierbar, sollen aber
    # eine heutige Beobachtung nicht gleich stark beeinflussen.
    out["weight"] = min(0.95, 0.65 + 0.05 * (year - 2018))
    return schema.conform_observations(out)


def load(fx: FxTable, predictor) -> pd.DataFrame:
    folder = paths.RAW_STACKOVERFLOW_HISTORY
    frames = []
    for year in sorted(_CONVERTED):
        path = folder / f"{year}.csv"
        if path.exists():
            frame = _load_year(path, year, fx, predictor)
            if not frame.empty:
                frames.append(frame)
    return (schema.conform_observations(pd.concat(frames, ignore_index=True))
            if frames else pd.DataFrame())
