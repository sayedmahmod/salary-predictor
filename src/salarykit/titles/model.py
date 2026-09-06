"""Statistischer Jobtitel-Klassifikator.

Warum TF-IDF und keine Satz-Embeddings? Jobtitel sind zwei bis fuenf Tokens
lang, mehrsprachig und voller Abkuerzungen. Auf so kurzen Strings tragen
Zeichen-n-Gramme (``char_wb`` 2-5) den Grossteil der Semantik: sie fangen
"Softwareentwickler" / "Software Developer" / "Sw Dev" ueber gemeinsame
Teilstrings, ueberstehen Tippfehler und brauchen weder GPU noch Modell-Download.
Ein lineares Modell darauf ist deterministisch, in Sekunden trainiert,
wenige MB gross und liefert kalibrierbare Scores.

Der ``embed``-Backend-Hook (:func:`build_vectorizer`) ist da, falls spaeter
doch Embeddings gewuenscht sind - die Schnittstelle bleibt gleich. Das
Gehaltsmodell nutzt dieselben Titel dagegen bereits dicht: dort reduziert eine
SVD die TF-IDF-Matrix auf 128 Dimensionen (siehe :mod:`salarykit.salary.model`).

Trainiert wird mit schwacher Supervision: der Regel-Matcher
(:mod:`salarykit.titles.match`) labelt, was er sicher erkennt, das Modell
generalisiert daraus auf die Formulierungen, die keine Regel trifft.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from sklearn.calibration import CalibratedClassifierCV
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import classification_report, f1_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import FeatureUnion
from sklearn.svm import LinearSVC

from salarykit.geo import fold_variants

MODEL_FILENAME = "title_model.joblib"


def normalize_for_model(text: str) -> str:
    """Gleiche Normalisierung wie beim Regel-Matcher, damit beide dasselbe sehen."""
    variants = sorted(fold_variants(text or ""), key=len, reverse=True)
    return variants[0] if variants else ""


def build_vectorizer(backend: str = "tfidf") -> FeatureUnion:
    if backend != "tfidf":
        raise ValueError(
            f"Backend {backend!r} ist nicht eingebaut. Fuer Embeddings "
            "sentence-transformers installieren und hier einhaengen."
        )
    return FeatureUnion([
        ("word", TfidfVectorizer(
            analyzer="word", ngram_range=(1, 2), sublinear_tf=True,
            min_df=1, lowercase=True, preprocessor=normalize_for_model,
            token_pattern=r"[a-z0-9&+#]+")),
        ("char", TfidfVectorizer(
            analyzer="char_wb", ngram_range=(2, 5), sublinear_tf=True,
            min_df=2, lowercase=True, preprocessor=normalize_for_model)),
    ])


@dataclass
class TrainReport:
    n_train: int
    n_test: int
    n_classes: int
    accuracy: float
    macro_f1: float
    weighted_f1: float
    per_class: dict[str, dict] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "n_train": self.n_train, "n_test": self.n_test,
            "n_classes": self.n_classes, "accuracy": round(self.accuracy, 4),
            "macro_f1": round(self.macro_f1, 4),
            "weighted_f1": round(self.weighted_f1, 4),
            "per_class": self.per_class,
        }


class TitleModel:
    """Vektorisierer + linearer Klassifikator ueber Taxonomie-Codes."""

    def __init__(self, vectorizer, classifier, backend: str = "tfidf"):
        self.vectorizer = vectorizer
        self.classifier = classifier
        self.backend = backend

    # ------------------------------------------------------------------
    @classmethod
    def train(cls, texts: list[str], labels: list[str], *,
              sample_weight: list[float] | None = None,
              backend: str = "tfidf", test_size: float = 0.15,
              random_state: int = 13) -> tuple["TitleModel", TrainReport]:
        texts = list(texts)
        labels = list(labels)
        weights = np.asarray(sample_weight if sample_weight is not None
                             else np.ones(len(texts)), dtype=float)

        # Klassen mit <4 Beispielen lassen sich nicht stratifiziert splitten.
        counts: dict[str, int] = {}
        for lab in labels:
            counts[lab] = counts.get(lab, 0) + 1
        splittable = [i for i, lab in enumerate(labels) if counts[lab] >= 4]
        rest = [i for i, lab in enumerate(labels) if counts[lab] < 4]

        idx_train, idx_test = train_test_split(
            splittable, test_size=test_size, random_state=random_state,
            stratify=[labels[i] for i in splittable])
        idx_train = idx_train + rest

        vectorizer = build_vectorizer(backend)
        x_train = vectorizer.fit_transform([texts[i] for i in idx_train])
        x_test = vectorizer.transform([texts[i] for i in idx_test])

        # LinearSVC statt SGD: auf diesen hochdimensionalen, duennen TF-IDF-
        # Merkmalen loest der Koordinatenabstieg das Problem exakt, wo SGD nach
        # 60 Epochen noch unterwegs ist - vor allem bei den seltenen Klassen
        # (Macro-F1 0,947 -> 0,965 auf demselben Holdout).
        #
        # LinearSVC selbst liefert nur Abstaende zur Hyperebene; die
        # Reject-Option in JobTitlePredictor braucht aber Wahrscheinlichkeiten.
        # Darum die Sigmoid-Kalibrierung. ``ensemble=False`` kalibriert auf
        # kreuzvalidierten Vorhersagen und behaelt *ein* auf allen Daten
        # trainiertes Modell - sonst laegen drei Kopien im Artefakt (22 MB
        # statt 59 MB) - und schneidet dabei sogar besser ab.
        classifier = CalibratedClassifierCV(
            LinearSVC(C=1.0, class_weight="balanced", random_state=random_state),
            method="sigmoid", cv=3, ensemble=False)
        classifier.fit(x_train, [labels[i] for i in idx_train],
                       sample_weight=weights[idx_train])

        y_test = [labels[i] for i in idx_test]
        y_pred = classifier.predict(x_test)
        report = TrainReport(
            n_train=len(idx_train), n_test=len(idx_test),
            n_classes=len(set(labels)),
            accuracy=float((np.asarray(y_pred) == np.asarray(y_test)).mean()),
            macro_f1=float(f1_score(y_test, y_pred, average="macro", zero_division=0)),
            weighted_f1=float(f1_score(y_test, y_pred, average="weighted", zero_division=0)),
            per_class=classification_report(y_test, y_pred, output_dict=True,
                                            zero_division=0),
        )
        return cls(vectorizer, classifier, backend), report

    # ------------------------------------------------------------------
    def predict(self, texts: list[str], top_k: int = 3) -> list[list[tuple[str, float]]]:
        """Top-k (Code, Score) je Titel. Score ist eine normierte Wahrscheinlichkeit."""
        if not texts:
            return []
        matrix = self.vectorizer.transform(texts)
        proba = self.classifier.predict_proba(matrix)
        classes = self.classifier.classes_
        k = min(top_k, len(classes))
        out: list[list[tuple[str, float]]] = []
        for row in proba:
            total = row.sum()
            row = row / total if total > 0 else row
            order = np.argsort(row)[::-1][:k]
            out.append([(str(classes[i]), float(round(row[i], 4))) for i in order])
        return out

    # ------------------------------------------------------------------
    def save(self, path: str | Path) -> Path:
        import joblib

        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump({"vectorizer": self.vectorizer,
                     "classifier": self.classifier,
                     "backend": self.backend}, path, compress=3)
        return path

    @classmethod
    def load(cls, path: str | Path) -> "TitleModel":
        import joblib

        blob = joblib.load(Path(path))
        return cls(blob["vectorizer"], blob["classifier"], blob.get("backend", "tfidf"))


def write_report(report: TrainReport, path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report.to_dict(), indent=2, ensure_ascii=False))
    return path
