"""HF ``krishujeniya/Salary_of_Data_Professions`` -> observations.

Kleine Tabelle mit Berufsbezeichnung, Alter, Erfahrung und Gehalt.

Wichtige Einschraenkung: die Quelle nennt **weder Waehrung noch Periode noch
Land**. Der Betrag wird deshalb nur als ``salary_raw`` uebernommen; auf Jahr,
EUR oder USD wird bewusst nicht umgerechnet, weil jede solche Umrechnung eine
erfundene Annahme waere. Damit fallen diese Zeilen aus der Quantilsrechnung
heraus - sie stehen fuer die Titel- und Erfahrungsauswertung zur Verfuegung.
"""
from __future__ import annotations

import pandas as pd

from salarykit import paths, schema
from salarykit.money import FxTable
from salarykit.sources._common import attach_titles, stable_id

SOURCE = "hf_data_professions"
DATASET = "HF krishujeniya/Salary_of_Data_Professions"
LICENSE = "MIT (Herkunft der Daten ungeklaert)"

SEX = {"M": "male", "F": "female"}


def load(fx: FxTable, predictor) -> pd.DataFrame:
    path = (paths.RAW_HF / "data_professions" /
            "salary_prediction_data_professions.csv")
    if not path.exists():
        return pd.DataFrame()

    df = pd.read_csv(path)
    df["DESIGNATION"] = df["DESIGNATION"].astype("string")
    df = attach_titles(df, "DESIGNATION", predictor)

    current = pd.to_datetime(df["CURRENT DATE"], errors="coerce", format="mixed")
    joined = pd.to_datetime(df["DOJ"], errors="coerce", format="mixed")
    tenure = (current - joined).dt.days / 365.25

    out = pd.DataFrame(index=df.index)
    out["obs_id"] = [stable_id(SOURCE, i) for i in range(len(df))]
    out["source"] = SOURCE
    out["source_dataset"] = DATASET
    out["record_type"] = "survey_response"
    out["license"] = LICENSE
    out["year"] = current.dt.year
    out["observed_at"] = current

    out["job_title"] = df["DESIGNATION"]
    for col in ("job_title_clean", "job_title_core", "normalized_job_title",
                "normalized_job_code", "job_family", "norm_method",
                "norm_confidence", "isco08", "soc2018", "kldb2010"):
        out[col] = df[col]

    out["seniority"] = df.title_seniority
    out["seniority_source"] = df.title_seniority.notna().map(
        {True: "title", False: "none"})

    out["salary_raw"] = pd.to_numeric(df["SALARY"], errors="coerce")
    out["salary_basis"] = "point"
    out["fx_source"] = "unknown"          # Waehrung der Quelle ist nicht angegeben

    exp = pd.to_numeric(df["PAST EXP"], errors="coerce").fillna(0) + tenure.fillna(0)
    out["experience_years"] = exp.where(exp > 0)
    out["industry"] = df["UNIT"].astype("string")
    out["gender"] = df["SEX"].astype("string").map(SEX)
    out["weight"] = 1.0
    return schema.conform_observations(out)
