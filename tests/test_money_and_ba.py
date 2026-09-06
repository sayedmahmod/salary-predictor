import unittest

from salarykit.money import FxTable, annual_factor
from salarykit.sources.ba_entgelt import quantile_from_brackets


class MoneyTests(unittest.TestCase):
    def test_annual_factors(self):
        self.assertEqual(annual_factor("month"), 12)
        self.assertEqual(annual_factor("hourly"), 2080)

    def test_fx_nearest_year_and_static_fallback(self):
        fx = FxTable(by_year={("EUR", 2024): 1.1})
        self.assertEqual(fx.usd_per_unit("EUR", 2025), (1.1, "empirical"))
        self.assertEqual(fx.usd_per_unit("USD", 2025), (1.0, "identity"))


class BracketQuantileTests(unittest.TestCase):
    def test_interpolates_inside_closed_bracket(self):
        self.assertEqual(quantile_from_brackets([10, 10, 0, 0, 0, 0], 0.25), 1000)

    def test_open_upper_bracket_is_unknown(self):
        self.assertIsNone(quantile_from_brackets([0, 0, 0, 0, 0, 10], 0.5))


if __name__ == "__main__":
    unittest.main()
