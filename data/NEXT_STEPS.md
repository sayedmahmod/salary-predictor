# Sources still missing: handover and access

## Already done

- **BLS OEWS 2025:** `data/raw/bls_oews/all_data_M_2025.xlsx` is present
  and is processed into `aggregates.parquet`. The historically named folder is
  kept for compatibility.
- **BA Entgeltstatistik:** annual files for 2020 to 2025 are stored under
  `data/raw/ba/jahreszahlen/` and are processed.
- **Eurostat SES:** the German API exports are present; the annual table is
  processed.
- **Destatis 62361-0034:** the public bulk CSV is downloaded without credentials
  and processed into annual KldB aggregates.
- **German salary supplements:** Stack Overflow 2018-2024, IT Salary Survey EU
  2018-2020 and the conservatively filtered Stellen-Atlas salary subset are
  downloaded and processed.

## Access to request

1. **Levels.fyi:** submit the form at https://www.levels.fyi/api-access/ with a
   business e-mail, name, role, organisation size, intended use and use case.
   After approval, place the export in `data/raw/levels_fyi/`. Never write API
   keys into a chat or into the repository.
2. **SOEP:** research use only. Submit the application for a data transfer
   agreement and the data-protection form to the DIW; the institution must
   demonstrate scientific research. Once accepted, store the DIW-provided
   download locally - do not upload or publish it here. Share only the local
   path afterwards.
