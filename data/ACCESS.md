# Access restrictions

This project only contains data that was published without a login.

- **Levels.fyi:** the provider grants API access on request only. For that
  reason `data/raw/restricted/` deliberately holds no scraped substitute.
- **SOEP:** individual and panel data require an application and a usage
  agreement with the DIW. They are not copied into any project directory.
- **BLS OEWS:** an automated request initially answered with HTTP 403; the May
  2025 XLSX was subsequently stored successfully and is processed.
  `DOWNLOAD_STATUS.txt` now documents only that earlier failed attempt.
- **BA, Destatis and Eurostat:** their public offerings are aggregated
  statistics. They are not equivalent to personal microdata.
