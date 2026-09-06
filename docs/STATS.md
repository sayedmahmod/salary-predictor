# Project statistics

As of the local build on 6 September 2026. The underlying data is not published
in this repository. All figures are descriptive and are not individual salary
advice.

## Scope

| Source | Rows | Type | With EUR annual salary |
|---|---:|---|---:|
| Zalize Tech Job Postings | 394,300 | job postings | 107,149 |
| aijobs.net | 151,445 | salary reports | 151,445 |
| Stack Overflow 2025 | 49,191 | survey | 23,947 |
| Aramente EU Tech Jobs | 20,318 | job postings | 0 |
| Salary of Data Professions | 2,639 | third-party dataset | 0 |
| BA Entgeltstatistik | 157,553 | official aggregates | – |
| BLS OEWS | 37,249 | official aggregates | – |
| Eurostat SES | 262 | official aggregates | – |

In total: 617,893 individual observations, 195,064 aggregate rows, 141 countries
and 20,097 distinct recognised place names, from 222,482 unique raw titles.

## Job title normalisation

| Method | Rows | Share |
|---|---:|---:|
| Rule / alias | 485,532 | 78.6% |
| Controlled source field | 38,005 | 6.2% |
| ML model | 34,619 | 5.6% |
| Deliberately unmatched | 59,737 | 9.7% |

90.3% of titles were assigned. The title model reaches 97.6% accuracy and 96.5%
macro F1 on a weakly-supervised holdout. That measures agreement with
automatically generated labels, **not** with a human-annotated gold standard.

The classifier is a calibrated linear SVM over word and character TF-IDF
n-grams. Replacing the previous SGD classifier raised accuracy from 96.2% to
97.6% and macro F1 from 94.7% to 96.5%, and shrank the artefact from 86 MB to
22 MB.

## Salary coverage

- 282,541 observations carry a converted EUR annual salary.
- 271,993 of those (96.3%) receive a quantile within a sufficiently large peer
  group.
- Values outside 1,000-2,000,000 EUR/year stay in the raw columns but are
  excluded from quantiles and model training.
- This produces 3,240 groups across title, country, year and optionally
  seniority.

Global medians are not directly comparable, because the populations differ:

| Source | Median EUR/year |
|---|---:|
| aijobs.net | 129,294 |
| Zalize Tech Job Postings | 97,614 |
| Stack Overflow 2025 | 64,923 |

## Salary predictor

Scored on a duplicate-grouped holdout, so rows sharing `(title, country,
salary)` never straddle the split.

| Metric | Value |
|---|---:|
| Training rows | 198,165 |
| Calibration rows | 21,485 |
| Holdout rows | 53,663 |
| Median absolute error | 22,632 EUR |
| Median absolute percentage error | 20.4% |
| R² on log(salary) | 0.664 |
| Mean pinball loss | 12,077 |
| Coverage of p25-p75 | 51.5% (nominal 50%) |
| Coverage of p10-p90 | 82.2% (nominal 80%) |

Error by country, on the same holdout:

| Country | Holdout rows | Median APE | Median absolute error |
|---|---:|---:|---:|
| US | 42,347 | 19.9% | 25,375 EUR |
| GB | 2,603 | 15.5% | 7,522 EUR |
| CA | 2,133 | 21.3% | 20,647 EUR |
| DE | 512 | 21.1% | 14,444 EUR |
| AU | 423 | 19.3% | 15,750 EUR |
| FR | 366 | 25.8% | 14,697 EUR |
| NL | 324 | 28.6% | 14,813 EUR |

### What changed against the previous revision

| Step | Median APE |
|---|---:|
| Previously reported (random split) | 22.8% |
| Same model, leakage-free split | 23.4% |
| + staff seniority fix | 23.3% |
| + job-title embedding | 22.5% |
| + industry / region / city | 21.5% |
| + official-statistics prior | 21.4% |
| + larger ensemble | 21.2% |
| + retrained title model, conformal bands | **20.4%** |

The previous number was measured on a random holdout. Because about 60% of rows
are exact repeats of `(title, country, salary)`, identical records sat on both
sides of that split, which flattered the result by 0.6 percentage points.

The holdout is not representative, and the source data is not either. The model
learns relationships within these three microdata sources; it is not causal and
guarantees nothing about an individual offer.

## Germany example

Roles with many salary observations, pooled across record types:

| Normalised title | n | Sources | p25 | Median | p75 |
|---|---:|---:|---:|---:|---:|
| Full Stack Engineer | 664 | 3 | 48,375 | 65,000 | 80,000 |
| Backend Engineer | 307 | 3 | 59,000 | 75,000 | 90,000 |
| Software Engineer | 189 | 3 | 58,976 | 75,000 | 100,000 |
| Software Architect | 168 | 3 | 80,000 | 94,500 | 115,000 |
| Research Scientist | 117 | 3 | 50,000 | 62,000 | 75,000 |
| Data Scientist | 113 | 3 | 60,000 | 75,000 | 106,876 |
| Data Engineer | 112 | 3 | 66,660 | 81,745 | 111,250 |
| Frontend Engineer | 95 | 2 | 52,250 | 68,287 | 85,000 |
| Machine Learning Engineer | 92 | 3 | 79,900 | 99,806 | 130,000 |
| DevOps Engineer | 84 | 3 | 59,750 | 75,000 | 90,000 |

Amounts in EUR/year, rounded. These are **empirical** quantiles over the
collected observations, not model output - useful as a reality check on what the
model is fitted to. Attribution and usage notices:
[`DATA_POLICY.md`](../DATA_POLICY.md).
