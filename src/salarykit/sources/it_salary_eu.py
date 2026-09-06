"""CC0 IT Salary Survey EU 2018--2020, konservativ auf Deutschland begrenzt."""
from __future__ import annotations

import pandas as pd

from salarykit import paths, schema
from salarykit.money import FxTable
from salarykit.sources._common import attach_titles, resolve_locations, stable_id

SOURCE = "it_salary_eu"
DATASET = "IT Salary Survey for EU region 2018-2020 (Germany subset)"
LICENSE = "CC0-1.0"

_FILES = {
    2018: "IT Salary Survey EU 2018.csv",
    2019: "T Salary Survey EU 2019.csv",
    2020: "IT Salary Survey EU  2020.csv",
}
_FIELDS = {
    2018: {"time": "Timestamp", "title": "Position", "salary": "Current Salary",
           "experience": "Years of experience", "seniority": "Your level"},
    2019: {"time": "Zeitstempel", "title": "Position (without seniority)",
           "salary": "Yearly brutto salary (without bonus and stocks)",
           "experience": "Years of experience", "seniority": "Seniority level"},
    2020: {"time": "Timestamp", "title": "Position ",
           "salary": "Yearly brutto salary (without bonus and stocks) in EUR",
           "experience": "Total years of experience", "seniority": "Seniority level"},
}


def _seniority(values: pd.Series) -> pd.Series:
    text = values.astype("string").str.strip().str.lower()
    mapping = {"student": "intern", "intern": "intern", "entry": "entry",
               "junior": "junior", "middle": "mid", "mid": "mid",
               "senior": "senior", "lead": "lead", "head": "head",
               "director": "director", "principal": "principal"}
    return text.map(mapping)


def _experience(values: pd.Series) -> pd.Series:
    text = values.astype("string").str.replace(",", ".", regex=False)
    return pd.to_numeric(text.str.extract(r"(\d+(?:\.\d+)?)", expand=False), errors="coerce")


def _employment(values: pd.Series) -> pd.Series:
    text = values.astype("string").str.lower()
    out = pd.Series(pd.NA, index=values.index, dtype="string")
    out = out.mask(text.str.contains("full", na=False), "full_time")
    out = out.mask(text.str.contains("part", na=False), "part_time")
    out = out.mask(text.str.contains("self|freelanc", na=False), "freelance")
    return out


def _load_year(path, year: int, fx: FxTable, predictor) -> pd.DataFrame:
    df = pd.read_csv(path)
    fields = _FIELDS[year]
    places = resolve_locations(df["City"], pd.Series([None] * len(df), index=df.index))
    df = df.loc[places.country_iso2.eq("DE")].copy()
    places = places.loc[df.index]
    df["_region"] = places.region
    df["_city"] = places.city
    df = df.reset_index(drop=True)
    df = attach_titles(df, fields["title"], predictor)

    salary = pd.to_numeric(df[fields["salary"]], errors="coerce")
    timestamp = pd.to_datetime(df[fields["time"]], errors="coerce", dayfirst=True)
    out = pd.DataFrame(index=df.index)
    out["obs_id"] = [stable_id(SOURCE, year, i, ts) for i, ts in
                     zip(df.index, df[fields["time"]])]
    out["source"] = SOURCE
    out["source_dataset"] = DATASET
    out["record_type"] = "survey_response"
    out["license"] = LICENSE
    out["year"] = year
    out["observed_at"] = timestamp
    out["job_title"] = df[fields["title"]]
    for col in ("job_title_clean", "job_title_core", "normalized_job_title",
                "normalized_job_code", "job_family", "norm_method",
                "norm_confidence", "isco08", "soc2018", "kldb2010"):
        out[col] = df[col]
    sourced_seniority = _seniority(df[fields["seniority"]])
    out["seniority"] = sourced_seniority.fillna(df["title_seniority"])
    out["seniority_source"] = sourced_seniority.notna().map(
        {True: "source_field", False: "title"})
    employment = (df["Employment status"] if "Employment status" in df
                  else pd.Series("Full-time employee", index=df.index))
    out["employment_type"] = _employment(employment).fillna("full_time")
    out["location_raw"] = df["City"]
    out["country_iso2"] = "DE"
    out["country_name"] = "Germany"
    out["region"] = df["_region"]
    out["city"] = df["_city"]
    out["location_source"] = "source_field"
    out["salary_raw"] = salary
    out["salary_currency"] = "EUR"
    out["salary_period"] = "year"
    out["salary_basis"] = "point"
    out["salary_annual_local"] = salary
    out["salary_annual_eur"] = salary
    out["salary_annual_usd"] = salary * fx.usd_per_eur(year)
    out["fx_rate_usd_per_unit"] = fx.usd_per_eur(year)
    out["fx_source"] = "identity"
    out["experience_years"] = _experience(df[fields["experience"]])
    out["company_size"] = df.get("Company size")
    out["company_name"] = df.get("Company name ")
    out["industry"] = df.get("Company business sector")
    out["gender"] = df.get("Gender")
    out["weight"] = 0.65 + 0.05 * (year - 2018)
    return schema.conform_observations(out)


def load(fx: FxTable, predictor) -> pd.DataFrame:
    frames = []
    for year, filename in _FILES.items():
        path = paths.RAW_IT_SALARY_EU / filename
        if path.exists():
            frames.append(_load_year(path, year, fx, predictor))
    return (schema.conform_observations(pd.concat(frames, ignore_index=True))
            if frames else pd.DataFrame())
