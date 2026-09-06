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
| Stack Overflow 2018-2024 (Germany) | 39,510 | survey | 21,632 |
| Aramente EU Tech Jobs | 20,318 | job postings | 0 |
| IT Salary Survey EU 2018-2020 (Germany) | 2,626 | survey | 2,622 |
| Salary of Data Professions | 2,639 | third-party dataset | 0 |
| Stellen-Atlas salary subset (Germany) | 351 | job postings | 351 |
| BA Entgeltstatistik | 157,553 | official aggregates | – |
| BLS OEWS | 37,249 | official aggregates | – |
| Eurostat SES | 262 | official aggregates | – |
| Destatis Verdiensterhebung | 4,443 | official aggregates | – |

In total: 660,380 individual observations, 199,507 aggregate rows, 141 countries
and 20,097 distinct recognised city names, from 229,851 unique raw titles.

## Job title normalisation

| Method | Rows | Share |
|---|---:|---:|
| Rule / alias | 491,885 | 74.5% |
| Controlled source field | 67,088 | 10.2% |
| ML model | 36,128 | 5.5% |
| Deliberately unmatched | 65,279 | 9.9% |

90.1% of rows were assigned. The title model reaches 97.6% accuracy and 96.5%
macro F1 on a weakly-supervised holdout. That measures agreement with
automatically generated labels, **not** with a human-annotated gold standard.

The classifier is a calibrated linear SVM over word and character TF-IDF
n-grams. Replacing the previous SGD classifier raised accuracy from 96.2% to
97.6% and macro F1 from 94.7% to 96.5%, and shrank the artefact from 86 MB to
22 MB.

## Salary coverage

- 307,146 observations carry a converted EUR annual salary.
- 296,056 of those (96.4%) receive a quantile within a sufficiently large peer
  group.
- Values outside 1,000-2,000,000 EUR/year stay in the raw columns but are
  excluded from quantiles and model training.
- This produces 3,570 groups across title, country, year and optionally
  seniority.

Global medians are not directly comparable, because the populations differ:

| Source | Median EUR/year |
|---|---:|
| aijobs.net | 129,294 |
| Zalize Tech Job Postings | 97,614 |
| Stack Overflow 2025 | 64,923 |
| IT Salary Survey EU (Germany) | 69,000 |
| Stack Overflow 2018-2024 (Germany) | 59,512 |
| Stellen-Atlas salary subset (Germany) | 54,000 |

## Salary predictor

Scored on a duplicate-grouped holdout, so rows sharing `(title, country,
salary)` never straddle the split.

| Metric | Value |
|---|---:|
| Training rows | 215,013 |
| Calibration rows | 23,061 |
| Holdout rows | 59,270 |
| Median absolute error | 21,624 EUR |
| Median absolute percentage error | 21.3% |
| R² on log(salary) | 0.637 |
| Mean pinball loss | 12,412 |
| Coverage of p25-p75 | 51.0% (nominal 50%) |
| Coverage of p10-p90 | 79.6% (nominal 80%) |

Error by country, on the same holdout:

| Country | Holdout rows | Median APE | Median absolute error |
|---|---:|---:|---:|
| US | 43,019 | 20.6% | 25,662 EUR |
| DE | 5,189 | 20.0% | 11,615 EUR |
| GB | 2,533 | 28.7% | 8,451 EUR |
| CA | 2,270 | 22.4% | 20,937 EUR |
| AU | 426 | 17.7% | 15,927 EUR |
| FR | 385 | 25.6% | 13,768 EUR |
| NL | 319 | 19.4% | 11,167 EUR |

Because the expanded holdout contains the newly added German surveys, its
global metric is not directly comparable to the previous report. On the exact
same 53,663-row pre-expansion holdout, the old and new artefacts compare as
follows:

| Fixed holdout | Old model | New model |
|---|---:|---:|
| Global median APE | 20.40% | **19.81%** |
| Global median absolute error | 22,632 EUR | **21,986 EUR** |
| Germany median APE (n=512) | 21.05% | **20.66%** |
| Germany median absolute error (n=512) | 14,444 EUR | **13,659 EUR** |

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
| + retrained title model, conformal bands | 20.4% |
| + German surveys and Destatis, fixed old holdout | **19.8%** |

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
| Full Stack Engineer | 6,095 | 5 | 45,725 | 60,000 | 77,333 |
| Backend Engineer | 5,327 | 5 | 49,700 | 64,389 | 80,217 |
| Frontend Engineer | 2,563 | 4 | 42,863 | 57,000 | 71,533 |
| Software Engineer | 2,268 | 6 | 50,231 | 64,633 | 80,000 |
| Research Scientist | 1,224 | 5 | 40,185 | 53,833 | 67,447 |
| Data Scientist | 1,137 | 5 | 51,578 | 65,000 | 83,385 |
| Mobile Engineer | 1,082 | 4 | 49,245 | 64,015 | 78,117 |
| Database Administrator | 980 | 4 | 33,481 | 48,292 | 64,454 |
| Data Analyst | 681 | 5 | 45,072 | 58,976 | 75,400 |
| Embedded Engineer | 623 | 4 | 53,104 | 67,000 | 82,315 |

Amounts in EUR/year, rounded. These are **empirical** quantiles over the
collected observations, not model output - useful as a reality check on what the
model is fitted to. Attribution and usage notices:
[`DATA_POLICY.md`](../DATA_POLICY.md).
