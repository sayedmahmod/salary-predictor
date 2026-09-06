import unittest

import pandas as pd

from salarykit import schema
from salarykit.salary.model import (SalaryModel, grouped_split,
                                    training_frame)
from salarykit.salary.predict import _approx_quantile


class SalaryModelTests(unittest.TestCase):
    def _observations(self):
        rows = []
        for i in range(160):
            rows.append({
                "obs_id": f"s{i}",
                "source": "survey_a" if i % 2 else "posting_b",
                "record_type": "survey_response" if i % 2 else "job_posting",
                "normalized_job_code": "software.backend" if i % 3 else "data.scientist",
                "normalized_job_title": "Backend Engineer" if i % 3 else "Data Scientist",
                "job_family": "software" if i % 3 else "data_ai",
                "country_iso2": "DE" if i % 4 else "US",
                "seniority": "senior" if i % 2 else "mid",
                "employment_type": "full_time",
                "remote_type": "remote" if i % 3 else "hybrid",
                "year": 2024 + i % 2,
                "experience_years": 3 + i % 12,
                "salary_annual_eur": 45_000 + i * 500,
            })
        return schema.conform_observations(pd.DataFrame(rows))

    def test_training_frame_excludes_unknown_and_outlier(self):
        observations = self._observations()
        observations.loc[0, "normalized_job_code"] = "other.unknown"
        observations.loc[1, "salary_annual_eur"] = 20_000_000
        self.assertEqual(len(training_frame(observations)), 158)

    def test_quantile_models_return_monotone_values(self):
        model, report = SalaryModel.train(self._observations(), test_size=0.2,
                                          max_iter=8, random_state=3)
        sample = self._observations().iloc[:2]
        result = model.predict(sample)
        for row in result.itertuples(index=False):
            self.assertEqual(list(row), sorted(row))
        # n_train zaehlt nur die Zeilen, die in die Baeume eingegangen sind;
        # die Kalibrierscheibe fuer die konformen Baender kommt extra.
        self.assertEqual(report.n_train + report.n_calibration + report.n_test, 160)
        self.assertGreater(report.n_calibration, 0)

    def test_grouped_split_keeps_duplicate_rows_on_one_side(self):
        """Dieselbe Anzeige darf nicht in Training *und* Holdout stehen.

        Knapp 60 % der echten Zeilen sind exakte Wiederholungen; ein
        zufaelliger Split laesst das Modell sie wiedererkennen statt
        vorhersagen und schoent die Kennzahlen.
        """
        rows = []
        for i in range(200):
            rows.append({
                "obs_id": f"d{i}", "source": "posting_b", "record_type": "job_posting",
                "job_title": f"Backend Engineer {i % 25}",
                "normalized_job_code": "software.backend",
                "normalized_job_title": "Backend Engineer", "job_family": "software",
                "country_iso2": "DE", "seniority": "senior",
                "employment_type": "full_time", "remote_type": "remote",
                "year": 2025, "experience_years": 5,
                "salary_annual_eur": 60_000 + (i % 25) * 1_000,
            })
        frame = training_frame(schema.conform_observations(pd.DataFrame(rows)))
        train_idx, test_idx = grouped_split(frame, test_size=0.3, random_state=7)

        def keys(idx):
            part = frame.iloc[idx]
            return set(zip(part.job_title.astype(str),
                           part.salary_annual_eur.round(0)))

        self.assertTrue(keys(train_idx).isdisjoint(keys(test_idx)))
        self.assertEqual(len(train_idx) + len(test_idx), len(frame))

    def test_current_salary_interpolation(self):
        self.assertEqual(_approx_quantile(70_000, [40_000, 55_000, 70_000,
                                                   90_000, 120_000]), 0.5)


if __name__ == "__main__":
    unittest.main()
