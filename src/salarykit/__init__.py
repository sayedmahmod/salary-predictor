"""salarykit - heterogene Gehaltsquellen in ein einheitliches Format bringen.

Zwei Kernbausteine:

* :mod:`salarykit.titles` - Jobtitel saeubern, Attribute (Seniority, Ort,
  Arbeitsmodell, Vertragsart) herausloesen und den Restttitel auf eine
  kanonische Taxonomie klassifizieren.
* :mod:`salarykit.sources` + :mod:`salarykit.build` - jede Rohquelle in das
  gemeinsame Schema aus :mod:`salarykit.schema` ueberfuehren.
"""
import os

# joblib fragt auf manchen eingeschraenkten macOS-Umgebungen erfolglos die
# physischen CPU-Kerne per ``sysctl`` ab und schreibt dabei einen Traceback.
# Ein konservatives explizites Limit vermeidet das, ohne Single-Core zu erzwingen.
os.environ.setdefault("LOKY_MAX_CPU_COUNT", str(max(1, (os.cpu_count() or 2) - 1)))

from salarykit.titles.clean import clean_title, CleanedTitle
from salarykit.titles.predict import JobTitlePredictor
from salarykit.salary.predict import SalaryPrediction, SalaryPredictor

__all__ = [
    "clean_title", "CleanedTitle", "JobTitlePredictor",
    "SalaryPrediction", "SalaryPredictor",
]
__version__ = "0.1.0"
