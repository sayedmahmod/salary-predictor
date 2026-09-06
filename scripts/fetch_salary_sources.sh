#!/usr/bin/env bash
# Download the public salary datasets listed in data/SOURCES.md.
# Run from repository root: bash scripts/fetch_salary_sources.sh
set -euo pipefail

root="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
raw="$root/data/raw"
mkdir -p "$raw"/{stackoverflow_2025,aijobs,bls_oews,eurostat_ses,destatis,ba,restricted}
mkdir -p "$raw/huggingface"/{eu_tech_jobs,data_professions,tech_job_postings}

get() {
  local url="$1" output="$2"
  curl --fail --location --retry 3 --retry-delay 2 --output "$output" "$url"
}

# Stack Overflow's archive is stored through Git LFS.  media.githubusercontent.com
# serves the actual object rather than the small LFS pointer stored in the Git tree.
get "https://media.githubusercontent.com/media/StackExchange/Survey/main/packages/archive/2025/results.csv" \
  "$raw/stackoverflow_2025/survey_results_public.csv"
get "https://media.githubusercontent.com/media/StackExchange/Survey/main/packages/archive/2025/schema.csv" \
  "$raw/stackoverflow_2025/survey_results_schema.csv"
get "https://media.githubusercontent.com/media/StackExchange/Survey/main/packages/archive/2025/survey.pdf" \
  "$raw/stackoverflow_2025/survey.pdf"

# aijobs.net historical, respondent-level salary archive (CC0).
get "https://raw.githubusercontent.com/foorilla/ai-jobs-net-salaries/main/salaries.csv" \
  "$raw/aijobs/salaries.csv"
get "https://raw.githubusercontent.com/foorilla/ai-jobs-net-salaries/main/salaries.json" \
  "$raw/aijobs/salaries.json"
get "https://raw.githubusercontent.com/foorilla/ai-jobs-net-salaries/main/LICENSE" \
  "$raw/aijobs/LICENSE"

# Third-party, explicitly licensed Hugging Face datasets.  Revisions are pinned
# to make later analyses reproducible; see data/SOURCES.md for restrictions.
get "https://huggingface.co/datasets/Aramente/eu-tech-jobs/resolve/f395dce081dac22b3724f32fbdec785eec0bfddb/latest/jobs.parquet" \
  "$raw/huggingface/eu_tech_jobs/jobs.parquet"
get "https://huggingface.co/datasets/Aramente/eu-tech-jobs/resolve/f395dce081dac22b3724f32fbdec785eec0bfddb/latest/companies.parquet" \
  "$raw/huggingface/eu_tech_jobs/companies.parquet"
get "https://huggingface.co/datasets/Aramente/eu-tech-jobs/resolve/f395dce081dac22b3724f32fbdec785eec0bfddb/latest/metadata.json" \
  "$raw/huggingface/eu_tech_jobs/metadata.json"
get "https://huggingface.co/datasets/Aramente/eu-tech-jobs/raw/f395dce081dac22b3724f32fbdec785eec0bfddb/README.md" \
  "$raw/huggingface/eu_tech_jobs/README.md"

# Die Dataset-Card nennt MIT, dokumentiert die Herkunft aber nicht ausreichend.
# Deshalb nur nach bewusster lokaler Freigabe herunterladen.
if [[ "${INCLUDE_UNVERIFIED:-0}" == "1" ]]; then
  get "https://huggingface.co/datasets/krishujeniya/Salary_of_Data_Professions/resolve/b63fb1367641c70bfdc5d3676881563c1c1f646b/Salary%20Prediction%20of%20Data%20Professions.csv" \
    "$raw/huggingface/data_professions/salary_prediction_data_professions.csv"
  get "https://huggingface.co/datasets/krishujeniya/Salary_of_Data_Professions/raw/b63fb1367641c70bfdc5d3676881563c1c1f646b/README.md" \
    "$raw/huggingface/data_professions/README.md"
else
  echo "Skip Salary_of_Data_Professions (set INCLUDE_UNVERIFIED=1 to opt in)."
fi

# CC BY-NC 4.0: nie stillschweigend in einem potenziell kommerziellen Projekt
# aktivieren. Der Nutzer muss die nicht-kommerzielle Verwendung bestaetigen.
if [[ "${INCLUDE_NONCOMMERCIAL:-0}" == "1" ]]; then
  get "https://huggingface.co/datasets/zalizedata/tech-job-postings-salary-dataset/resolve/2314a3ac6897d6a454d53a1120ec3a540e82907d/data/L/jobs-00000-of-00001.parquet" \
    "$raw/huggingface/tech_job_postings/jobs_L.parquet"
  get "https://huggingface.co/datasets/zalizedata/tech-job-postings-salary-dataset/raw/2314a3ac6897d6a454d53a1120ec3a540e82907d/README.md" \
    "$raw/huggingface/tech_job_postings/README.md"
