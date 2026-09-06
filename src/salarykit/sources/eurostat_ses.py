"""Eurostat Structure of Earnings Survey (Deutschland) -> aggregates.

Verwendet wird die Jahrestabelle und darin die Gesamtbranche sowie Gesamtalter.
Sie liefert Mittelwert, Median, erstes und neuntes Dezil in EUR/Jahr fuer
breite ISCO-08-Berufsgruppen. Die Gruppen sind absichtlich nicht auf einen
einzelnen Taxonomie-Jobtitel gezwungen: ``Professionals`` ist breiter als jede
einzelne Rolle und eine solche Zuordnung waere irrefuehrend.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from salarykit import paths, schema
from salarykit.money import FxTable
from salarykit.sources._common import stable_id

SOURCE = "eurostat_ses"
DATASET = "Eurostat Structure of Earnings Survey - annual earnings"
LICENSE = "Eurostat reuse policy"

INDICATORS = {
    "MEAN_E_EUR": "mean_raw",
    "MED_E_EUR": "p50_raw",
    "D1_E_EUR": "p10_raw",
    "D9_E_EUR": "p90_raw",
}
WORKTIME = {"TOTAL": "total", "FT": "full_time", "PT": "part_time"}
SEX = {"T": "total", "M": "male", "F": "female"}


def _position_codes(blob: dict) -> list[list[str]]:
    """Dimensionscodes jeweils in ihrer JSON-stat-Positionsreihenfolge."""
    result = []
    for dim in blob["id"]:
        index = blob["dimension"][dim]["category"]["index"]
        result.append([code for code, _ in sorted(index.items(), key=lambda item: item[1])])
    return result


def _selected_values(path: Path) -> pd.DataFrame:
    blob = json.loads(path.read_text())
    dims = blob["id"]
    sizes = tuple(blob["size"])
    codes = _position_codes(blob)
    labels = {dim: blob["dimension"][dim]["category"].get("label", {}) for dim in dims}
    rows = []
    for flat, value in blob.get("value", {}).items():
        coordinate = np.unravel_index(int(flat), sizes)
        row = {dim: codes[i][coordinate[i]] for i, dim in enumerate(dims)}
        if (row["nace_r2"] != "B-S_X_O" or row["age"] != "TOTAL" or
                row["geo"] != "DE" or row["worktime"] not in WORKTIME or
                row["sex"] not in SEX or row["indic_se"] not in INDICATORS):
            continue
        row["value"] = value
        row["occupation_label"] = labels["isco08"].get(row["isco08"], row["isco08"])
        row["industry_label"] = labels["nace_r2"].get(row["nace_r2"], row["nace_r2"])
        rows.append(row)
    return pd.DataFrame(rows)


def load(fx: FxTable, predictor=None) -> pd.DataFrame:
    path = paths.RAW_EUROSTAT / "earn_ses_annual_DE.json"
    if not path.exists():
        return pd.DataFrame()
    long = _selected_values(path)
    if long.empty:
        return pd.DataFrame()
    index = ["time", "isco08", "occupation_label", "worktime", "sex",
             "industry_label"]
    wide = long.pivot_table(index=index, columns="indic_se", values="value",
                            aggfunc="first").reset_index()
    wide = wide.rename(columns=INDICATORS)

    out = pd.DataFrame(index=wide.index)
    out["agg_id"] = [stable_id(SOURCE, y, occ, work, sex) for y, occ, work, sex in
                     zip(wide.time, wide.isco08, wide.worktime, wide.sex)]
    out["source"] = SOURCE
    out["source_dataset"] = DATASET
    out["license"] = LICENSE
    out["year"] = pd.to_numeric(wide.time, errors="coerce")
    out["occupation_scheme"] = "ISCO08"
    out["occupation_code"] = wide.isco08.str.removeprefix("OC")
    out["occupation_label"] = wide.occupation_label.astype("string")
    out["occupation_level"] = wide.isco08.map(
        lambda c: "total" if c == "TOTAL" else ("major" if "-" not in c else "aggregate"))
    out["norm_method"] = "unmatched"
    out["norm_confidence"] = 0.0
    out["geo_level"] = "country"
    out["geo_code"] = "DE"
    out["geo_name"] = "Germany"
    out["country_iso2"] = "DE"
    out["sex"] = wide.sex.map(SEX)
    out["worktime"] = wide.worktime.map(WORKTIME)
    out["industry"] = wide.industry_label.astype("string")
    out["salary_currency"] = "EUR"
    out["salary_period"] = "year"
    for col in ("mean_raw", "p10_raw", "p50_raw", "p90_raw"):
        out[col] = pd.to_numeric(wide[col], errors="coerce") if col in wide else pd.NA
        out[col.replace("_raw", "_annual_eur")] = out[col]
    usd_per_eur = out["year"].map(
        lambda y: fx.usd_per_eur(int(y)) if pd.notna(y) else fx.usd_per_eur())
    out["mean_annual_usd"] = out["mean_annual_eur"] * usd_per_eur
    out["p50_annual_usd"] = out["p50_annual_eur"] * usd_per_eur
    out["quantile_method"] = "reported"
    return schema.conform_aggregates(out)
