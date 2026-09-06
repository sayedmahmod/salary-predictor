"""Stack Overflow Developer Survey 2025 -> observations.

Die Umfrage hat keinen freien Jobtitel, sondern das kontrollierte Feld
``DevType``. Das wird direkt auf die Taxonomie gemappt (``norm_method =
source_field``) - genauer als den Klassifikator auf eine Auswahlliste
loszulassen. Was die Karte nicht kennt, geht durch den normalen Weg.

``ConvertedCompYearly`` ist bereits USD/Jahr; der Wert wird uebernommen.
"""
from __future__ import annotations

import pandas as pd

from salarykit import paths, schema
from salarykit.money import FxTable
from salarykit.sources._common import (attach_titles, country_columns,
                                       stable_id)
from salarykit.titles.taxonomy import FAMILIES, role

SOURCE = "so_2025"
DATASET = "Stack Overflow Developer Survey 2025"
LICENSE = "ODbL-1.0"
YEAR = 2025

USECOLS = ["ResponseId", "Age", "EdLevel", "Employment", "WorkExp", "YearsCode",
           "DevType", "OrgSize", "ICorPM", "RemoteWork", "Country", "Currency",
           "CompTotal", "ConvertedCompYearly", "Industry"]

#: DevType (kontrolliertes Vokabular) -> Taxonomie-Code.
DEVTYPE_TO_CODE: dict[str, str] = {
    "Developer, full-stack": "software.fullstack",
    "Developer, back-end": "software.backend",
    "Developer, front-end": "software.frontend",
    "Developer, desktop or enterprise applications": "software.engineer",
    "Developer, mobile": "software.mobile",
    "Developer, embedded applications or devices": "software.embedded",
    "Developer, game or graphics": "software.games",
    "Developer, QA or test": "quality.qa_engineer",
    "Developer, AI apps or physical AI": "data.ml_engineer",
    "Developer Experience": "software.platform",
    "Developer Advocate": "marketing.seo_content",
    "Engineering manager": "management.engineering",
    "Engineer, site reliability": "infra.sre",
    "Engineer, data": "data.engineer",
    "Data engineer": "data.engineer",
    "Data scientist": "data.scientist",
    "Data scientist or machine learning specialist": "data.scientist",
    "Data or business analyst": "data.analyst",
    "AI/ML engineer": "data.ml_engineer",
    "Applied scientist": "data.ml_scientist",
    "Research & Development role": "research.scientist",
    "Academic researcher": "research.scientist",
    "Scientist": "research.scientist",
    "DevOps engineer or professional": "infra.devops",
    "Cloud infrastructure engineer": "infra.cloud",
    "System administrator": "infra.systems",
    "Database administrator": "data.dba",
    "Security professional": "security.engineer",
    "Cybersecurity or InfoSec professional": "security.analyst",
    "Hardware Engineer": "eng.electrical",
    "Architect, software or solutions": "software.architect",
    "Product manager": "product.manager",
    "Project manager": "product.project_manager",
    "Program manager": "product.program_manager",
    "Designer": "design.product_designer",
    "Marketing or sales professional": "sales.representative",
    "Educator": "education.teacher",
    "Support engineer or analyst": "it.support",
    "Senior executive (C-suite, VP, etc.)": "management.executive",
    "Founder, technology or otherwise": "management.executive",
    "Blockchain": "software.engineer",
}

REMOTE = {
    "Remote": "remote",
    "In-person": "onsite",
    "Hybrid (some remote, leans heavy to in-person)": "hybrid",
    "Hybrid (some in-person, leans heavy to flexibility)": "hybrid",
    "Your choice (very flexible, you can come in when you want or just as needed)": "remote",
}
EMPLOYMENT = {
    "Employed": "full_time",
    "Employed, full-time": "full_time",
    "Employed, part-time": "part_time",
    "Independent contractor, freelancer, or self-employed": "freelance",
    "Student, full-time": "internship",
    "Student, part-time": "internship",
}


