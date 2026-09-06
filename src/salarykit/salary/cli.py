"""Kommandozeile fuer Gehaltsvorhersagen."""
from __future__ import annotations

import argparse
import json

from salarykit.salary.predict import SalaryPredictor


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Jahresgehalt und Quantilband aus Jobtitel und Kontext schaetzen")
    parser.add_argument("job_title")
    parser.add_argument("--location")
    parser.add_argument("--country")
    parser.add_argument("--year", type=int)
    parser.add_argument("--seniority")
    parser.add_argument("--experience", type=float)
    parser.add_argument("--employment-type")
    parser.add_argument("--remote-type", choices=["onsite", "hybrid", "remote"])
    parser.add_argument("--industry", help="Branche, z. B. 'Software Development'")
    parser.add_argument("--market-basis", choices=["survey_response", "job_posting"],
                        default="survey_response")
    parser.add_argument("--current-salary-eur", type=float)
    parser.add_argument("--model-path")
    args = parser.parse_args(argv)
    predictor = SalaryPredictor(model_path=args.model_path)
    result = predictor.predict(
        args.job_title, location=args.location, country_iso2=args.country,
        year=args.year, seniority=args.seniority,
        experience_years=args.experience, employment_type=args.employment_type,
        remote_type=args.remote_type, industry=args.industry,
        market_basis=args.market_basis,
        current_salary_eur=args.current_salary_eur,
    )
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    return 0 if result.supported else 2


if __name__ == "__main__":
    raise SystemExit(main())
