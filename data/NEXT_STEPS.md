# Sources still missing: handover and access

## Already done

- **BLS OEWS 2025:** `data/raw/bls_oews/all_data_M_2025.xlsx` is present
  and is processed into `aggregates.parquet`. The historically named folder is
  kept for compatibility.
- **BA Entgeltstatistik:** annual files for 2020 to 2025 are stored under
  `data/raw/ba/jahreszahlen/` and are processed.
- **Eurostat SES:** the German API exports are present; the annual table is
  processed.

## Blocked on credentials

1. **Destatis:** open table `62361-0034` (gross annual earnings by sex and
   occupation) in GENESIS, widen the selection if needed, and save the CSV or
   XLSX download under `data/raw/destatis/62361-0034/`.

Once the file is in place, add a Destatis adapter following the pattern in
`src/salarykit/sources/` and register it in the build.

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
