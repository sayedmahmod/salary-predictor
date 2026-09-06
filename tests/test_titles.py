import unittest

from salarykit import JobTitlePredictor, clean_title


class TitleCleaningTests(unittest.TestCase):
    def test_gender_location_and_contract_are_removed(self):
        title = clean_title("Sr. Softwareentwickler:in (m/w/d) - München, Vollzeit")
        self.assertEqual(title.clean, "Sr. Softwareentwickler")
        self.assertEqual(title.core, "Softwareentwickler")
        self.assertEqual(title.seniority, "senior")
        self.assertEqual(title.employment_type, "full_time")
        self.assertEqual(title.country_iso2, "DE")
        self.assertEqual(title.city, "Muenchen")
        self.assertTrue(title.had_gender_marker)

    def test_rule_predictor_is_deterministic_without_model(self):
        prediction = JobTitlePredictor(use_model=False).predict(
            "Head of Engineering | Remote Germany")
        self.assertEqual(prediction.code, "management.engineering")
        self.assertEqual(prediction.seniority, "head")
        self.assertEqual(prediction.remote_type, "remote")
        self.assertEqual(prediction.method, "rule")

    def test_staff_is_a_level_before_a_role_but_not_a_noun(self):
        """"Staff" ist nur vor einer Rolle eine Stufe.

        Eine Whitelist der Folgewoerter greift zu kurz - die Tech-Vokabeln
        dahinter sind ein offener Long Tail.
        """
        for title in ("Staff Backend Engineer", "Staff Site Reliability Engineer",
                      "Staff FPGA Engineer", "Staff Product Designer"):
            with self.subTest(title=title):
                self.assertEqual(clean_title(title).seniority, "staff")

        for title in ("Staff Nurse", "Staff Accountant", "Chief of Staff",
                      "Member of Technical Staff", "Kitchen Staff"):
            with self.subTest(title=title):
                self.assertNotEqual(clean_title(title).seniority, "staff")

    def test_empty_title_is_unmatched(self):
        prediction = JobTitlePredictor(use_model=False).predict("")
        self.assertEqual(prediction.code, "other.unknown")
        self.assertEqual(prediction.method, "unmatched")


if __name__ == "__main__":
    unittest.main()
