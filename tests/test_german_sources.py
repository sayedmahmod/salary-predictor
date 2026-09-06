import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from salarykit.money import FxTable
from salarykit.sources import destatis_earnings
from salarykit.sources.it_salary_eu import _experience, _seniority
from salarykit.sources.stackoverflow_history import _mapped_devtype, _years


class GermanSourceTests(unittest.TestCase):
    def test_historical_stackoverflow_normalises_experience_and_multi_role(self):
        values = _years(pd.Series(["Less than 1 year", "7", "More than 50 years"]))
        self.assertEqual(values.tolist(), [0.5, 7.0, 51.0])
        self.assertEqual(
            _mapped_devtype("Developer, back-end;Database administrator"),
            "software.backend",
        )

    def test_it_survey_normalises_seniority_and_decimal_experience(self):
        self.assertEqual(_seniority(pd.Series(["Middle", "Senior"])).tolist(),
                         ["mid", "senior"])
        self.assertEqual(_experience(pd.Series(["3,5 years", "10"])).tolist(),
                         [3.5, 10.0])

    def test_destatis_csv_expands_three_sexes_and_suppression(self):
        content = (
            "Tabelle: 62361-0034\n" + "header\n" * 6 +
            "2025;KB10-43;Informatik;70000;65000;/;/;68000;63000\n"
            "__________\n"
        ).encode("latin-1")
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "62361-0034_00.csv").write_bytes(content)
            with patch("salarykit.sources.destatis_earnings.paths.RAW_DESTATIS", root):
                result = destatis_earnings.load(FxTable())
        self.assertEqual(len(result), 3)
        self.assertEqual(result.sex.tolist(), ["male", "female", "total"])
        self.assertTrue(pd.isna(result.loc[result.sex == "female", "p50_raw"]).all())
        self.assertEqual(float(result.loc[result.sex == "total", "p50_raw"].iloc[0]),
                         63_000)


if __name__ == "__main__":
    unittest.main()
