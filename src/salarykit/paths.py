"""Zentrale Pfade. Alles relativ zum Projektwurzelverzeichnis."""
from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(os.environ.get("SALARYKIT_ROOT", Path(__file__).resolve().parents[2]))

RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"
INTERIM = ROOT / "data" / "interim"
MODELS = ROOT / "models"
REPORTS = ROOT / "reports"

RAW_STACKOVERFLOW = RAW / "stackoverflow_2025"
RAW_AIJOBS = RAW / "aijobs"
RAW_HF = RAW / "huggingface"
RAW_BLS = RAW / "bls_oews"
RAW_BA = RAW / "ba"
RAW_EUROSTAT = RAW / "eurostat_ses"


def ensure_dirs() -> None:
    for p in (PROCESSED, INTERIM, MODELS, REPORTS):
        p.mkdir(parents=True, exist_ok=True)
