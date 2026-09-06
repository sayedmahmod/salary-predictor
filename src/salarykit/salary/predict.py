"""Oeffentliche API: Job- und Kontextangaben rein, Gehaltsband raus."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from salarykit import paths
from salarykit.geo import normalize_country, parse_location
from salarykit.salary.model import MODEL_FILENAME, SalaryModel
from salarykit.titles.predict import JobTitlePredictor, TitlePrediction


@dataclass
class SalaryPrediction:
    job_title: str
    normalized_job_title: str
    normalized_job_code: str
    job_family: str
    title_method: str
    title_confidence: float
    country_iso2: str | None
    region: str | None
    city: str | None
    year: int
    seniority: str | None
    experience_years: float | None
    employment_type: str | None
    remote_type: str | None
    industry: str | None
    market_basis: str
    p10_annual_eur: float | None
    p25_annual_eur: float | None
    p50_annual_eur: float | None
    p75_annual_eur: float | None
    p90_annual_eur: float | None
    p50_annual_usd: float | None
    current_salary_eur: float | None
    current_salary_quantile: float | None
    support_level: str
    support_n: int
    support_sources: list[str]
    supported: bool
    reason: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


def _approx_quantile(value: float, predicted: list[float]) -> float:
    quantiles = np.asarray([0.10, 0.25, 0.50, 0.75, 0.90])
    salaries = np.asarray(predicted, dtype=float)
    unique_salary, positions = np.unique(salaries, return_index=True)
    unique_quantile = quantiles[positions]
    result = np.interp(value, unique_salary, unique_quantile,
                       left=0.05, right=0.95)
    return round(float(result), 4)


class SalaryPredictor:
    """Kombiniert Jobtitel-Normalisierung und Gehalts-Quantilmodell."""

    def __init__(self, model_path: str | Path | None = None, *,
                 title_predictor: JobTitlePredictor | None = None):
        path = Path(model_path) if model_path else paths.MODELS / MODEL_FILENAME
        if not path.exists():
            raise FileNotFoundError(
                f"Kein Gehaltsmodell unter {path}. Erst "
                "scripts/train_salary_model.py ausfuehren."
            )
        self.model = SalaryModel.load(path)
        self.title_predictor = title_predictor or JobTitlePredictor()

    def predict(self, job_title: str, *, location: str | None = None,
                country_iso2: str | None = None, year: int | None = None,
                seniority: str | None = None, experience_years: float | None = None,
                employment_type: str | None = None,
                remote_type: str | None = None,
                industry: str | None = None,
                market_basis: str = "survey_response",
                current_salary_eur: float | None = None) -> SalaryPrediction:
        if market_basis not in {"survey_response", "job_posting"}:
            raise ValueError("market_basis muss survey_response oder job_posting sein")
        title = self.title_predictor.predict(job_title)
        normalized_country = normalize_country(country_iso2)[0] if country_iso2 else None
        place = parse_location(location or "", default_country=normalized_country)
        country = normalized_country or place.country_iso2 or title.country_iso2
        region = place.region or title.region
        city = place.city or title.city
        default_year = self.model.max_year_by_record_type.get(
            market_basis, self.model.max_year)
        final_year = int(year or default_year)
        final_seniority = seniority or title.seniority
        final_remote = remote_type or title.remote_type
        final_employment = employment_type or title.employment_type or "full_time"
        if title.code == "other.unknown":
            return self._unsupported(title, country, region, city, final_year,
                                     final_seniority, experience_years,
                                     final_employment, final_remote, industry,
                                     market_basis, current_salary_eur,
                                     "Jobtitel konnte nicht sicher normalisiert werden")
        frame = pd.DataFrame([{
            "normalized_job_code": title.code,
            "country_iso2": country,
            "seniority": final_seniority,
            "employment_type": final_employment,
            "remote_type": final_remote,
            "record_type": market_basis,
            "job_family": title.family,
            "industry": industry,
            "region": region,
            "city": city,
            "year": final_year,
            "experience_years": experience_years,
            # Der Titel geht zusaetzlich als Text ein: der Taxonomie-Code
            # allein verliert, was ihn von seinen Geschwistern unterscheidet.
            "job_title_core": title.core,
        }])
        row = self.model.predict(frame).iloc[0]
        values = [float(row[f"p{q:02d}_annual_eur"]) for q in (10, 25, 50, 75, 90)]
        support_level, support_n, support_sources = self.model.support_for(
            title.code, country, final_year, final_seniority)
        current_quantile = (_approx_quantile(float(current_salary_eur), values)
                            if current_salary_eur is not None else None)
        return SalaryPrediction(
            job_title=job_title, normalized_job_title=title.label,
            normalized_job_code=title.code, job_family=title.family,
            title_method=title.method, title_confidence=title.confidence,
            country_iso2=country, region=region, city=city, year=final_year,
            seniority=final_seniority, experience_years=experience_years,
            employment_type=final_employment, remote_type=final_remote,
            industry=industry, market_basis=market_basis,
            p10_annual_eur=round(values[0], 2), p25_annual_eur=round(values[1], 2),
            p50_annual_eur=round(values[2], 2), p75_annual_eur=round(values[3], 2),
            p90_annual_eur=round(values[4], 2),
            p50_annual_usd=round(values[2] * self.model.usd_per_eur, 2),
            current_salary_eur=current_salary_eur,
            current_salary_quantile=current_quantile,
            support_level=support_level, support_n=support_n,
            support_sources=support_sources, supported=True,
        )

    @staticmethod
    def _unsupported(title: TitlePrediction, country, region, city, year,
                     seniority, experience_years, employment_type, remote_type,
                     industry, market_basis, current_salary_eur,
                     reason) -> SalaryPrediction:
        return SalaryPrediction(
            job_title=title.raw, normalized_job_title=title.label,
            normalized_job_code=title.code, job_family=title.family,
            title_method=title.method, title_confidence=title.confidence,
            country_iso2=country, region=region, city=city, year=year,
            seniority=seniority, experience_years=experience_years,
            employment_type=employment_type, remote_type=remote_type,
            industry=industry, market_basis=market_basis,
            p10_annual_eur=None, p25_annual_eur=None, p50_annual_eur=None,
            p75_annual_eur=None, p90_annual_eur=None, p50_annual_usd=None,
            current_salary_eur=current_salary_eur, current_salary_quantile=None,
            support_level="none", support_n=0, support_sources=[],
            supported=False, reason=reason,
        )
