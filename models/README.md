# Trained artefacts

| File | What it is |
|---|---|
| `title_model.joblib` | TF-IDF (word + character n-grams) into a calibrated linear SVM over 107 canonical roles |
| `salary_model.joblib` | five `HistGradientBoostingRegressor` quantile models on log annual EUR salaries, plus the encoder, the title vectoriser and the conformal widening |

Neither artefact contains row-level records. `salary_model.joblib` carries a
200-entry city vocabulary, a support index that stores only a row count and the
source names per group, and a prior of 112 median values per role/country group.
That is aggregation, not redistribution - but the terms below still apply,
because the aggregates are derived from the sources.

## Model and data licensing

The source code is licensed under the [MIT Licence](LICENSE).

The pretrained models, evaluation results and derived figures are **not**
covered by the MIT License. They are published solely for non-commercial
research, educational use and portfolio demonstration.

The models incorporate data from sources including the Zalize Tech Job Postings
Salary Dataset, licensed under CC BY-NC 4.0. No source-level or row-level data
is distributed in this repository.

Commercial users must retrain the models exclusively from commercially
compatible sources.

## Intended use

SalaryKit is not intended for candidate ranking, automated hiring decisions,
individual compensation decisions or other consequential employment decisions.

It estimates a statistical distribution for a role in a place, from data that is
skewed towards tech and towards the United States. It says nothing about an
individual person, and its output is not an offer, a benchmark or advice.

## Required source notices

> - Contains information from the **Stack Overflow Developer Survey 2025**, made
>   available under the Open Database License (ODbL) 1.0; individual contents
>   under the Database Contents License (DbCL) 1.0.
> - Source: **aijobs.net** Global AI, ML and Data Science Salary Index (CC0 1.0).
> - Source: **Aramente/eu-tech-jobs** (CC BY 4.0); data cleaned and normalised.
> - **DataForge (data.zalize.com)**, Tech Job Postings Salary Dataset
>   (CC BY-NC 4.0); data cleaned and normalised.
> - Source: **Statistik der Bundesagentur für Arbeit**; transformed output.
> - Source: **U.S. Bureau of Labor Statistics**, Occupational Employment and Wage
>   Statistics; transformed output.
> - Source: **Eurostat**, Structure of Earnings Survey; transformed output.

Retraining from source is described in the
[README](../README.md#building-the-dataset-locally); the source matrix and the
publication rules are in [DATA_POLICY.md](../DATA_POLICY.md).
