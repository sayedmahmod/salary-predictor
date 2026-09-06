"""BLS OEWS (May 2025) -> aggregates.

Die amtliche US-Berufsstatistik ist die sauberste Quantilsquelle im Projekt:
sie liefert p10/p25/p50/p75/p90 des Jahresverdienstes je Beruf (SOC 2018) und
Gebiet, direkt gemessen statt geschaetzt.

Uebernommen wird nur, was sich sinnvoll vergleichen laesst:
Bundesweit (AREA_TYPE 1) und je Bundesstaat (AREA_TYPE 2), branchenuebergreifend
(``I_GROUP = cross-industry``) und auf Berufsebene ``detailed``/``major``.
Metropolregionen bleiben draussen - sie wuerden die Tabelle vervierfachen,
ohne fuer den Vergleich mit DE/EU etwas beizutragen.
"""
from __future__ import annotations

import openpyxl
import pandas as pd

from salarykit import paths, schema
from salarykit.money import FxTable
from salarykit.sources._common import stable_id
from salarykit.titles.taxonomy import ROLES, role

SOURCE = "bls_oews"
DATASET = "BLS Occupational Employment and Wage Statistics, May 2025"
LICENSE = "public domain (U.S. Government)"
YEAR = 2025

SHEET = "All May 2025 data"
KEEP_AREA_TYPES = {"1", "2"}
KEEP_OCC_LEVELS = {"detailed", "major", "total"}

#: Spaltennamen -> Index im Blatt
FIELDS = {
    "AREA_TITLE": 1, "AREA_TYPE": 2, "PRIM_STATE": 3, "I_GROUP": 6,
    "OCC_CODE": 8, "OCC_TITLE": 9, "O_GROUP": 10, "TOT_EMP": 11,
    "A_MEAN": 18, "A_PCT10": 25, "A_PCT25": 26, "A_MEDIAN": 27,
    "A_PCT75": 28, "A_PCT90": 29,
}
#: BLS-Platzhalter fuer unterdrueckte Werte
SUPPRESSED = {"*", "**", "#", "~", ""}


def _num(value):
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace(",", "")
    if text in SUPPRESSED:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _soc_lookup() -> dict[str, str]:
    """SOC-Code -> Taxonomie-Code. Mehrfachbelegung: erste Rolle gewinnt."""
    out: dict[str, str] = {}
    for r in ROLES:
        if r.soc2018:
            out.setdefault(r.soc2018, r.code)
    return out


def load(fx: FxTable, predictor=None) -> pd.DataFrame:
    path = paths.RAW_BLS / "all_data_M_2025.xlsx"
    if not path.exists():
        return pd.DataFrame()

    workbook = openpyxl.load_workbook(path, read_only=True, data_only=True)
    sheet = workbook[SHEET]
    rows: list[dict] = []
    for raw in sheet.iter_rows(min_row=2, values_only=True):
        if str(raw[FIELDS["AREA_TYPE"]]) not in KEEP_AREA_TYPES:
            continue
        if str(raw[FIELDS["I_GROUP"]]) != "cross-industry":
            continue
        if str(raw[FIELDS["O_GROUP"]]) not in KEEP_OCC_LEVELS:
            continue
        rows.append({key: raw[idx] for key, idx in FIELDS.items()})
    workbook.close()

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    for col in ("TOT_EMP", "A_MEAN", "A_PCT10", "A_PCT25", "A_MEDIAN",
                "A_PCT75", "A_PCT90"):
        df[col] = df[col].map(_num)

    soc = _soc_lookup()
    codes = df.OCC_CODE.astype("string")
    mapped = codes.map(soc)
    # Fallback 1: Hauptgruppe (11-0000) fuer alles, was nicht exakt gemappt ist
    mapped = mapped.fillna(codes.str.slice(0, 2).add("-0000").map(soc))
    method = mapped.notna().map({True: "soc_crosswalk", False: None})

    # Fallback 2: die amtliche Berufsbezeichnung durch den Klassifikator
    # schicken. Genau dafuer ist er da - die SOC-Liste ist feiner als unsere
    # Taxonomie, aber die Bezeichnungen sind gut lesbar.
    if predictor is not None and mapped.isna().any():
        todo = df.loc[mapped.isna(), "OCC_TITLE"].astype("string").fillna("")
        unique = todo.drop_duplicates()
        guesses = {title: pred for title, pred
                   in zip(unique, predictor.predict_many(unique.tolist()))}
        mapped = mapped.copy()
        method = method.copy()
        for idx, title in todo.items():
            pred = guesses.get(title)
            if pred is not None and pred.method != "unmatched":
                mapped.at[idx] = pred.code
                method.at[idx] = pred.method

    usd_per_eur = fx.usd_per_eur(YEAR)
    out = pd.DataFrame(index=df.index)
    out["agg_id"] = [stable_id(SOURCE, a, o) for a, o in
                     zip(df.AREA_TITLE, df.OCC_CODE)]
    out["source"] = SOURCE
    out["source_dataset"] = DATASET
    out["license"] = LICENSE
    out["year"] = YEAR

    out["occupation_scheme"] = "SOC2018"
    out["occupation_code"] = codes
    out["occupation_label"] = df.OCC_TITLE.astype("string")
    out["occupation_level"] = df.O_GROUP.astype("string")
    out["normalized_job_code"] = mapped
    out["normalized_job_title"] = mapped.map(lambda c: role(c).label if pd.notna(c) else None)
    out["job_family"] = mapped.map(lambda c: role(c).family if pd.notna(c) else None)
    out["norm_method"] = method.fillna("unmatched")
    out["norm_confidence"] = mapped.notna().map({True: 0.9, False: 0.0})

    is_national = df.AREA_TYPE.astype("string") == "1"
    out["geo_level"] = is_national.map({True: "country", False: "state"})
    out["geo_code"] = df.PRIM_STATE.astype("string")
    out["geo_name"] = df.AREA_TITLE.astype("string")
    out["country_iso2"] = "US"
    out["region"] = out["geo_name"].where(~is_national)

    out["sex"] = "total"
    out["worktime"] = "total"
    out["industry"] = "cross-industry"
    out["employment_count"] = df.TOT_EMP

    out["salary_currency"] = "USD"
    out["salary_period"] = "year"
    out["mean_raw"] = df.A_MEAN
    out["p10_raw"] = df.A_PCT10
    out["p25_raw"] = df.A_PCT25
    out["p50_raw"] = df.A_MEDIAN
    out["p75_raw"] = df.A_PCT75
    out["p90_raw"] = df.A_PCT90
    for stat in ("mean", "p10", "p25", "p50", "p75", "p90"):
        out[f"{stat}_annual_eur"] = out[f"{stat}_raw"] / usd_per_eur
    out["mean_annual_usd"] = out["mean_raw"]
    out["p50_annual_usd"] = out["p50_raw"]
    out["quantile_method"] = "reported"
    return schema.conform_aggregates(out)
