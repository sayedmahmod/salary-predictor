"""Oeffentliche API: beliebiger Jobtitel rein, normalisierter Titel raus.

    >>> from salarykit import JobTitlePredictor
    >>> p = JobTitlePredictor()
    >>> p.predict("Sr. Softwareentwickler:in (m/w/d) - München, Vollzeit").label
    'Software Engineer'

Drei Schichten, in dieser Reihenfolge:

1. **clean**  - Gendering, Vertragsart, Ort, Marketing raus (:mod:`.clean`)
2. **rule**   - Alias-Gazetteer, longest match (:mod:`.match`)
3. **model**  - TF-IDF + lineares Modell fuer alles, was Schicht 2 nicht kennt
   (:mod:`.model`); faellt weg, wenn kein trainiertes Modell vorliegt.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from salarykit import paths
from salarykit.titles.clean import CleanedTitle, clean_title
from salarykit.titles.match import match_title
from salarykit.titles.model import MODEL_FILENAME, TitleModel
from salarykit.titles.taxonomy import FAMILIES, UNKNOWN, role

#: Ab hier wird eine Modellvorhersage uebernommen; darunter bleibt es
#: "unmatched". 0.45 ist empirisch gewaehlt: darueber sind die Vorhersagen auf
#: regel-losen Titeln ueberwiegend plausibel, darunter wird es Rauschen
#: (siehe reports/title_coverage.json).
MIN_MODEL_CONFIDENCE = 0.45


@dataclass
class TitlePrediction:
    """Alles, was aus einem Rohtitel herausgeholt wurde."""

    raw: str
    clean: str
    core: str
    code: str
    label: str
    family: str
    family_label: str
    method: str                       # rule | model | unmatched
    confidence: float
    alternatives: list[tuple[str, str, float]] = field(default_factory=list)
    isco08: str | None = None
    soc2018: str | None = None
    kldb2010: str | None = None
    seniority: str | None = None
    employment_type: str | None = None
    remote_type: str | None = None
    country_iso2: str | None = None
    region: str | None = None
    city: str | None = None
    languages: list[str] = field(default_factory=list)
    had_gender_marker: bool = False

    def to_dict(self) -> dict:
        return {
            "job_title": self.raw,
            "job_title_clean": self.clean,
            "job_title_core": self.core,
            "normalized_job_title": self.label,
            "normalized_job_code": self.code,
            "job_family": self.family,
            "job_family_label": self.family_label,
            "norm_method": self.method,
            "norm_confidence": self.confidence,
            "alternatives": [
                {"code": c, "label": l, "score": s} for c, l, s in self.alternatives
            ],
            "isco08": self.isco08,
            "soc2018": self.soc2018,
            "kldb2010": self.kldb2010,
            "seniority": self.seniority,
            "employment_type": self.employment_type,
            "remote_type": self.remote_type,
            "country_iso2": self.country_iso2,
            "region": self.region,
            "city": self.city,
            "languages": self.languages,
            "had_gender_marker": self.had_gender_marker,
        }


def _best_match(c: CleanedTitle):
    """Kern und vollstaendigen Titel abgleichen, spezifischeren Treffer nehmen.

    Manche Rollen stecken gerade im Stufenwort - "Head of Engineering" ist
    Engineering Manager, der Kern "Engineering" allein nur "Engineer".
    Gewinner ist der laengere Alias-Treffer.
    """
    candidates = []
    if c.core:
        hit = match_title(c.core)
        if hit is not None:
            candidates.append(hit)
    if c.clean and c.clean != c.core:
        hit = match_title(c.clean)
        if hit is not None:
            candidates.append(hit)
    if not candidates:
        return None
    return max(candidates, key=lambda h: (len(h.matched_alias.split()), h.confidence))


class JobTitlePredictor:
    """Klassifiziert beliebige Jobtitel auf die Taxonomie.

    Ohne trainiertes Modell laeuft nur die Regelschicht - das ist bewusst so,
    damit das Paket auch ohne ``scripts/train_title_model.py`` benutzbar ist.
    """

    def __init__(self, model_path: str | Path | None = None, *,
                 use_model: bool = True,
                 min_model_confidence: float = MIN_MODEL_CONFIDENCE):
        self.min_model_confidence = min_model_confidence
        self.model: TitleModel | None = None
        if use_model:
            path = Path(model_path) if model_path else paths.MODELS / MODEL_FILENAME
            if path.exists():
                self.model = TitleModel.load(path)
            elif model_path is not None:
                raise FileNotFoundError(f"Kein Modell unter {path}")

    # ------------------------------------------------------------------
    @property
    def has_model(self) -> bool:
        return self.model is not None

    def predict(self, title: str) -> TitlePrediction:
        return self.predict_many([title])[0]

    def predict_many(self, titles: list[str]) -> list[TitlePrediction]:
        cleaned = [clean_title(t) for t in titles]
        results: list[TitlePrediction | None] = []
        pending: list[int] = []

        for i, c in enumerate(cleaned):
            hit = _best_match(c)
            if hit is not None:
                results.append(self._build(c, hit.code, "rule", hit.confidence, []))
            else:
                results.append(None)
                pending.append(i)

        if pending and self.model is not None:
            cores = [cleaned[i].core for i in pending]
            for i, ranked in zip(pending, self.model.predict(cores, top_k=3)):
                if not ranked:
                    continue
                code, score = ranked[0]
                alts = [(c, role(c).label, s) for c, s in ranked[1:]]
                if score >= self.min_model_confidence:
                    results[i] = self._build(cleaned[i], code, "model", score, alts)
                else:
                    results[i] = self._build(cleaned[i], UNKNOWN.code, "unmatched",
                                             score, [(code, role(code).label, score), *alts])

        return [r if r is not None
                else self._build(cleaned[i], UNKNOWN.code, "unmatched", 0.0, [])
                for i, r in enumerate(results)]

    # ------------------------------------------------------------------
    @staticmethod
    def _build(c: CleanedTitle, code: str, method: str, confidence: float,
               alternatives: list[tuple[str, str, float]]) -> TitlePrediction:
        r = role(code)
        return TitlePrediction(
            raw=c.raw, clean=c.clean, core=c.core,
            code=r.code, label=r.label, family=r.family,
            family_label=FAMILIES.get(r.family, r.family),
            method=method, confidence=round(float(confidence), 4),
            alternatives=alternatives,
            isco08=r.isco08, soc2018=r.soc2018, kldb2010=r.kldb2010,
            seniority=c.seniority, employment_type=c.employment_type,
            remote_type=c.remote_type, country_iso2=c.country_iso2,
            region=c.region, city=c.city, languages=c.languages,
            had_gender_marker=c.had_gender_marker,
        )