else
  echo "Skip Zalize CC BY-NC data (set INCLUDE_NONCOMMERCIAL=1 to opt in)."
fi

# BLS OEWS: the complete "all data" workbook of the May release.  The adapter
# reads data/raw/bls_oews/all_data_M_<year>.xlsx, and that file ships inside
# oesm<yy>all.zip - so the archive has to be unpacked, not merely stored.  The
# national-only workbook would not carry the state-level rows the adapter keeps.
bls_year=2025
bls_zip="$raw/bls_oews/oesm${bls_year#20}all.zip"
bls_xlsx="$raw/bls_oews/all_data_M_${bls_year}.xlsx"
bls_status="$raw/bls_oews/DOWNLOAD_STATUS.txt"

if [ -f "$bls_xlsx" ]; then
  # An 80 MB download that is already on disk, possibly fetched by hand.
  printf '%s\n' "BLS OEWS: $(basename "$bls_xlsx") already present, not re-downloading."
elif get "https://www.bls.gov/oes/special.requests/oesm${bls_year#20}all.zip" "$bls_zip"; then
  # The workbook sits in a folder inside the archive; -j drops that folder.
  if unzip -o -q -j "$bls_zip" "*all_data_M_${bls_year}.xlsx" -d "$raw/bls_oews"; then
    rm -f "$bls_zip" "$bls_status"
  else
    printf '%s\n' "BLS OEWS: oesm${bls_year#20}all.zip holds no all_data_M_${bls_year}.xlsx; check the release layout." \
      > "$bls_status"
  fi
else
  # BLS answers HTTP 403 to some hosting environments.  Record the fact and
  # carry on with every other independent source.
  rm -f "$bls_zip"
  printf '%s\n' \
    "BLS OEWS download blocked (HTTP 403). Fetch https://www.bls.gov/oes/special.requests/oesm${bls_year#20}all.zip" \
    "from a browser, unpack it, and place all_data_M_${bls_year}.xlsx in $(dirname "$bls_xlsx")/." \
    > "$bls_status"
fi

# Eurostat Structure of Earnings Survey: monthly earnings by sex, age and occupation.
# Filter to Germany to keep the project focused and the download reproducible.
get "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/earn_ses_monthly?geo=DE" \
  "$raw/eurostat_ses/earn_ses_monthly_DE.json"
get "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/earn_ses_annual?geo=DE" \
  "$raw/eurostat_ses/earn_ses_annual_DE.json"
get "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/earn_ses_hourly?geo=DE" \
  "$raw/eurostat_ses/earn_ses_hourly_DE.json"

# The Genesis API supports public guest access for metadata and selected tables.
# Store a current catalogue response even when an individual table requires a login.
get "https://www-genesis.destatis.de/genesisWS/rest/2020/catalogue/tables?username=guest&password=guest&name=Verdienste&area=all&pagelength=500&language=de" \
  "$raw/destatis/genesis_verdienste_catalogue.xml" || true
# Current public table view (the modern GENESIS UI performs table exports by POST).
get "https://genesis.destatis.de/datenbank/online/statistic/62361/table/62361-0001" \
  "$raw/destatis/62361-0001_reallohn_nominallohnindex.html"

# BA's authoritative annual table landing page.  The downloadable workbook URL is
# versioned by BA; the landing HTML is saved to preserve the exact release discovery.
get "https://statistik.arbeitsagentur.de/DE/Navigation/Statistiken/Fachstatistiken/Beschaeftigung/Entgelt/Entgelt-Nav.html" \
  "$raw/ba/entgelt_landing_page.html"
get "https://statistik.arbeitsagentur.de/DE/Statischer-Content/Statistiken/Fachstatistiken/Beschaeftigung/Generische-Publikationen/Blickpunkt-Arbeitsmarkt-Analyse-zur-Entgeltstatistik.pdf?__blob=publicationFile" \
  "$raw/ba/analyse_entgeltstatistik_2024.pdf"

date -u +%Y-%m-%dT%H:%M:%SZ > "$raw/FETCHED_AT_UTC.txt"

# Some external macOS volumes create AppleDouble sidecars while downloading.
# They do not belong to the data archive.
find "$raw" -name '._*' -type f -delete

# Create checksums after successful downloads; ignored failures are recorded in status.
(cd "$raw" && find . -type f ! -name SHA256SUMS -exec shasum -a 256 {} \; | sort) > "$raw/SHA256SUMS"
