# Unified data schema

The pipeline keeps individual observations separate from official aggregates. A
job posting or survey response is not treated like an official distribution.

## `observations`

One row is one survey response or one job posting.

| Area | Key fields |
|---|---|
| Provenance | `obs_id`, `source`, `source_dataset`, `record_type`, `license` |
| Time | `year`, `observed_at` |
| Title | `job_title`, `job_title_clean`, `job_title_core` |
| Taxonomy | `normalized_job_title`, `normalized_job_code`, `job_family` |
| Confidence | `norm_method`, `norm_confidence` |
| Crosswalks | `isco08`, `soc2018`, `kldb2010` |
| Context | `seniority`, `employment_type`, `remote_type`, `experience_years` |
| Place | `location_raw`, `country_iso2`, `region`, `city`, `location_source` |
| Money | raw amount/range, currency, period, annualised values in EUR and USD |
| Quantile | `salary_quantile`, `salary_quantile_group`, `salary_quantile_n` |

## `aggregates`

One row is one published table cell by occupation, area, year, sex and working
time. Quantiles are taken over directly, or - for BA class counts - interpolated
linearly within closed classes. Open boundary classes are never guessed.

## `quantiles`

The group hierarchy is:

1. title + country + year + seniority
2. title + country + year
3. title + country
4. title + year
5. title

Small groups are not published. `n`, `n_sources` and `sources` show the
underlying evidence. The full definition lives in
[`src/salarykit/schema.py`](../src/salarykit/schema.py).
