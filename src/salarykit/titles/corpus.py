"""Trainingskorpus fuer den Jobtitel-Klassifikator.

Quellen der Labels (schwache Supervision):

1. Die Aliase der Taxonomie selbst - saubere, eindeutige Beispiele.
2. Alle eindeutigen gesaeuberten Titel aus den Rohdaten, die der Regel-Matcher
   mit ausreichender Sicherheit zuordnet.

Damit lernt das Modell die Formulierungen der echten Anzeigen, nicht nur das
Woerterbuch - und generalisiert auf die 40 % Titel, die keine Regel trifft.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

import pandas as pd

from salarykit import paths
from salarykit.titles.clean import clean_title
from salarykit.titles.match import match_title
from salarykit.titles.taxonomy import all_aliases

#: Ab dieser Regel-Sicherheit wird ein Titel als Label uebernommen.
MIN_RULE_CONFIDENCE = 0.70
#: Deckel je Klasse, damit "Software Engineer" das Modell nicht dominiert.
MAX_PER_CLASS = 4_000
#: Gewicht der Wortbuch-Beispiele gegenueber echten Anzeigentiteln.
ALIAS_WEIGHT = 3.0


@dataclass
class Corpus:
    texts: list[str]
    labels: list[str]
    weights: list[float]

    def __len__(self) -> int:
        return len(self.texts)

    def class_counts(self) -> Counter:
        return Counter(self.labels)


def raw_titles() -> pd.Series:
    """Alle Rohtitel aus den Mikrodatenquellen, mit Haeufigkeit."""
    frames: list[pd.Series] = []

    postings = paths.RAW_HF / "tech_job_postings" / "jobs_L.parquet"
    if postings.exists():
        frames.append(pd.read_parquet(postings, columns=["title"])["title"])

    eu_jobs = paths.RAW_HF / "eu_tech_jobs" / "jobs.parquet"
    if eu_jobs.exists():
        frames.append(pd.read_parquet(eu_jobs, columns=["title"])["title"])

    aijobs = paths.RAW_AIJOBS / "salaries.csv"
    if aijobs.exists():
        frames.append(pd.read_csv(aijobs, usecols=["job_title"])["job_title"])

    professions = (paths.RAW_HF / "data_professions" /
                   "salary_prediction_data_professions.csv")
    if professions.exists():
        frames.append(pd.read_csv(professions, usecols=["DESIGNATION"])["DESIGNATION"])

    if not frames:
        raise FileNotFoundError(
            f"Keine Rohdaten unter {paths.RAW}. Erst scripts/fetch_salary_sources.sh laufen lassen."
        )
    return pd.concat(frames).dropna().astype(str).value_counts()


def build(min_confidence: float = MIN_RULE_CONFIDENCE,
          max_per_class: int = MAX_PER_CLASS) -> tuple[Corpus, dict]:
    """Korpus bauen und ein paar Kennzahlen zur Abdeckung zurueckgeben."""
    texts: list[str] = []
    labels: list[str] = []
    weights: list[float] = []

    seen: set[str] = set()
    for alias, code in all_aliases():
        if alias in seen:
            continue
        seen.add(alias)
        texts.append(alias)
        labels.append(code)
        weights.append(ALIAS_WEIGHT)

    counts = raw_titles()
    per_class: Counter = Counter()
    stats = {"unique_titles": int(len(counts)), "rows": int(counts.sum()),
             "rule_hits_unique": 0, "rule_hits_rows": 0, "capped": 0}

    for title, n in counts.items():
        cleaned = clean_title(title)
        if not cleaned.core:
            continue
        hit = match_title(cleaned.core)
        if hit is None:
            continue
        stats["rule_hits_unique"] += 1
        stats["rule_hits_rows"] += int(n)
        if hit.confidence < min_confidence:
            continue
        key = cleaned.core.lower()
        if key in seen:
            continue
        if per_class[hit.code] >= max_per_class:
            stats["capped"] += 1
            continue
        seen.add(key)
        per_class[hit.code] += 1
        texts.append(cleaned.core)
        labels.append(hit.code)
        # Haeufige Titel zaehlen mehr, aber nur gedaempft (log-Skala).
        weights.append(1.0 + min(float(n) ** 0.25, 4.0))

    stats["corpus_size"] = len(texts)
    stats["classes"] = len(set(labels))
    return Corpus(texts, labels, weights), stats
