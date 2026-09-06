"""Destatis GENESIS 62361-0034: Jahresverdienste nach KldB und Geschlecht."""
from __future__ import annotations

import pandas as pd

from salarykit import paths, schema
from salarykit.money import FxTable
from salarykit.sources._common import stable_id
from salarykit.titles.taxonomy import ROLES, role

SOURCE = "destatis_earnings"
DATASET = "Destatis Verdiensterhebung, Tabelle 62361-0034"
LICENSE = "dl-de/by-2-0"


def _kldb_lookup() -> dict[str, str]:
    result = {}
    for item in ROLES:
        if item.kldb2010:
            result.setdefault(item.kldb2010, item.code)
    return result


def _number(values: pd.Series) -> pd.Series:
    return pd.to_numeric(values.replace({"/": pd.NA, ".": pd.NA, "-": pd.NA}),
                         errors="coerce")


def load(fx: FxTable, predictor=None) -> pd.DataFrame:
    path = paths.RAW_DESTATIS / "62361-0034_00.csv"
    if not path.exists():
        return pd.DataFrame()
    names = ["year", "occupation_code", "occupation_label",
             "male_mean", "male_median", "female_mean", "female_median",
             "total_mean", "total_median"]
    df = pd.read_csv(path, sep=";", encoding="latin-1", skiprows=7,
                     names=names, dtype="string")
    df = df[df["year"].str.fullmatch(r"\d{4}", na=False)].copy()
    df["year"] = pd.to_numeric(df["year"], errors="coerce")
    df["occupation_code"] = df["occupation_code"].str.replace("KB10-", "", regex=False)
    df["occupation_label"] = df["occupation_label"].str.strip()

    long = []
    for sex in ("male", "female", "total"):
        part = df[["year", "occupation_code", "occupation_label"]].copy()
        part["sex"] = sex
        part["mean"] = _number(df[f"{sex}_mean"])
        part["median"] = _number(df[f"{sex}_median"])
        long.append(part)
    data = pd.concat(long, ignore_index=True)

    lookup = _kldb_lookup()
    codes = data["occupation_code"].astype("string")
    mapped = codes.map(lookup)
    mapped = mapped.fillna(codes.str.slice(0, 3).map(lookup))
    mapped = mapped.fillna(codes.str.slice(0, 2).map(lookup))
    if predictor is not None and mapped.isna().any():
        labels = data.loc[mapped.isna(), "occupation_label"].drop_duplicates().tolist()
        predictions = dict(zip(labels, predictor.predict_many(labels)))
        for idx in data.index[mapped.isna()]:
            prediction = predictions[data.at[idx, "occupation_label"]]
            if prediction.method != "unmatched":
                mapped.at[idx] = prediction.code

    out = pd.DataFrame(index=data.index)
    out["agg_id"] = [stable_id(SOURCE, year, code, sex) for year, code, sex in
                     zip(data.year, codes, data.sex)]
    out["source"] = SOURCE
    out["source_dataset"] = DATASET
    out["license"] = LICENSE
    out["year"] = data["year"]
    out["occupation_scheme"] = "KldB2010"
    out["occupation_code"] = codes
    out["occupation_label"] = data["occupation_label"]
    out["occupation_level"] = codes.str.len().map(
        {2: "berufsbereich", 3: "berufshauptgruppe", 5: "berufsgattung"}).fillna(
            "detailed")
    out["normalized_job_code"] = mapped
    out["normalized_job_title"] = mapped.map(
        lambda code: role(code).label if pd.notna(code) else None)
    out["job_family"] = mapped.map(lambda code: role(code).family if pd.notna(code) else None)
    out["norm_method"] = mapped.notna().map({True: "kldb_crosswalk", False: "unmatched"})
    out["norm_confidence"] = mapped.notna().map({True: 0.8, False: 0.0})
    out["geo_level"] = "country"
    out["geo_code"] = "DE"
    out["geo_name"] = "Deutschland"
    out["country_iso2"] = "DE"
    out["sex"] = data["sex"]
    out["worktime"] = "total"
    out["industry"] = "alle Wirtschaftszweige"
    out["salary_currency"] = "EUR"
    out["salary_period"] = "year"
    out["mean_raw"] = data["mean"]
    out["p50_raw"] = data["median"]
    out["mean_annual_eur"] = data["mean"]
    out["p50_annual_eur"] = data["median"]
    usd_per_eur = out["year"].map(lambda year: fx.usd_per_eur(int(year)))
    out["mean_annual_usd"] = out["mean_annual_eur"] * usd_per_eur
    out["p50_annual_usd"] = out["p50_annual_eur"] * usd_per_eur
    out["quantile_method"] = "reported"
    return schema.conform_aggregates(out)
