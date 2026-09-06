#!/usr/bin/env python3
"""Regenerate the figures embedded in the README.

    python scripts/make_plots.py

Reads the local build (``data/processed``), the trained salary model and the
evaluation reports, and writes PNGs to ``docs/img/``. The figures are derived,
aggregated views - they contain no row-level third-party data.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Circle, PathPatch  # noqa: E402
from matplotlib.path import Path as MplPath  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from salarykit import paths  # noqa: E402

# Validated categorical slots (light surface). Only the first three slots clear
# the all-pairs colour-vision gates, so no figure here uses more than three.
BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
SURFACE = "#fcfcfb"
INK, INK_SOFT, GRID = "#0b0b0b", "#52514e", "#dedcd6"

OUT = Path(__file__).resolve().parents[1] / "docs" / "img"


def style() -> None:
    plt.rcParams.update({
        "figure.facecolor": SURFACE, "axes.facecolor": SURFACE,
        "savefig.facecolor": SURFACE, "font.size": 10,
        "text.color": INK, "axes.labelcolor": INK_SOFT,
        "xtick.color": INK_SOFT, "ytick.color": INK_SOFT,
        "axes.edgecolor": GRID, "grid.color": GRID, "grid.linewidth": 0.7,
        "axes.spines.top": False, "axes.spines.right": False,
        "figure.dpi": 160, "savefig.bbox": "tight",
    })


def save(fig, name: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / name
    fig.savefig(path)
    plt.close(fig)
    print(f"  -> {path.relative_to(Path(__file__).resolve().parents[1])}")


def title(ax, text: str, subtitle: str = "") -> None:
    """Titel und Unterzeile ueber der Achse, ohne sich zu ueberlagern."""
    ax.annotate(text, xy=(0, 1), xycoords="axes fraction",
                xytext=(0, 30 if subtitle else 12), textcoords="offset points",
                fontsize=12.5, fontweight="bold", color=INK, va="bottom")
    if subtitle:
        ax.annotate(subtitle, xy=(0, 1), xycoords="axes fraction",
                    xytext=(0, 12), textcoords="offset points",
                    fontsize=9, color=INK_SOFT, va="bottom")


# ---------------------------------------------------------------- figures
def fig_calibration(report: dict) -> None:
    """Do the predicted bands contain the share of reality they claim?"""
    nominal = np.array([0.50, 0.80])
    empirical = np.array([report["interval_50_coverage"], report["interval_80_coverage"]])

    fig, ax = plt.subplots(figsize=(5.4, 4.0))
    ax.plot([0.35, 0.95], [0.35, 0.95], color=GRID, lw=1.4, ls="--", zorder=1)
    ax.annotate("perfect calibration", xy=(0.90, 0.90), xytext=(-4, 8),
                textcoords="offset points", ha="right", fontsize=8.5, color=INK_SOFT)
    ax.scatter(nominal, empirical, s=110, color=BLUE, zorder=3,
               edgecolor=SURFACE, linewidth=2)
    for x, y, label in zip(nominal, empirical, ("p25-p75", "p10-p90")):
        ax.annotate(f"{label}\n{y:.1%} of holdout", xy=(x, y), xytext=(10, -14),
                    textcoords="offset points", fontsize=9, color=INK)

    ax.set_xlim(0.35, 1.0)
    ax.set_ylim(0.35, 1.0)
    ax.set_xlabel("nominal interval width")
    ax.set_ylabel("observed coverage on holdout")
    ax.xaxis.set_major_formatter(lambda v, _: f"{v:.0%}")
    ax.yaxis.set_major_formatter(lambda v, _: f"{v:.0%}")
    ax.grid(axis="both", alpha=0.6)
    ax.set_axisbelow(True)
    title(ax, "Prediction intervals are honest",
          "A p10-p90 band should contain 80% of real salaries. It contains "
          f"{empirical[1]:.1%}.")
    save(fig, "calibration.png")


def fig_variants(variants: list[dict]) -> None:
    """What each modelling decision was worth, on the leakage-free split.

    Punkte statt Balken: alle Werte liegen dicht beieinander, und ein Balken
    muesste bei 0 beginnen - sonst luegt seine Laenge. Die Position eines
    Punktes darf dagegen auf einem gezoomten Ausschnitt sitzen.
    """
    frame = pd.DataFrame(variants).iloc[::-1]
    labels = frame["label"].tolist()
    values = (frame["medape"] * 100).to_numpy()
    colors = [ORANGE if kind == "baseline" else
              (AQUA if kind == "final" else BLUE) for kind in frame["kind"]]
    baseline = float(frame.loc[frame["kind"] == "baseline", "medape"].max() * 100)

    fig, ax = plt.subplots(figsize=(7.8, 0.55 * len(labels) + 2.1))
    y = np.arange(len(labels))
    ax.axvline(baseline, color=GRID, lw=1.4, ls="--", zorder=1)
    ax.annotate("honest baseline", xy=(baseline, len(labels) - 0.35),
                xytext=(-7, 0), textcoords="offset points", ha="right",
                fontsize=8.5, color=INK_SOFT)
    for i, (value, color) in enumerate(zip(values, colors)):
        ax.plot([min(values.min(), baseline) - 0.35, value], [i, i],
                color=color, lw=1.6, alpha=0.35, zorder=2)
        ax.scatter([value], [i], s=95, color=color, zorder=3,
                   edgecolor=SURFACE, linewidth=2)
        ax.annotate(f"{value:.1f}%", xy=(value, i), xytext=(11, 0),
                    textcoords="offset points", va="center", fontsize=9.5,
                    color=INK)

    ax.set_yticks(y, labels)
    ax.set_xlim(values.min() - 0.45, values.max() + 0.9)
    ax.set_xlabel("median absolute percentage error (lower is better)")
    # Der Ausschnitt ist knapp drei Prozentpunkte breit - ganze Prozent als
    # Tick-Label wuerden mehrfach denselben Wert anzeigen.
    ax.xaxis.set_major_formatter(lambda v, _: f"{v:.1f}%")
    ax.grid(axis="x", alpha=0.6)
    ax.set_axisbelow(True)
    ax.tick_params(axis="y", length=0)
    ax.margins(y=0.1)
    title(ax, "Where the accuracy came from",
          "Each step measured on the same duplicate-grouped holdout.")
    save(fig, "variants.png")


def fig_sources(stats: dict) -> None:
    """How much each source contributes, and how much of it is usable."""
    frame = pd.DataFrame(stats["sources"]).sort_values("rows")
    y = np.arange(len(frame))
    fig, ax = plt.subplots(figsize=(7.4, 0.5 * len(frame) + 2.2))
    ax.barh(y + 0.19, frame["rows"] / 1000, height=0.34, color=BLUE, label="rows collected")
    ax.barh(y - 0.19, frame["with_salary"] / 1000, height=0.34, color=ORANGE,
            label="rows with a comparable EUR salary")
    ax.set_yticks(y, frame["name"])
    ax.set_xlabel("thousand rows")
    ax.grid(axis="x", alpha=0.6)
    ax.set_axisbelow(True)
    ax.tick_params(axis="y", length=0)
    ax.legend(frameon=False, loc="lower right", fontsize=9)
    title(ax, "Source coverage after normalisation",
          "Official statistics enter as aggregates and carry no row-level salary.")
    save(fig, "sources.png")


def fig_bands(bands: pd.DataFrame) -> None:
    """The product itself: a predicted band per seniority level."""
    levels = bands["seniority"].tolist()
    y = np.arange(len(levels))

    fig, ax = plt.subplots(figsize=(7.2, 0.62 * len(levels) + 2.2))
    for i, row in enumerate(bands.itertuples()):
        ax.plot([row.p10 / 1000, row.p90 / 1000], [i, i], color=BLUE, lw=2.4,
                alpha=0.35, solid_capstyle="round")
        ax.plot([row.p25 / 1000, row.p75 / 1000], [i, i], color=BLUE, lw=8,
                alpha=0.75, solid_capstyle="round")
        ax.scatter([row.p50 / 1000], [i], s=70, color=INK, zorder=4,
                   edgecolor=SURFACE, linewidth=2)
        ax.annotate(f"{row.p50 / 1000:.0f}k", xy=(row.p50 / 1000, i), xytext=(0, 11),
                    textcoords="offset points", ha="center", fontsize=9, color=INK)

    ax.set_yticks(y, levels)
    ax.set_xlabel("gross annual salary (thousand EUR)")
    ax.grid(axis="x", alpha=0.6)
    ax.set_axisbelow(True)
    ax.tick_params(axis="y", length=0)
    ax.margins(y=0.16)
    title(ax, "Predicted bands - Backend Engineer, Germany",
          "Dot = median, thick bar = p25-p75, thin line = p10-p90.")
    save(fig, "bands.png")






# Kurznamen fuer die Mindmap. taxonomy.FAMILIES traegt die deutschen Labels,
# README und Figuren sind englisch, und im Kreis ist der Platz knapp.
FAMILY_SHORT: dict[str, str] = {
    "software": "Software", "data_ai": "Data & AI",
    "infrastructure": "Infrastructure", "security": "Security",
    "quality": "Test & QA", "product": "Product", "design": "Design & UX",
    "research": "Research", "it_support": "IT Support", "sales": "Sales",
    "marketing": "Marketing", "customer": "Customer", "hr": "People & HR",
    "finance": "Finance", "legal": "Legal", "operations": "Operations",
    "supply_chain": "Supply Chain", "consulting": "Consulting",
    "management": "Leadership", "engineering_industrial": "Engineering",
    "trades": "Trades", "healthcare": "Healthcare", "education": "Education",
    "hospitality": "Hospitality", "retail": "Retail",
    "transport": "Transport", "admin": "Admin", "media": "Media",
    "generic": "Generic titles", "other": "Other",
}
# Sammelfamilien: echte Titel, die zu vage fuer eine Rolle sind.
CATCH_ALL = frozenset({"generic", "other"})

R_HUB, R_FAMILY, R_ROLE = 0.17, 0.44, 0.80
LIMIT = 1.22


def _xy(radius: float, degrees: float) -> tuple[float, float]:
    angle = np.radians(degrees)
    return radius * np.cos(angle), radius * np.sin(angle)


def _radial_text(ax, radius, degrees, text, **kw):
    """Beschriftung, die vom Zentrum nach aussen laeuft und lesbar bleibt.

    Auf der linken Haelfte wuerde der Text sonst auf dem Kopf stehen, also
    wird er um 180 Grad gedreht und rechtsbuendig gesetzt.
    """
    flip = np.cos(np.radians(degrees)) < 0
    x, y = _xy(radius, degrees)
    ax.text(x, y, text, rotation=degrees + 180 * flip, rotation_mode="anchor",
            ha="right" if flip else "left", va="center", **kw)


def fig_family_map() -> None:
    """Die Taxonomie als Mindmap: 107 Rollen in 29 Berufsfamilien.

    Rein strukturell und einfarbig - eine Farbe je Familie waere huebsch, aber
    nur drei kategoriale Slots bestehen die Farbsehtests, und 29 Toene waeren
    eine Unterscheidung, die das Auge nicht treffen kann. Grau markiert
    stattdessen genau eine Aussage: die beiden Sammelfamilien.
    """
    from salarykit.titles.taxonomy import FAMILIES, ROLES

    families = [(key, [role for role in ROLES if role.family == key])
                for key in FAMILIES]
    families = [(key, roles) for key, roles in families if roles]

    # Jede Rolle bekommt denselben Winkel, dazu eine Luecke je Familie - sonst
    # klebt das Label einer Ein-Rollen-Familie am Nachbarn.
    gap = 1.0
    step = 360.0 / (len(ROLES) + gap * len(families))

    fig, ax = plt.subplots(figsize=(16.0, 16.0))
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_xlim(-LIMIT, LIMIT)
    ax.set_ylim(-LIMIT, LIMIT)

    cursor = 90.0
    for key, roles in families:
        color = INK_SOFT if key in CATCH_ALL else BLUE
        cursor -= gap * step / 2
        leaf_angles = [cursor - (i + 0.5) * step for i in range(len(roles))]
        cursor -= len(roles) * step + gap * step / 2
        family_angle = float(np.mean(leaf_angles))

        ax.plot(*zip(_xy(R_HUB, family_angle), _xy(R_FAMILY, family_angle)),
                color=color, lw=1.8, alpha=0.55, zorder=2)
        for angle in leaf_angles:
            span = R_ROLE - R_FAMILY
            vertices = [_xy(R_FAMILY, family_angle),
                        _xy(R_FAMILY + 0.55 * span, family_angle),
                        _xy(R_ROLE - 0.18 * span, angle),
                        _xy(R_ROLE, angle)]
            ax.add_patch(PathPatch(
                MplPath(vertices, [MplPath.MOVETO, MplPath.CURVE4,
                                   MplPath.CURVE4, MplPath.CURVE4]),
                facecolor="none", edgecolor=color, lw=1.1, alpha=0.42,
                zorder=2))

        for angle, role in zip(leaf_angles, roles):
            ax.scatter(*_xy(R_ROLE, angle), s=17, color=color, zorder=4)
            _radial_text(ax, R_ROLE + 0.018, angle, role.label, fontsize=8.5,
                         color=INK, zorder=5)

        ax.scatter(*_xy(R_FAMILY, family_angle), s=95, color=color, zorder=4,
                   edgecolor=SURFACE, linewidth=2)
        _radial_text(ax, R_FAMILY + 0.015, family_angle,
                     f"{FAMILY_SHORT.get(key, key)}  ({len(roles)})",
                     fontsize=10.5, fontweight="bold", color=color, zorder=3,
                     bbox={"facecolor": SURFACE, "edgecolor": "none",
                           "pad": 2.5})

    ax.add_patch(Circle((0, 0), R_HUB, facecolor=SURFACE, edgecolor=GRID,
                        lw=1.2, zorder=3))
    ax.text(0, 0.045, "107", ha="center", va="center", fontsize=34,
            fontweight="bold", color=INK, zorder=5)
    ax.text(0, -0.032, "canonical roles", ha="center", va="center",
            fontsize=11.5, color=INK, zorder=5)
    ax.text(0, -0.082, "in 29 job families", ha="center", va="center",
            fontsize=10, color=INK_SOFT, zorder=5)

    title(ax, "The job title taxonomy",
          "Every free-text title is mapped onto one of these roles - or onto "
          "nothing at all. Grey = collector families for titles too vague to "
          "place.")
    save(fig, "families.png")


# ---------------------------------------------------------------- inputs
def band_table() -> pd.DataFrame:
    from salarykit.salary.predict import SalaryPredictor

    predictor = SalaryPredictor()
    rows = []
    for level in ("junior", "mid", "senior", "staff", "principal"):
        pred = predictor.predict("Backend Engineer", country_iso2="DE", seniority=level)
        rows.append({"seniority": level.capitalize(), "p10": pred.p10_annual_eur,
                     "p25": pred.p25_annual_eur, "p50": pred.p50_annual_eur,
                     "p75": pred.p75_annual_eur, "p90": pred.p90_annual_eur})
    return pd.DataFrame(rows)




def source_stats() -> dict:
    obs = pd.read_parquet(paths.PROCESSED / "observations.parquet",
                          columns=["source", "salary_annual_eur"])
    agg = pd.read_parquet(paths.PROCESSED / "aggregates.parquet", columns=["source"])
    pretty = {
        "hf_tech_postings": "Zalize tech job postings",
        "aijobs": "aijobs.net salary index",
        "so_2025": "Stack Overflow survey 2025",
        "so_history": "Stack Overflow surveys 2018-2024 (DE)",
        "it_salary_eu": "EU IT salary survey 2018-2020 (DE)",
        "hf_german_job_postings": "Stellen-Atlas salary subset (DE)",
        "hf_eu_tech_jobs": "Aramente EU tech jobs",
        "hf_data_professions": "Salary of data professions",
        "ba_entgelt": "BA Entgeltstatistik (official)",
        "bls_oews": "BLS OEWS (official)",
        "eurostat_ses": "Eurostat SES (official)",
        "destatis_earnings": "Destatis annual earnings (official)",
    }
    rows = []
    grouped = obs.groupby("source")
    for name, part in grouped:
        rows.append({"name": pretty.get(str(name), str(name)), "rows": len(part),
                     "with_salary": int(part["salary_annual_eur"].notna().sum())})
    for name, count in agg["source"].value_counts().items():
        rows.append({"name": pretty.get(str(name), str(name)), "rows": int(count),
                     "with_salary": 0})
    return {"sources": rows}


def main() -> int:
    style()
    print("Rendering README figures ...")

    report = json.loads((paths.REPORTS / "salary_model.json").read_text())
    fig_calibration(report)

    variants_path = paths.REPORTS / "eval_variants.json"
    if variants_path.exists():
        fig_variants(json.loads(variants_path.read_text()))
    else:
        print("  (skipped variants.png - reports/eval_variants.json missing)")

    fig_sources(source_stats())
    fig_bands(band_table())
    fig_family_map()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
