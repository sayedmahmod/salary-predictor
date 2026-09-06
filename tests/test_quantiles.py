import unittest

import pandas as pd

from salarykit import schema
from salarykit.quantiles import attach_salary_quantiles, build_quantile_table


class QuantileTests(unittest.TestCase):
    def _observations(self):
        rows = []
        for i, salary in enumerate(range(40_000, 80_000, 2_000)):
            rows.append({
                "obs_id": f"x{i}", "source": "test", "year": 2025,
                "normalized_job_code": "software.backend",
                "normalized_job_title": "Backend Engineer", "job_family": "software",
                "country_iso2": "DE", "seniority": "senior",
                "salary_annual_eur": salary, "salary_annual_usd": salary * 1.1,
            })
        return schema.conform_observations(pd.DataFrame(rows))

    def test_attaches_bounded_rank_and_specific_group(self):
        result = attach_salary_quantiles(self._observations(), min_group_size=10)
        self.assertTrue(result.salary_quantile.between(0, 1).all())
        self.assertEqual(set(result.salary_quantile_group.dropna()),
                         {"title_country_year_seniority"})
        self.assertEqual(set(result.salary_quantile_n.dropna()), {20})

    def test_builds_monotone_summary(self):
        result = build_quantile_table(self._observations(), min_group_size=10)
        row = result[result.grouping == "title_country_year_seniority"].iloc[0]
        values = [row.p10_annual_eur, row.p25_annual_eur, row.p50_annual_eur,
                  row.p75_annual_eur, row.p90_annual_eur]
        self.assertEqual(values, sorted(values))
        self.assertEqual(row.n, 20)

    def test_outlier_is_retained_but_not_ranked(self):
        observations = self._observations()
        observations.loc[0, "salary_annual_eur"] = 20_000_000
        result = attach_salary_quantiles(observations, min_group_size=10)
        self.assertTrue(pd.isna(result.loc[0, "salary_quantile"]))
        self.assertEqual(result.loc[0, "salary_annual_eur"], 20_000_000)


if __name__ == "__main__":
    unittest.main()
