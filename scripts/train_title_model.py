#!/usr/bin/env python3
"""Trainiert den Jobtitel-Klassifikator und schreibt Modell + Bericht.

    python scripts/train_title_model.py [--max-per-class 4000] [--min-confidence 0.7]

Ausgabe:
    models/title_model.joblib      das Modell
    reports/title_model.json       Kennzahlen (Accuracy, Macro-F1, je Klasse)
    reports/title_coverage.json    wie viel die Modellschicht zusaetzlich abdeckt
"""
from __future__ import annotations

import argparse
import json
import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from salarykit import paths                                    # noqa: E402
from salarykit.titles import corpus as corpus_mod              # noqa: E402
from salarykit.titles.clean import clean_title                 # noqa: E402
from salarykit.titles.match import match_title                 # noqa: E402
from salarykit.titles.model import (MODEL_FILENAME, TitleModel,  # noqa: E402
                                    write_report)
from salarykit.titles.predict import MIN_MODEL_CONFIDENCE      # noqa: E402
from salarykit.titles.taxonomy import role                     # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--max-per-class", type=int, default=corpus_mod.MAX_PER_CLASS)
    ap.add_argument("--min-confidence", type=float, default=corpus_mod.MIN_RULE_CONFIDENCE)
    ap.add_argument("--test-size", type=float, default=0.15)
    ap.add_argument("--seed", type=int, default=13)
    args = ap.parse_args()

    paths.ensure_dirs()

    print("Korpus bauen ...", flush=True)
    started = time.time()
    corpus, stats = corpus_mod.build(min_confidence=args.min_confidence,
                                     max_per_class=args.max_per_class)
    print(f"  {len(corpus):,} Beispiele, {stats['classes']} Klassen "
          f"({time.time() - started:.0f}s)")
    print(f"  Regelabdeckung: {stats['rule_hits_unique']:,}/{stats['unique_titles']:,} "
          f"eindeutige Titel "
          f"({stats['rule_hits_unique'] / stats['unique_titles']:.1%})")

    print("Modell trainieren ...", flush=True)
    started = time.time()
    model, report = TitleModel.train(
        corpus.texts, corpus.labels, sample_weight=corpus.weights,
        test_size=args.test_size, random_state=args.seed)
    print(f"  Accuracy {report.accuracy:.3f} | Macro-F1 {report.macro_f1:.3f} | "
          f"Weighted-F1 {report.weighted_f1:.3f} ({time.time() - started:.0f}s)")

    model_path = model.save(paths.MODELS / MODEL_FILENAME)
    write_report(report, paths.REPORTS / "title_model.json")
    print(f"  -> {model_path}")

    coverage = _coverage_gain(model, args.seed)
    (paths.REPORTS / "title_coverage.json").write_text(
        json.dumps({**stats, **coverage}, indent=2, ensure_ascii=False))
    print(f"Zusatzabdeckung durch das Modell: "
          f"{coverage['model_confident_share']:.1%} der regel-losen Titel "
          f"(Schwelle {MIN_MODEL_CONFIDENCE})")
    print("Beispiele:")
    for row in coverage["examples"]:
        print(f"  {row['core'][:44]:46} -> {row['label']}  ({row['score']})")
    return 0


def _coverage_gain(model: TitleModel, seed: int) -> dict:
    """Was faengt das Modell auf, das keine Regel trifft?"""
    counts = corpus_mod.raw_titles()
    unmatched = []
    for title in counts.index:
        cleaned = clean_title(title)
        if cleaned.core and match_title(cleaned.core) is None:
            unmatched.append(cleaned.core)
    if not unmatched:
        return {"unmatched_unique": 0, "model_confident_share": 0.0, "examples": []}

    rng = random.Random(seed)
    sample = rng.sample(unmatched, min(20_000, len(unmatched)))
    ranked = model.predict(sample, top_k=1)
    confident = [(core, r[0][0], r[0][1]) for core, r in zip(sample, ranked)
                 if r and r[0][1] >= MIN_MODEL_CONFIDENCE]
    examples = [{"core": c, "code": code, "label": role(code).label,
                 "score": round(score, 3)}
                for c, code, score in confident[:15]]
    return {
        "unmatched_unique": len(unmatched),
        "model_sample": len(sample),
        "model_confident": len(confident),
        "model_confident_share": len(confident) / len(sample),
        "examples": examples,
    }


if __name__ == "__main__":
    raise SystemExit(main())
