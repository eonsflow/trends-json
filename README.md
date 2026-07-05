# Daily Trend Fetcher

Automatically fetches daily trends and enriches them with **Naver DataLab
search-volume trends** (검색량 추이).

- Keyword list is merged from Naver/Google sources.
- For each keyword, the [Naver DataLab Search Trend API](https://developers.naver.com/docs/serviceapi/datalab/search/search.md)
  (`POST /v1/datalab/search`, up to 5 keyword groups per request) provides:
  - `volume`: the most recent relative search ratio (0–100, DataLab scale)
  - `trend`: the daily time series `[{ "date", "ratio" }, ...]` for the last 30 days
- Output is saved to `trends.json` and served via GitHub Pages.

## Required GitHub Secrets

Set these in **Settings → Secrets and variables → Actions**:

| Secret | Description |
| --- | --- |
| `NAVER_CLIENT_ID` | Naver DataLab (Developers) application Client ID |
| `NAVER_CLIENT_SECRET` | Naver DataLab application Client Secret |
| `EONSFLOW` | GitHub token used to commit `trends.json` |

If the DataLab credentials are missing or the API call fails, the fetcher
falls back to a random `volume` and an empty `trend` so the job never breaks.

## Notes

DataLab ratios are relative to the maximum **within each request**, so values
are comparable inside a keyword's own time series but not perfectly comparable
across separate batches of keywords.
