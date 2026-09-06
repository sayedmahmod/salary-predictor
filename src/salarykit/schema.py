"""Das einheitliche Zielformat.

Drei Tabellen, weil die Quellen zwei grundverschiedene Kornungen haben:

``observations``
    Mikrodaten: eine Zeile = eine einzelne Gehaltsangabe (Umfrageantwort oder
    Stellenanzeige). Quellen: Stack Overflow 2025, aijobs.net, HF Tech Job
    Postings, HF EU Tech Jobs, HF Data Professions.

``aggregates``
    Amtliche/aggregierte Statistik: eine Zeile = eine Tabellenzelle
    (Beruf x Region x Jahr x Geschlecht) mit fertigen Quantilen.
    Quellen: BLS OEWS, BA Entgeltstatistik, Eurostat SES.

``quantiles``
    Aus ``observations`` selbst gerechnete Verteilungen je
    (normalisierter Jobtitel x Land x Jahr [x Seniority]).

Alle drei teilen sich die Schluesselspalten ``normalized_job_title``,
``year``, ``country_iso2`` - darueber sind sie joinbar.
"""
from __future__ import annotations

# --------------------------------------------------------------------------
# kontrollierte Vokabulare
# --------------------------------------------------------------------------

SENIORITY_LEVELS = [
    "intern",       # Praktikum, Werkstudent, Trainee
    "entry",        # Berufseinsteiger, Graduate, Junior
    "junior",
    "mid",
    "senior",
    "staff",
    "principal",
    "lead",         # Team-/Gruppenleitung, Tech Lead
    "head",         # Head of, Bereichsleitung
    "director",
    "executive",    # C-Level, VP, Geschaeftsfuehrung
]
#: grobe Ordnung, damit man vergleichen/sortieren kann
SENIORITY_RANK = {name: i for i, name in enumerate(SENIORITY_LEVELS)}

EMPLOYMENT_TYPES = [
    "full_time", "part_time", "contract", "freelance",
    "internship", "temporary", "apprenticeship", "working_student",
]

REMOTE_TYPES = ["onsite", "hybrid", "remote"]

SALARY_PERIODS = ["year", "month", "week", "day", "hour"]

RECORD_TYPES = ["survey_response", "job_posting"]

#: Wie der normalisierte Titel zustande kam - wichtig fuer Vertrauen/Filter.
NORM_METHODS = [
    "rule", "model", "source_field",
    "soc_crosswalk", "kldb_crosswalk", "isco_crosswalk",
    "unmatched",
]


# --------------------------------------------------------------------------
# observations
# --------------------------------------------------------------------------

OBSERVATION_COLUMNS: dict[str, str] = {
    # Herkunft
    "obs_id":                 "string",   # stabiler Hash ueber source+row
    "source":                 "string",   # so_2025 | aijobs | hf_tech_postings | ...
    "source_dataset":         "string",   # menschenlesbarer Quellname
    "record_type":            "string",   # survey_response | job_posting
    "license":                "string",

    # Zeit
    "year":                   "Int16",    # Bezugsjahr der Gehaltsangabe
    "observed_at":            "datetime64[ns]",

    # --- Jobtitel: roh -> sauber -> normalisiert -------------------------
    "job_title":              "string",   # exakt wie in der Quelle
    "job_title_clean":        "string",   # Gendering/Noise raus, lesbar
    "job_title_core":         "string",   # zusaetzlich ohne Seniority/Ort -> Klassifikator-Input
    "normalized_job_title":   "string",   # Taxonomie-Label, z.B. "Backend Engineer"
    "normalized_job_code":    "string",   # Taxonomie-Code, z.B. "eng.backend"
    "job_family":             "string",   # z.B. "engineering"
    "norm_method":            "string",   # rule | model | source_field | unmatched
    "norm_confidence":        "float32",
    "isco08":                 "string",   # Bruecke zu Eurostat
    "soc2018":                "string",   # Bruecke zu BLS OEWS
    "kldb2010":               "string",   # Bruecke zur BA-Statistik

    # --- weitere aus dem Titel/Feldern gezogene Attribute -----------------
    "seniority":              "string",
    "seniority_source":       "string",   # title | source_field | none
    "employment_type":        "string",
    "remote_type":            "string",

    # --- Ort --------------------------------------------------------------
    "location_raw":           "string",
    "country_iso2":           "string",
    "country_name":           "string",
    "region":                 "string",   # Bundesland / US-State
    "city":                   "string",
    "location_source":        "string",   # source_field | title | none

    # --- Geld -------------------------------------------------------------
    "salary_min_raw":         "float64",
    "salary_max_raw":         "float64",
    "salary_raw":             "float64",  # Punktwert wie berichtet
    "salary_currency":        "string",
    "salary_period":          "string",   # Periode der Rohangabe
    "salary_basis":           "string",   # point | range_mid | range_min
    "salary_annual_local":    "float64",  # auf Jahr hochgerechnet, Ursprungswaehrung
    "salary_annual_eur":      "float64",
    "salary_annual_usd":      "float64",
    "fx_rate_usd_per_unit":   "float64",
    "fx_source":              "string",   # source_provided | empirical | static | identity | unknown

    # --- Quantil dieser Zeile in ihrer Vergleichsgruppe -------------------
    "salary_quantile":        "float32",  # empirischer Rang 0..1
    "salary_quantile_group":  "string",   # ueber welche Gruppe gerankt wurde
    "salary_quantile_n":      "Int32",    # Gruppengroesse

    # --- Kontext ----------------------------------------------------------
    "experience_years":       "float32",
    "company_size":           "string",
    "company_name":           "string",
    "industry":               "string",
    "education_level":        "string",
    "gender":                 "string",
    "weight":                 "float32",
}

