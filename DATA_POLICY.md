# Data and publication policy

This file is a practical safety rule for the repository, not legal advice. A
commercial data release should be reviewed separately by a lawyer.

## What lives on GitHub

- source code, tests and the schema
- the hand-maintained job-title taxonomy, as Python code
- the download script, with links to the original providers
- aggregated, non-row-level project statistics with their sources named
- derived figures under `docs/img/`, which show aggregates only
- `models/*.joblib` - the trained title and salary models
- the evaluation reports that hold metrics only: `reports/salary_model.json`,
  `reports/eval_variants.json`, `reports/title_model.json`

## What does not live on GitHub

- `data/raw/` - downloaded original files
- `data/processed/` - merged or transformed data
- `data/interim/` - intermediate artefacts
- `reports/title_coverage.json` - quotes raw job titles from the sources as
  examples
- credentials, tokens or `.env` files

## Why the models are versioned

They contain no row-level records. `title_model.joblib` holds a TF-IDF
vocabulary and the classifier weights. `salary_model.joblib` holds the boosted
trees, a 200-entry city vocabulary, a support index that stores only a row
count and the source names per group, and a prior of 112 median values per
role/country group.

That is aggregation, not redistribution - but it is still derived from sources
with share-alike (Stack Overflow, ODbL) and non-commercial (Zalize, CC BY-NC)
terms. **This is defensible while the repository is private.** Before making it
public, or before shipping the models as a product, the terms in the matrix
below should be reviewed for the artefacts, not only for the raw data.

The exclusions are enforced technically in `.gitignore`. An additional
repository check (`scripts/check_repository.py`) guards against accidentally
committing large or sensitive files.

## Source matrix

| Source | Stated licence / rule | How this project treats it |
|---|---|---|
| aijobs.net Salary Index | CC0 1.0 | Use permitted; raw data still stays out of the repository |
| Stack Overflow Developer Survey 2025 | ODbL 1.0, contents under DbCL 1.0 | Attribution and share-alike apply; do not redistribute inside a mixed dataset |
| Aramente EU Tech Jobs | data under CC BY 4.0 | Attribution and a change notice are required |
| Salary of Data Professions | dataset card states MIT; provenance barely documented | Do not redistribute; local, optional input only |
| Zalize Tech Job Postings | CC BY-NC 4.0 | Academic/personal use only; attribution and backlink; not for commercial use |
| BA Entgeltstatistik | Datenlizenz Deutschland - Namensnennung 2.0, per the source | Keep the source credit |
| BLS OEWS | Public domain; the BLS asks to be cited | Keep the source credit |
| Eurostat SES | Re-use permitted with source acknowledgement | Name the source and mark changes |
| Levels.fyi / SOEP | no freely embeddable dataset | Nothing published without separate clearance |

## Required attribution notices

Whenever results built from this pipeline are published, at least the following
notices should stay visible:

- Contains information from the Stack Overflow Developer Survey 2025, made
  available under ODbL 1.0; individual contents under DbCL 1.0.
- Source: aijobs.net Global AI, ML and Data Science Salary Index (CC0 1.0).
- Source: Aramente/eu-tech-jobs (CC BY 4.0); data cleaned and normalised.
- DataForge (data.zalize.com), Tech Job Postings Salary Dataset (CC BY-NC 4.0);
  data cleaned and normalised.
- Source: Statistik der Bundesagentur für Arbeit; transformed output.
- Source: U.S. Bureau of Labor Statistics, OEWS; transformed output.
- Source: Eurostat, Structure of Earnings Survey; transformed output.

## If data is ever to be published

Do not simply upload `observations.parquet`. Each source should be exported and
licensed separately. Stack Overflow (share-alike) and Zalize (non-commercial) in
particular should not end up in a single combined download without a careful
review. For a commercially usable release, exclude Zalize and the
poorly-documented Data Professions source.

Source URLs and the revisions used locally are listed in
[`data/SOURCES.md`](data/SOURCES.md).
