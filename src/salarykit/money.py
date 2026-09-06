"""Gehaelter auf eine gemeinsame Einheit bringen: Jahresbrutto in EUR und USD.

Zwei Umrechnungen sind noetig.

**Periode -> Jahr.** Stundensaetze, Monats- und Tagessaetze werden mit festen
Faktoren hochgerechnet. Die Faktoren sind Konvention, keine Messung, und
deshalb hier an einer Stelle dokumentiert.

**Waehrung -> EUR/USD.** Statt einer Online-Kursabfrage werden die Kurse *aus
den Daten selbst* geschaetzt: aijobs.net liefert ``salary`` und
``salary_in_usd`` fuer dieselbe Zeile, Stack Overflow ``CompTotal`` und
``ConvertedCompYearly``. Der Median beider Verhaeltnisse je (Waehrung, Jahr)
ist der Kurs, den die Quelle selbst benutzt hat. Das haelt den Build offline
und reproduzierbar und vermeidet, dass eigene Kurse den bereits umgerechneten
Werten der Quelle widersprechen.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

from salarykit import paths

#: Wie viele Perioden ergeben ein Jahr. 2080 h = 40 h x 52 Wochen (US-Konvention,
#: die auch die Stellenanzeigen mit Stundensatz zugrunde legen), 260 Arbeitstage.
PERIOD_FACTORS: dict[str, float] = {
    "year": 1.0, "annual": 1.0, "yearly": 1.0, "pa": 1.0,
    "month": 12.0, "monthly": 12.0,
    "week": 52.0, "weekly": 52.0,
    "day": 260.0, "daily": 260.0,
    "hour": 2080.0, "hourly": 2080.0,
}

#: Nur als Rueckfallebene fuer Waehrungen, die in keiner Quelle mit
#: Umrechnung vorkommen. USD je Einheit, Stand der Quellen-Snapshots (2025).
STATIC_USD_PER_UNIT: dict[str, float] = {
    "USD": 1.0, "EUR": 1.16, "GBP": 1.34, "CHF": 1.25, "CAD": 0.73,
    "AUD": 0.65, "NZD": 0.60, "JPY": 0.0068, "CNY": 0.14, "HKD": 0.128,
    "SGD": 0.78, "INR": 0.0117, "IDR": 0.000061, "MYR": 0.24, "PHP": 0.0176,
    "THB": 0.031, "VND": 0.000038, "KRW": 0.00072, "TWD": 0.032,
    "SEK": 0.105, "NOK": 0.098, "DKK": 0.156, "ISK": 0.0080,
    "PLN": 0.275, "CZK": 0.047, "HUF": 0.0029, "RON": 0.23, "BGN": 0.594,
    "HRK": 0.154, "RSD": 0.0099, "UAH": 0.024, "RUB": 0.012,
    "TRY": 0.025, "ILS": 0.30, "AED": 0.272, "SAR": 0.267, "QAR": 0.275,
    "EGP": 0.0206, "MAD": 0.11, "ZAR": 0.057, "NGN": 0.00065, "KES": 0.0077,
    "BRL": 0.185, "MXN": 0.054, "ARS": 0.00075, "CLP": 0.00105,
    "COP": 0.00025, "PEN": 0.28, "UYU": 0.025,
}

#: Ohne die kaeme man bei "EUR -> EUR" auf einen Umweg ueber USD.
_BASE = "USD"


@dataclass
class FxTable:
    """USD je Waehrungseinheit, moeglichst je Jahr."""

    by_year: dict[tuple[str, int], float] = field(default_factory=dict)
    by_currency: dict[str, float] = field(default_factory=dict)
    source_note: str = ""

    # ------------------------------------------------------------------
    def usd_per_unit(self, currency: str | None, year: int | None = None
                     ) -> tuple[float | None, str]:
        """Kurs plus Herkunft ("empirical" / "static" / "unknown")."""
        if currency is None or currency is pd.NA or (
                isinstance(currency, float) and pd.isna(currency)) or not str(currency).strip():
            return None, "unknown"
        code = str(currency).strip().upper()[:3]
        if code == _BASE:
            return 1.0, "identity"
        if year is not None:
            rate = self.by_year.get((code, int(year)))
            if rate:
                return rate, "empirical"
            # naechstliegendes Jahr derselben Waehrung
            years = [y for c, y in self.by_year if c == code]
            if years:
                nearest = min(years, key=lambda y: abs(y - int(year)))
                return self.by_year[(code, nearest)], "empirical"
        if code in self.by_currency:
            return self.by_currency[code], "empirical"
        if code in STATIC_USD_PER_UNIT:
            return STATIC_USD_PER_UNIT[code], "static"
        return None, "unknown"

    def usd_per_eur(self, year: int | None = None) -> float:
        rate, _ = self.usd_per_unit("EUR", year)
        return rate or STATIC_USD_PER_UNIT["EUR"]

    # ------------------------------------------------------------------
    def to_dict(self) -> dict:
        return {
            "note": self.source_note,
            "by_year": {f"{c}:{y}": round(v, 8) for (c, y), v in sorted(self.by_year.items())},
            "by_currency": {c: round(v, 8) for c, v in sorted(self.by_currency.items())},
        }

    def save(self, path: str | Path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2))
        return path

    @classmethod
    def load(cls, path: str | Path) -> "FxTable":
        blob = json.loads(Path(path).read_text())
        by_year = {}
        for key, value in blob.get("by_year", {}).items():
            code, year = key.split(":")
            by_year[(code, int(year))] = float(value)
        return cls(by_year=by_year,
                   by_currency={k: float(v) for k, v in blob.get("by_currency", {}).items()},
                   source_note=blob.get("note", ""))


# --------------------------------------------------------------------------
# Kurse aus den Quellen schaetzen
# --------------------------------------------------------------------------

_MIN_OBS = 3        # weniger Beobachtungen -> Median ist Zufall


def _ratios(local: pd.Series, usd: pd.Series, currency: pd.Series,
            year: pd.Series | None) -> pd.DataFrame:
    frame = pd.DataFrame({
        "currency": currency.astype("string").str.strip().str.upper().str[:3],
        "local": pd.to_numeric(local, errors="coerce"),
        "usd": pd.to_numeric(usd, errors="coerce"),
        "year": pd.to_numeric(year, errors="coerce") if year is not None else np.nan,
    })
    frame = frame[(frame.local > 0) & (frame.usd > 0) & frame.currency.notna()]
    frame["rate"] = frame.usd / frame.local
    return frame


def build_fx_table() -> FxTable:
    """Kurse aus aijobs.net und Stack Overflow schaetzen."""
    frames: list[pd.DataFrame] = []
    notes: list[str] = []

    aijobs = paths.RAW_AIJOBS / "salaries.csv"
    if aijobs.exists():
        df = pd.read_csv(aijobs, usecols=["work_year", "salary", "salary_currency",
                                          "salary_in_usd"])
        frames.append(_ratios(df.salary, df.salary_in_usd, df.salary_currency,
                              df.work_year))
        notes.append("aijobs.net salary/salary_in_usd")

    survey = paths.RAW_STACKOVERFLOW / "survey_results_public.csv"
    if survey.exists():
        df = pd.read_csv(survey, usecols=["Currency", "CompTotal", "ConvertedCompYearly"],
                         low_memory=False)
        year = pd.Series(2025, index=df.index)
        frames.append(_ratios(df.CompTotal, df.ConvertedCompYearly, df.Currency, year))
        notes.append("Stack Overflow 2025 CompTotal/ConvertedCompYearly")

    if not frames:
        return FxTable(source_note="nur statische Rueckfallkurse")

    data = pd.concat(frames, ignore_index=True)
    by_year: dict[tuple[str, int], float] = {}
    grouped = data.dropna(subset=["year"]).groupby(["currency", "year"]).rate
    for (code, year), series in grouped:
        if len(series) >= _MIN_OBS:
            by_year[(str(code), int(year))] = float(series.median())

    by_currency: dict[str, float] = {}
    for code, series in data.groupby("currency").rate:
        if len(series) >= _MIN_OBS:
            by_currency[str(code)] = float(series.median())

    return FxTable(by_year=by_year, by_currency=by_currency,
                   source_note="Median aus " + " + ".join(notes))


# --------------------------------------------------------------------------
# Umrechnung
# --------------------------------------------------------------------------

def annual_factor(period: str | None) -> float:
    if not period:
        return 1.0
    return PERIOD_FACTORS.get(str(period).strip().lower(), 1.0)


def annualize(value, period: str | None):
    """Betrag auf Jahresbasis bringen (vektorisiert oder skalar)."""
    factor = annual_factor(period)
    if isinstance(value, pd.Series):
        return value * factor
    return None if value is None or pd.isna(value) else value * factor


def annualize_series(values: pd.Series, periods: pd.Series) -> pd.Series:
    factors = periods.astype("string").str.strip().str.lower().map(PERIOD_FACTORS)
    return pd.to_numeric(values, errors="coerce") * factors.fillna(1.0)


def convert_series(values: pd.Series, currencies: pd.Series, years: pd.Series,
                   fx: FxTable) -> pd.DataFrame:
    """-> DataFrame mit usd, eur, rate, fx_source. Einmal je Kombination gerechnet."""
    values = pd.to_numeric(values, errors="coerce")
    codes = currencies.astype("string").str.strip().str.upper().str[:3]
    yrs = pd.to_numeric(years, errors="coerce")

    keys = pd.DataFrame({"currency": codes, "year": yrs})
    unique = keys.drop_duplicates()
    lookup: dict[tuple, tuple[float | None, str]] = {}
    for code, year in unique.itertuples(index=False):
        year_int = int(year) if pd.notna(year) else None
        lookup[(code, year if pd.notna(year) else None)] = fx.usd_per_unit(code, year_int)

    rates, sources = [], []
    for code, year in keys.itertuples(index=False):
        rate, source = lookup[(code, year if pd.notna(year) else None)]
        rates.append(rate if rate is not None else np.nan)
        sources.append(source)

    rate_series = pd.Series(rates, index=values.index, dtype="float64")
    usd = values * rate_series
    eur_rates = pd.Series(
        [fx.usd_per_eur(int(y) if pd.notna(y) else None) for y in yrs],
        index=values.index, dtype="float64")
    return pd.DataFrame({
        "salary_annual_usd": usd,
        "salary_annual_eur": usd / eur_rates,
        "fx_rate_usd_per_unit": rate_series,
        "fx_source": pd.Series(sources, index=values.index, dtype="string"),
    })