OBSERVATION_ORDER = list(OBSERVATION_COLUMNS)


# --------------------------------------------------------------------------
# aggregates
# --------------------------------------------------------------------------

AGGREGATE_COLUMNS: dict[str, str] = {
    "agg_id":                 "string",
    "source":                 "string",   # bls_oews | ba_entgelt | eurostat_ses
    "source_dataset":         "string",
    "license":                "string",
    "year":                   "Int16",

    # Beruf im Originalschema plus Bruecke in unsere Taxonomie
    "occupation_scheme":      "string",   # SOC2018 | KldB2010 | ISCO08
    "occupation_code":        "string",
    "occupation_label":       "string",
    "occupation_level":       "string",   # total | major | minor | broad | detailed
    "normalized_job_title":   "string",
    "normalized_job_code":    "string",
    "job_family":             "string",
    "norm_method":            "string",
    "norm_confidence":        "float32",

    # Ort
    "geo_level":              "string",   # country | state | region | district
    "geo_code":               "string",
    "geo_name":               "string",
    "country_iso2":           "string",
    "region":                 "string",

    # Schnitt
    "sex":                    "string",   # total | male | female
    "worktime":               "string",   # total | full_time | part_time
    "industry":               "string",
    "employment_count":       "float64",

    # Geld - immer zusaetzlich auf Jahr/EUR/USD gebracht
    "salary_currency":        "string",
    "salary_period":          "string",
    "mean_raw":               "float64",
    "p10_raw":                "float64",
    "p25_raw":                "float64",
    "p50_raw":                "float64",
    "p75_raw":                "float64",
    "p90_raw":                "float64",
    "mean_annual_eur":        "float64",
    "p10_annual_eur":         "float64",
    "p25_annual_eur":         "float64",
    "p50_annual_eur":         "float64",
    "p75_annual_eur":         "float64",
    "p90_annual_eur":         "float64",
    "mean_annual_usd":        "float64",
    "p50_annual_usd":         "float64",
    "quantile_method":        "string",   # reported | interpolated_from_brackets
}

AGGREGATE_ORDER = list(AGGREGATE_COLUMNS)


# --------------------------------------------------------------------------
# quantiles (abgeleitet aus observations)
# --------------------------------------------------------------------------

QUANTILE_COLUMNS: dict[str, str] = {
    "group_key":              "string",
    "grouping":               "string",   # title_country_year | title_country | title_year | title
    "normalized_job_title":   "string",
    "normalized_job_code":    "string",
    "job_family":             "string",
    "country_iso2":           "string",
    "year":                   "Int16",
    "seniority":              "string",
    "n":                      "Int32",
    "n_sources":              "Int16",
    "sources":                "string",
    "mean_annual_eur":        "float64",
    "p10_annual_eur":         "float64",
    "p25_annual_eur":         "float64",
    "p50_annual_eur":         "float64",
    "p75_annual_eur":         "float64",
    "p90_annual_eur":         "float64",
    "p50_annual_usd":         "float64",
}

QUANTILE_ORDER = list(QUANTILE_COLUMNS)


# --------------------------------------------------------------------------
# Helfer
# --------------------------------------------------------------------------

def conform(df, columns: dict[str, str], order: list[str]):
    """Fehlende Spalten ergaenzen, Typen setzen, Reihenfolge herstellen."""
    import pandas as pd

    df = df.copy()
    for col, dtype in columns.items():
        if col not in df.columns:
            df[col] = pd.NA
        try:
            df[col] = df[col].astype(dtype)
        except (TypeError, ValueError):
            if dtype.startswith(("Int", "float")):
                df[col] = pd.to_numeric(df[col], errors="coerce").astype(dtype)
            elif dtype.startswith("datetime"):
                df[col] = pd.to_datetime(df[col], errors="coerce", utc=True).dt.tz_localize(None)
            else:
                df[col] = df[col].astype("string")
    return df[order]


def conform_observations(df):
    return conform(df, OBSERVATION_COLUMNS, OBSERVATION_ORDER)


def conform_aggregates(df):
    return conform(df, AGGREGATE_COLUMNS, AGGREGATE_ORDER)


def conform_quantiles(df):
    return conform(df, QUANTILE_COLUMNS, QUANTILE_ORDER)