def load(fx: FxTable, predictor) -> pd.DataFrame:
    path = paths.RAW_STACKOVERFLOW / "survey_results_public.csv"
    if not path.exists():
        return pd.DataFrame()

    header = pd.read_csv(path, nrows=0).columns.tolist()
    cols = [c for c in USECOLS if c in header]
    df = pd.read_csv(path, usecols=cols, low_memory=False)
    for missing in set(USECOLS) - set(cols):
        df[missing] = pd.NA

    df["DevType"] = df["DevType"].astype("string")
    df = attach_titles(df, "DevType", predictor)

    mapped = df["DevType"].map(DEVTYPE_TO_CODE)
    out = pd.DataFrame(index=df.index)
    out["obs_id"] = df.ResponseId.map(lambda r: stable_id(SOURCE, r))
    out["source"] = SOURCE
    out["source_dataset"] = DATASET
    out["record_type"] = "survey_response"
    out["license"] = LICENSE
    out["year"] = YEAR
    out["observed_at"] = pd.Timestamp(f"{YEAR}-06-30")

    out["job_title"] = df["DevType"]
    out["job_title_clean"] = df["job_title_clean"]
    out["job_title_core"] = df["job_title_core"]
    out["normalized_job_code"] = mapped.fillna(df["normalized_job_code"])
    out["normalized_job_title"] = out["normalized_job_code"].map(lambda c: role(c).label)
    out["job_family"] = out["normalized_job_code"].map(lambda c: role(c).family)
    out["norm_method"] = mapped.notna().map({True: "source_field", False: None})
    out["norm_method"] = out["norm_method"].fillna(df["norm_method"])
    out["norm_confidence"] = mapped.notna().map({True: 1.0, False: None})
    out["norm_confidence"] = out["norm_confidence"].fillna(df["norm_confidence"])
    out["isco08"] = out["normalized_job_code"].map(lambda c: role(c).isco08)
    out["soc2018"] = out["normalized_job_code"].map(lambda c: role(c).soc2018)
    out["kldb2010"] = out["normalized_job_code"].map(lambda c: role(c).kldb2010)

    # Aus ICorPM laesst sich nur Fuehrung/keine Fuehrung ableiten - das ist
    # gruber als unsere Stufen, deshalb nur als schwaches Signal.
    out["seniority"] = df.ICorPM.map({"People manager": "lead"})
    out["seniority_source"] = out["seniority"].notna().map(
        {True: "source_field", False: "none"})
    out["employment_type"] = df.Employment.astype("string").map(EMPLOYMENT)
    out["remote_type"] = df.RemoteWork.astype("string").map(REMOTE)

    countries = country_columns(df.Country)
    out["location_raw"] = df.Country.astype("string")
    out["country_iso2"] = countries.country_iso2
    out["country_name"] = countries.country_name
    out["location_source"] = "source_field"

    out["salary_raw"] = pd.to_numeric(df.CompTotal, errors="coerce")
    out["salary_currency"] = df.Currency.astype("string").str.slice(0, 3)
    out["salary_period"] = "year"
    out["salary_basis"] = "point"
    out["salary_annual_local"] = out["salary_raw"]
    out["salary_annual_usd"] = pd.to_numeric(df.ConvertedCompYearly, errors="coerce")
    out["salary_annual_eur"] = out["salary_annual_usd"] / fx.usd_per_eur(YEAR)
    out["fx_rate_usd_per_unit"] = out["salary_annual_usd"] / out["salary_raw"]
    out["fx_source"] = "source_provided"

    out["experience_years"] = pd.to_numeric(df.WorkExp, errors="coerce")
    out["company_size"] = df.OrgSize.astype("string")
    out["industry"] = df.Industry.astype("string")
    out["education_level"] = df.EdLevel.astype("string")
    out["weight"] = 1.0
    return schema.conform_observations(out)
