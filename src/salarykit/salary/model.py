"""Quantilmodell fuer Jahresgehaelter.

Fuenf Gradient-Boosting-Modelle schaetzen bedingte Quantile auf logarithmierten
EUR-Jahresgehaeltern. Kategorische Merkmale werden explizit ordinal kodiert und
vom Estimator als Kategorien behandelt; unbekannte Werte bleiben zulaessig.

Neben den kategorischen Kontextmerkmalen bekommt das Modell eine dichte
Darstellung des Jobtitels selbst (:data:`TEXT_FEATURE`): TF-IDF ueber Wort- und
Zeichen-n-Gramme, per SVD auf :data:`TITLE_EMBEDDING_DIMS` Dimensionen
reduziert. Der Taxonomie-Code allein wirft weg, was im Titel steht - "ML
Engineer, LLM Infrastructure" und "ML Engineer" landen sonst im selben Bucket.

Bewertet wird auf einem duplikat-gruppierten Holdout: knapp 60 % der Zeilen sind
exakte Wiederholungen aus (Titel, Land, Gehalt), und ein zufaelliger Split legt
identische Datensaetze auf beide Seiten. :func:`grouped_split` verhindert das.

Die Baender werden anschliessend konform nachkalibriert (CQR): unabhaengig
trainierte Quantilmodelle treffen ihre nominale Abdeckung nur ungefaehr - mit
mehr Kapazitaet werden sie scharf, aber zu eng. Auf einer separaten
Kalibrierungsscheibe wird darum je Quantilpaar eine Verbreiterung bestimmt, die
die empirische Abdeckung auf den Sollwert zieht.
"""
from __future__ import annotations

import json
import os
import warnings
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
os.environ.setdefault("LOKY_MAX_CPU_COUNT", str(os.cpu_count() or 1))
warnings.filterwarnings("ignore", message="Could not find the number of physical cores.*")
warnings.filterwarnings("ignore", category=UserWarning,
                        module=r"joblib\.externals\.loky\.backend\.context")

from sklearn.decomposition import TruncatedSVD
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import mean_absolute_error, median_absolute_error, r2_score
from sklearn.model_selection import GroupShuffleSplit
from sklearn.pipeline import FeatureUnion
from sklearn.preprocessing import OrdinalEncoder

from salarykit.quantiles import MAX_ANNUAL_EUR, MIN_ANNUAL_EUR

MODEL_FILENAME = "salary_model.joblib"
QUANTILES = (0.10, 0.25, 0.50, 0.75, 0.90)

#: Kontext, den das Modell als Kategorien sieht.
#:
#: Bewusst *nicht* dabei: ``company_size``. Die Spalte ist ein perfekter
#: Quellenindikator - aijobs schreibt "medium (50-250)", die Stack-Overflow-
#: Umfrage numerische Klassen, die Anzeigenquellen gar nichts. Das Modell wuerde
#: daraus die Quelle ablesen und deren Gehaltsniveau uebernehmen, und ein
#: Aufrufer kann den Wert zur Vorhersagezeit ohnehin nicht sinnvoll setzen.
CAT_FEATURES = (
    "normalized_job_code", "country_iso2", "seniority", "employment_type",
    "remote_type", "record_type", "job_family", "industry", "region", "city",
)
NUM_FEATURES = ("year", "experience_years")

#: Freitext des Titels, aus dem die dichte Darstellung entsteht.
TEXT_FEATURE = "job_title_core"
TITLE_EMBEDDING_DIMS = 128
#: Vokabulardeckel, damit die SVD-Komponentenmatrix handhabbar bleibt.
TITLE_MAX_WORD_FEATURES = 30_000
TITLE_MAX_CHAR_FEATURES = 60_000

#: HistGradientBoosting laesst hoechstens 255 Kategorien je Merkmal zu. Alles
#: darueber wird auf die haeufigsten Auspraegungen des Trainings gefaltet.
MAX_CATEGORIES = 200

#: Merkmale aus den amtlichen Aggregaten (BA, BLS, Eurostat).
PRIOR_FEATURES = ("prior_role_log", "prior_country_log", "prior_level")

#: Symmetrische Quantilpaare und ihre nominale Abdeckung. Fuer sie wird die
#: Bandbreite konform nachjustiert (:meth:`SalaryModel._fit_conformal`).
CONFORMAL_PAIRS = ((0.10, 0.90, 0.80), (0.25, 0.75, 0.50))
#: Anteil der Trainingsdaten, der nur zur Kalibrierung dient.
CALIBRATION_FRACTION = 0.10

