# Salary data sources

Retrieval: see `scripts/fetch_salary_sources.sh`. Raw files belong in
`data/raw/<source>/`; `data/raw/SHA256SUMS` records the checksums. The fetch
step never rewrites data that did not come from one of the primary sources
listed here.

| Source | Local contents | Granularity | Vintage / limitation |
|---|---|---|---|
| Stack Overflow Developer Survey 2025 | `stackoverflow_2025/` | individual voluntary responses, incl. compensation, role, experience, technologies | Non-representative self-selection; filter Germany via `Country = Germany`. |
| aijobs.net Salary Index | `aijobs/` | individual anonymous AI/ML/data salary reports | Historical archive 2021-2025, CC0. |
| Hugging Face: Aramente/eu-tech-jobs | `huggingface/eu_tech_jobs/` | active EU tech vacancies incl. salary band where published | CC BY 4.0; daily snapshot, commit `f395dce`. Third-party source, not a salary survey. |
| Hugging Face: Salary_of_Data_Professions | `huggingface/data_professions/` | data-profession salary table | MIT; commit `b63fb13`. Third-party source; verify provenance before using it in an analysis. |
| Hugging Face: Zalize Tech Job Postings | `huggingface/tech_job_postings/` | 394k tech vacancies with parsed salary bands | CC BY-NC 4.0: personal/academic, non-commercial use only; commit `2314a3a`. |
| BA Entgeltstatistik | `ba/` | officially aggregated tables | Annual files 2020-2025, landing page and 2024 analysis stored. No microdata download. |
| Destatis / GENESIS | `destatis/` | officially aggregated tables and catalogue | The public table page 62361-0001 is stored; the GENESIS web interface serves exports over POST. No credentials are kept in this project. |
| Eurostat SES | `eurostat_ses/` | officially aggregated, Germany | Structure of Earnings Survey; the API call is limited to `geo=DE`, and the build uses the annual table. |
| BLS OEWS | `bls_oews_2024/` | officially aggregated, USA, by occupation | Complete May 2025 all-data workbook; the historically named folder is kept for compatibility. |
| Levels.fyi | `restricted/` | no file | API available on request only, per the provider; no unauthorised collection. |
| SOEP | `restricted/` | no file | Research data access requires an application and a usage agreement. |

## Source URLs

- Stack Overflow: https://github.com/StackExchange/Survey/tree/main/packages/archive/2025
- aijobs.net: https://github.com/foorilla/ai-jobs-net-salaries
- Hugging Face EU tech jobs: https://huggingface.co/datasets/Aramente/eu-tech-jobs
- Hugging Face Data Professions: https://huggingface.co/datasets/krishujeniya/Salary_of_Data_Professions
- Hugging Face Tech Job Postings: https://huggingface.co/datasets/zalizedata/tech-job-postings-salary-dataset
- BA: https://statistik.arbeitsagentur.de/DE/Navigation/Statistiken/Fachstatistiken/Beschaeftigung/Entgelt/Entgelt-Nav.html
- Destatis: https://www.destatis.de/DE/Themen/Arbeit/Verdienste/Verdienste-Branche-Berufe/_inhalt.html
- Eurostat SES: https://ec.europa.eu/eurostat/web/labour-market/information-data/earnings
- BLS OEWS: https://www.bls.gov/oes/tables.htm
- Levels.fyi API: https://www.levels.fyi/api-access/
- SOEP access: https://www.diw.de/de/diw_01.c.601584.de/datenzugang.html
