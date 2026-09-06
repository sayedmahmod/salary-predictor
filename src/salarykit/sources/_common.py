"""Bausteine, die alle Quell-Adapter teilen."""
from __future__ import annotations

import hashlib

import pandas as pd

from salarykit.geo import COUNTRY_NAMES, normalize_country, parse_location
from salarykit.titles.predict import JobTitlePredictor
from salarykit.titles.taxonomy import FAMILIES

#: Spalten, die :func:`attach_titles` erzeugt.
TITLE_COLUMNS = [
    "job_title_clean", "job_title_core", "normalized_job_title",
    "normalized_job_code", "job_family", "norm_method", "norm_confidence",
    "isco08", "soc2018", "kldb2010",
]
#: Aus dem Titel gezogene Nebenattribute - die Adapter entscheiden, ob sie
#: gegenueber einem echten Quellfeld den Vorrang bekommen.
TITLE_EXTRAS = [
    "title_seniority", "title_employment_type", "title_remote_type",
    "title_country_iso2", "title_region", "title_city",
]


def stable_id(source: str, *parts) -> str:
    raw = "|".join([source, *(str(p) for p in parts)])
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


def attach_titles(df: pd.DataFrame, title_col: str,
                  predictor: JobTitlePredictor) -> pd.DataFrame:
    """Titel saeubern und klassifizieren - dedupliziert ueber eindeutige Titel.

    Bei 400k Anzeigen mit 200k eindeutigen Titeln halbiert das die Arbeit; bei
    aijobs mit 422 eindeutigen Titeln auf 150k Zeilen spart es fast alles.
    """
    titles = df[title_col].astype("string").fillna("")
    unique = titles.drop_duplicates().tolist()
    predictions = predictor.predict_many(unique)

    table = pd.DataFrame({
        title_col: unique,
        "job_title_clean": [p.clean for p in predictions],
        "job_title_core": [p.core for p in predictions],
        "normalized_job_title": [p.label for p in predictions],
        "normalized_job_code": [p.code for p in predictions],
        "job_family": [p.family for p in predictions],
        "norm_method": [p.method for p in predictions],
        "norm_confidence": [p.confidence for p in predictions],
        "isco08": [p.isco08 for p in predictions],
        "soc2018": [p.soc2018 for p in predictions],
        "kldb2010": [p.kldb2010 for p in predictions],
        "title_seniority": [p.seniority for p in predictions],
        "title_employment_type": [p.employment_type for p in predictions],
        "title_remote_type": [p.remote_type for p in predictions],
        "title_country_iso2": [p.country_iso2 for p in predictions],
        "title_region": [p.region for p in predictions],
        "title_city": [p.city for p in predictions],
    })
    out = df.copy()
    out[title_col] = titles
    return out.merge(table, on=title_col, how="left")


def resolve_locations(raw: pd.Series, default_country: pd.Series | None = None
                      ) -> pd.DataFrame:
    """Ortsfelder aufloesen, ebenfalls ueber eindeutige Werte."""
    raw = raw.astype("string").fillna("")
    if default_country is None:
        default_country = pd.Series([None] * len(raw), index=raw.index, dtype="object")
    else:
        default_country = default_country.astype("object").where(
            default_country.notna(), None)

    pairs = pd.DataFrame({"raw": raw, "cc": default_country})
    unique = pairs.drop_duplicates()
    cache: dict[tuple, tuple] = {}
    for value, country in unique.itertuples(index=False):
        place = parse_location(value, default_country=country)
        cache[(value, country)] = (place.country_iso2, place.country_name,
                                   place.region, place.city)

    resolved = [cache[(v, c)] for v, c in pairs.itertuples(index=False)]
    return pd.DataFrame(resolved, index=raw.index,
                        columns=["country_iso2", "country_name", "region", "city"])


def country_columns(values: pd.Series) -> pd.DataFrame:
    """Landfeld -> (ISO2, Name), ebenfalls ueber eindeutige Werte."""
    values = values.astype("string")
    cache = {v: normalize_country(v) for v in values.dropna().unique()}
    iso = values.map(lambda v: cache.get(v, (None, None))[0] if pd.notna(v) else None)
    name = values.map(lambda v: cache.get(v, (None, None))[1] if pd.notna(v) else None)
    return pd.DataFrame({"country_iso2": iso, "country_name": name})


def iso2_to_name(values: pd.Series) -> pd.Series:
    return values.astype("string").map(lambda v: COUNTRY_NAMES.get(v) if pd.notna(v) else None)


def family_label(codes: pd.Series) -> pd.Series:
    return codes.astype("string").map(lambda c: FAMILIES.get(c, c) if pd.notna(c) else None)


def coalesce(*series: pd.Series) -> pd.Series:
    """Erste nicht-leere Angabe je Zeile."""
    out = series[0].copy()
    for other in series[1:]:
        out = out.where(out.notna() & (out.astype("string") != ""), other)
    return out