MISSING = "__missing__"
OTHER = "__other__"


@dataclass
class SalaryTrainReport:
    n_train: int
    n_test: int
    sources: dict[str, int]
    median_absolute_error_eur: float
    mean_absolute_error_eur: float
    median_absolute_percentage_error: float
    r2_log: float
    pinball_loss: float
    interval_50_coverage: float
    interval_80_coverage: float
    by_country: dict[str, dict]
    split: str = "grouped"
    n_calibration: int = 0

    def to_dict(self) -> dict:
        return {
            "n_train": self.n_train,
            "n_test": self.n_test,
            "n_calibration": self.n_calibration,
            "split": self.split,
            "sources": self.sources,
            "median_absolute_error_eur": round(self.median_absolute_error_eur, 2),
            "mean_absolute_error_eur": round(self.mean_absolute_error_eur, 2),
            "median_absolute_percentage_error": round(
                self.median_absolute_percentage_error, 4),
            "r2_log": round(self.r2_log, 4),
            "pinball_loss": round(self.pinball_loss, 2),
            "interval_50_coverage": round(self.interval_50_coverage, 4),
            "interval_80_coverage": round(self.interval_80_coverage, 4),
            "by_country": self.by_country,
            "note": ("Duplicate-grouped holdout: rows sharing (title, country, "
                     "salary) never straddle the split. Source-balanced sample "
                     "weights; intervals conformalised on a held-out "
                     "calibration slice. Intervals describe conditional data "
                     "dispersion, not a guarantee."),
        }


def training_frame(observations: pd.DataFrame) -> pd.DataFrame:
    """Plausible, klassifizierte Gehaltszeilen fuer das Modell auswaehlen."""
    salary = pd.to_numeric(observations["salary_annual_eur"], errors="coerce")
    code = observations["normalized_job_code"].astype("string")
    mask = (salary.between(MIN_ANNUAL_EUR, MAX_ANNUAL_EUR) & code.notna() &
            (code != "") & (code != "other.unknown"))
    columns = [*CAT_FEATURES, *NUM_FEATURES, TEXT_FEATURE,
               "salary_annual_eur", "source", "job_title"]
    available = [c for c in columns if c in observations.columns]
    frame = observations.loc[mask, available].copy()
    for missing in set(columns) - set(available):
        frame[missing] = pd.NA
    frame["salary_annual_eur"] = salary.loc[mask]
    return frame.reset_index(drop=True)


def grouped_split(frame: pd.DataFrame, *, test_size: float = 0.20,
                  random_state: int = 13) -> tuple[np.ndarray, np.ndarray]:
    """Duplikat-sicherer Split.

    Ein zufaelliger Split ueberschaetzt das Modell deutlich: dieselbe Anzeige
    taucht mehrfach auf, landet in Training *und* Holdout und wird dort
    wiedererkannt statt vorhergesagt. Zeilen mit identischem (Titel, Land,
    Gehalt) bilden darum eine Gruppe und bleiben zusammen.
    """
    key = (frame["job_title"].astype("string").fillna("").str.lower() + "|" +
           frame["country_iso2"].astype("string").fillna("") + "|" +
           frame["salary_annual_eur"].round(0).astype("int64").astype(str))
    groups = pd.factorize(key)[0]
    splitter = GroupShuffleSplit(n_splits=1, test_size=test_size,
                                 random_state=random_state)
    train_idx, test_idx = next(splitter.split(frame, groups=groups))
    return train_idx, test_idx


def official_prior_tables(aggregates: pd.DataFrame) -> dict[str, dict]:
    """Mediane aus den amtlichen Aggregaten als Nachschlagetabellen.

    BA und BLS decken Rollen und Laender ab, in denen die Mikrodaten duenn
    sind - fuer Deutschland stehen 63.567 amtlichen Zeilen nur gut 3.000
    Einzelbeobachtungen gegenueber.
    """
    frame = aggregates
    frame = frame[frame["p50_annual_eur"].notna() &
                  frame["normalized_job_code"].notna()]
    frame = frame[frame["sex"].astype("string") == "total"]
    value = pd.to_numeric(frame["p50_annual_eur"], errors="coerce")
    frame = frame.assign(p50_annual_eur=value)

    by_code_country = (frame.groupby(["normalized_job_code", "country_iso2"],
                                     observed=True)["p50_annual_eur"].median())
    by_code = frame.groupby("normalized_job_code", observed=True)["p50_annual_eur"].median()
    by_country = frame.groupby("country_iso2", observed=True)["p50_annual_eur"].median()
    return {
        "by_code_country": {f"{k[0]}|{k[1]}": float(v)
                            for k, v in by_code_country.items()},
        "by_code": {str(k): float(v) for k, v in by_code.items()},
        "by_country": {str(k): float(v) for k, v in by_country.items()},
    }


class SalaryModel:
    """Persistierbarer Quantil-Regressor plus Support-Metadaten."""

    def __init__(self, encoder: OrdinalEncoder, numeric_medians: dict[str, float],
                 models: dict[float, HistGradientBoostingRegressor],
                 support: dict[str, dict], max_year: int,
                 usd_per_eur: float = 1.0,
                 max_year_by_record_type: dict[str, int] | None = None,
                 category_vocab: dict[str, list[str]] | None = None,
                 title_vectorizer=None, title_svd=None,
                 prior: dict[str, dict] | None = None,
                 conformal: dict[str, float] | None = None):
        self.encoder = encoder
        self.numeric_medians = numeric_medians
        self.models = models
        self.support = support
        self.max_year = max_year
        self.usd_per_eur = usd_per_eur
        self.max_year_by_record_type = max_year_by_record_type or {}
        self.category_vocab = category_vocab or {}
        self.title_vectorizer = title_vectorizer
        self.title_svd = title_svd
        self.prior = prior or {}
        self.conformal = conformal or {}

    # ------------------------------------------------------------------
    def _prepare_categories(self, frame: pd.DataFrame) -> pd.DataFrame:
        out = pd.DataFrame(index=frame.index)
        for col in CAT_FEATURES:
            values = (frame[col] if col in frame.columns
                      else pd.Series(pd.NA, index=frame.index))
            values = values.astype("string").fillna(MISSING).replace("", MISSING)
            allowed = self.category_vocab.get(col)
            if allowed is not None:
                values = values.where(values.isin(allowed), OTHER)
            out[col] = values
        return out

    def _prior_block(self, frame: pd.DataFrame) -> np.ndarray:
        by_cc = self.prior.get("by_code_country", {})
        by_code = self.prior.get("by_code", {})
        by_country = self.prior.get("by_country", {})
        code = frame["normalized_job_code"].astype("string").fillna("")
        country = frame["country_iso2"].astype("string").fillna("")
        role, level = [], []
        for c, k in zip(code, country):
            value = by_cc.get(f"{c}|{k}")
            if value is not None:
                found = 1.0
            else:
                value = by_code.get(c)
                found = 0.5 if value is not None else 0.0
            role.append(np.log1p(value) if value else np.nan)
            level.append(found)
        country_level = [np.log1p(by_country[k]) if k in by_country else np.nan
                         for k in country]
        return np.column_stack([np.asarray(role, dtype=float),
                                np.asarray(country_level, dtype=float),
                                np.asarray(level, dtype=float)])

    def _title_block(self, frame: pd.DataFrame) -> np.ndarray:
        text = (frame[TEXT_FEATURE].astype("string").fillna("").str.lower()
                if TEXT_FEATURE in frame.columns
                else pd.Series([""] * len(frame), index=frame.index))
        return self.title_svd.transform(self.title_vectorizer.transform(text))

    def _matrix(self, frame: pd.DataFrame) -> np.ndarray:
        blocks: list[np.ndarray] = [self.encoder.transform(self._prepare_categories(frame))]
        for col in NUM_FEATURES:
            values = pd.to_numeric(frame[col], errors="coerce").fillna(
                self.numeric_medians[col])
            blocks.append(values.to_numpy(dtype=float)[:, None])
        if self.prior:
            blocks.append(self._prior_block(frame))
        if self.title_svd is not None:
            blocks.append(self._title_block(frame))
        return np.column_stack(blocks)

    # ------------------------------------------------------------------
    @staticmethod
    def _support_table(frame: pd.DataFrame) -> dict[str, dict]:
        specs = [
            ("title_country_year_seniority",
             ["normalized_job_code", "country_iso2", "year", "seniority"]),
            ("title_country_year", ["normalized_job_code", "country_iso2", "year"]),
            ("title_country", ["normalized_job_code", "country_iso2"]),
            ("title", ["normalized_job_code"]),
        ]
        result: dict[str, dict] = {}
        clean = frame.copy()
        for col in ("normalized_job_code", "country_iso2", "seniority"):
            clean[col] = clean[col].astype("string").fillna(MISSING)
        for name, columns in specs:
            grouped = clean.groupby(columns, dropna=False, observed=True)
            for key, part in grouped:
                values = key if isinstance(key, tuple) else (key,)
                encoded = "|".join([name, *(str(v) for v in values)])
                result[encoded] = {
                    "n": int(len(part)),
                    "sources": sorted(part.source.dropna().astype(str).unique().tolist()),
                }
        return result

    @staticmethod
    def _build_vocab(frame: pd.DataFrame) -> dict[str, list[str]]:
        """Hochkardinale Kategorien auf die haeufigsten Auspraegungen falten."""
        vocab: dict[str, list[str]] = {}
        for col in CAT_FEATURES:
            values = frame[col].astype("string").fillna(MISSING).replace("", MISSING)
            if values.nunique() > MAX_CATEGORIES:
                top = values.value_counts().head(MAX_CATEGORIES - 1).index.tolist()
                vocab[col] = [*top, MISSING]
        return vocab

    @staticmethod
    def _build_title_encoder(texts: pd.Series, dims: int, random_state: int):
        """Dichte Titeldarstellung lernen, oder ``(None, None)``.

        Ohne brauchbaren Text - etwa in einem Minimaldatensatz ohne
        ``job_title_core`` - traegt die Darstellung nichts bei und der
        Vektorisierer haette ohnehin ein leeres Vokabular.
        """
        usable = texts[texts.str.len() > 0]
        if len(usable) < 50:
            return None, None
        vectorizer = FeatureUnion([
            ("word", TfidfVectorizer(analyzer="word", ngram_range=(1, 2),
                                     sublinear_tf=True, min_df=3,
                                     max_features=TITLE_MAX_WORD_FEATURES,
                                     token_pattern=r"[a-z0-9&+#]+")),
            ("char", TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5),
                                     sublinear_tf=True, min_df=5,
                                     max_features=TITLE_MAX_CHAR_FEATURES)),
        ])
        try:
            matrix = vectorizer.fit_transform(texts)
        except ValueError:
            return None, None
        dims = min(dims, matrix.shape[1] - 1)
        if dims < 2:
            return None, None
        svd = TruncatedSVD(n_components=dims, random_state=random_state)
        svd.fit(matrix)
        # float32 reicht und halbiert die Komponentenmatrix.
        svd.components_ = svd.components_.astype(np.float32)
        return vectorizer, svd

    # ------------------------------------------------------------------
    def _raw_log_predictions(self, matrix: np.ndarray) -> dict[float, np.ndarray]:
        return {q: self.models[q].predict(matrix) for q in QUANTILES}

    def _fit_conformal(self, matrix: np.ndarray, y_log: np.ndarray) -> dict[str, float]:
        """Bandbreiten so nachziehen, dass die Abdeckung stimmt (CQR).

        Fuer ein Paar (lo, hi) ist der Konformitaetswert
        ``max(lo(x) - y, y - hi(x))``: positiv, wenn der Punkt ausserhalb liegt,
        negativ, wenn er komfortabel innerhalb liegt. Das (1-alpha)-Quantil
        dieser Werte ist genau die Verbreiterung, die auf der Kalibrierscheibe
        die nominale Abdeckung herstellt - und sie ist auch negativ zulaessig,
        wenn die Baender zu weit waren.
        """
        if len(y_log) < 200:
            return {}
        predicted = self._raw_log_predictions(matrix)
        offsets: dict[str, float] = {}
        n = len(y_log)
        for low, high, target in CONFORMAL_PAIRS:
            score = np.maximum(predicted[low] - y_log, y_log - predicted[high])
            # Endliche-Stichproben-Korrektur der konformen Vorhersage.
            level = min(1.0, target * (1 + 1 / n))
            offsets[f"{low:.2f}|{high:.2f}"] = float(np.quantile(score, level))
        return offsets

    def _apply_conformal(self, predicted: dict[float, np.ndarray]) -> dict[float, np.ndarray]:
        if not self.conformal:
            return predicted
        out = dict(predicted)
        for low, high, _ in CONFORMAL_PAIRS:
            offset = self.conformal.get(f"{low:.2f}|{high:.2f}")
            if offset is None:
                continue
            out[low] = out[low] - offset
            out[high] = out[high] + offset
        return out

    # ------------------------------------------------------------------
    @classmethod
    def train(cls, observations: pd.DataFrame, *, aggregates: pd.DataFrame | None = None,
              test_size: float = 0.20, random_state: int = 13, max_iter: int = 400,
              learning_rate: float = 0.05, max_leaf_nodes: int = 63,
              title_dims: int = TITLE_EMBEDDING_DIMS,
              usd_per_eur: float = 1.0) -> tuple["SalaryModel", SalaryTrainReport]:
        frame = training_frame(observations)
        if len(frame) < 100:
            raise ValueError("Mindestens 100 valide Gehaltsbeobachtungen erforderlich")

        train_idx, test_idx = grouped_split(frame, test_size=test_size,
                                            random_state=random_state)
        train_frame = frame.iloc[train_idx]

        vocab = cls._build_vocab(train_frame)
        prior = (official_prior_tables(aggregates) if aggregates is not None
                 and len(aggregates) else {})
        title_texts = train_frame[TEXT_FEATURE].astype("string").fillna("").str.lower()
        vectorizer, svd = cls._build_title_encoder(title_texts, title_dims, random_state)

        numeric_medians = {
            col: float(pd.to_numeric(train_frame[col], errors="coerce").median())
            for col in NUM_FEATURES
        }
        numeric_medians = {k: (v if np.isfinite(v) else 0.0)
                           for k, v in numeric_medians.items()}
        max_year_by_record_type = {
            str(kind): int(pd.to_numeric(part.year, errors="coerce").max())
            for kind, part in frame.groupby("record_type")
        }

        shell = cls(OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=-1,
                                   encoded_missing_value=-1, dtype=np.float64),
                    numeric_medians, {}, {},
                    int(pd.to_numeric(frame.year, errors="coerce").max()),
                    usd_per_eur, max_year_by_record_type, vocab, vectorizer, svd, prior)
        shell.encoder.fit(shell._prepare_categories(train_frame))

        # Eine Scheibe des Trainings bleibt fuer die konforme Kalibrierung
        # unberuehrt - sie darf nicht in die Baeume eingegangen sein.
        fit_idx, calib_idx = grouped_split(
            train_frame.reset_index(drop=True),
            test_size=CALIBRATION_FRACTION, random_state=random_state + 1)
        fit_rows = train_idx[fit_idx]
        calib_rows = train_idx[calib_idx]

        x_fit = shell._matrix(frame.iloc[fit_rows])
        x_calib = shell._matrix(frame.iloc[calib_rows])
        x_test = shell._matrix(frame.iloc[test_idx])
        y = np.log1p(frame.salary_annual_eur.to_numpy(dtype=float))

        # Jede Quelle erhaelt insgesamt dasselbe Gewicht. Sonst wuerde eine
        # einzelne grosse Posting-Quelle das Modell fast vollstaendig bestimmen.
        fit_sources = frame.iloc[fit_rows].source.astype(str)
        source_counts = fit_sources.value_counts()
        weights = fit_sources.map(
            lambda source: len(fit_sources) / (len(source_counts) * source_counts[source])
        ).to_numpy(dtype=float)

        models = {}
        predictions = {}
        categorical = list(range(len(CAT_FEATURES)))
        for quantile in QUANTILES:
            estimator = HistGradientBoostingRegressor(
                loss="quantile", quantile=quantile, learning_rate=learning_rate,
                max_iter=max_iter, max_leaf_nodes=max_leaf_nodes,
                min_samples_leaf=30, l2_regularization=0.15,
                categorical_features=categorical, early_stopping=True,
                validation_fraction=0.10, n_iter_no_change=25,
                random_state=random_state,
            )
            estimator.fit(x_fit, y[fit_rows], sample_weight=weights)
            models[quantile] = estimator

        shell.models = models
        shell.support = cls._support_table(frame)
        shell.conformal = shell._fit_conformal(x_calib, y[calib_rows])

        predictions = {q: np.expm1(v) for q, v in
                       shell._apply_conformal(shell._raw_log_predictions(x_test)).items()}
        stacked = np.sort(np.maximum(
            np.column_stack([predictions[q] for q in QUANTILES]), 0), axis=1)
        predictions = {q: stacked[:, i] for i, q in enumerate(QUANTILES)}
        test_frame = frame.iloc[test_idx]
        actual = test_frame.salary_annual_eur.to_numpy(dtype=float)
        report = cls._report(actual, predictions, test_frame, frame,
                             len(fit_rows), len(test_idx))
        report.n_calibration = len(calib_rows)
        return shell, report

    @staticmethod
    def _report(actual, predictions, test_frame, frame, n_train, n_test
                ) -> SalaryTrainReport:
        median = predictions[0.50]
        ape = np.abs(actual - median) / actual
        pinball = float(np.mean([
            np.mean(np.maximum(q * (actual - predictions[q]),
                               (q - 1) * (actual - predictions[q])))
            for q in QUANTILES
        ]))
        countries = test_frame.country_iso2.astype("string").fillna("").to_numpy()
        by_country = {}
        for iso in pd.Series(countries).value_counts().head(8).index:
            mask = countries == iso
            if mask.sum() < 100 or not iso:
                continue
            by_country[str(iso)] = {
                "n": int(mask.sum()),
                "medape": round(float(np.median(ape[mask])), 4),
                "medae_eur": round(float(np.median(np.abs(actual - median)[mask])), 2),
            }
        return SalaryTrainReport(
            n_train=n_train, n_test=n_test,
            sources={str(k): int(v) for k, v in frame.source.value_counts().items()},
            median_absolute_error_eur=float(median_absolute_error(actual, median)),
            mean_absolute_error_eur=float(mean_absolute_error(actual, median)),
            median_absolute_percentage_error=float(np.median(ape)),
            r2_log=float(r2_score(np.log1p(actual), np.log1p(np.maximum(median, 0)))),
            pinball_loss=pinball,
            interval_50_coverage=float(np.mean(
                (actual >= predictions[0.25]) & (actual <= predictions[0.75]))),
            interval_80_coverage=float(np.mean(
                (actual >= predictions[0.10]) & (actual <= predictions[0.90]))),
            by_country=by_country,
        )

    # ------------------------------------------------------------------
    def predict(self, frame: pd.DataFrame) -> pd.DataFrame:
        if not self.models:
            raise RuntimeError("SalaryModel enthaelt keine trainierten Regressoren")
        matrix = self._matrix(frame)
        adjusted = self._apply_conformal(self._raw_log_predictions(matrix))
        raw = np.column_stack([np.expm1(adjusted[q]) for q in QUANTILES])
        # Quantilmodelle werden unabhaengig trainiert und koennen sich selten
        # kreuzen. Sortieren erzwingt eine gueltige Vorhersageverteilung.
        raw = np.sort(np.maximum(raw, 0), axis=1)
        return pd.DataFrame(raw, index=frame.index,
                            columns=[f"p{int(q * 100):02d}_annual_eur" for q in QUANTILES])

    def support_for(self, code: str, country: str | None, year: int,
                    seniority: str | None, min_support: int = 10
                    ) -> tuple[str, int, list[str]]:
        candidates = [
            ("title_country_year_seniority", [code, country or MISSING, year,
                                              seniority or MISSING]),
            ("title_country_year", [code, country or MISSING, year]),
            ("title_country", [code, country or MISSING]),
            ("title", [code]),
        ]
        for name, values in candidates:
            key = "|".join([name, *(str(v) for v in values)])
            if key in self.support and int(self.support[key]["n"]) >= min_support:
                item = self.support[key]
                return name, int(item["n"]), list(item["sources"])
        return "none", 0, []

    # ------------------------------------------------------------------
    def save(self, path: str | Path) -> Path:
        import joblib

        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump({
            "encoder": self.encoder, "numeric_medians": self.numeric_medians,
            "models": self.models, "support": self.support,
            "max_year": self.max_year, "usd_per_eur": self.usd_per_eur,
            "max_year_by_record_type": self.max_year_by_record_type,
            "category_vocab": self.category_vocab,
            "title_vectorizer": self.title_vectorizer, "title_svd": self.title_svd,
            "prior": self.prior, "conformal": self.conformal,
        }, path, compress=3)
        return path

    @classmethod
    def load(cls, path: str | Path) -> "SalaryModel":
        import joblib

        blob = joblib.load(Path(path))
        return cls(blob["encoder"], blob["numeric_medians"], blob["models"],
                   blob.get("support", {}), blob["max_year"],
                   blob.get("usd_per_eur", 1.0),
                   blob.get("max_year_by_record_type", {}),
                   blob.get("category_vocab", {}),
                   blob.get("title_vectorizer"), blob.get("title_svd"),
                   blob.get("prior", {}), blob.get("conformal", {}))


def write_report(report: SalaryTrainReport, path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report.to_dict(), indent=2, ensure_ascii=False))
    return path
