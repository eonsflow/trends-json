# Daily Trend Fetcher

Automatically fetches daily trends and enriches each keyword with **Naver
search-volume + search-volume trend** (검색량 · 검색량 추이), ported from the
`citeflow` project's `lib/naver.ts`.

Two Naver APIs are used (up to 5 keywords per request, batched):

1. **DataLab Search Trend** (`POST /v1/datalab/search`) → `trend`
   - Monthly relative index (0–100, normalized within each request)
   - `trend`: `[{ "period", "ratio" }, ...]` for the last 12 months
2. **Search Ad Keyword Tool** (`GET api.searchad.naver.com/keywordstool`,
   HMAC-SHA256 signed) → `volume` and `related`
   - `volume`: absolute monthly search count (PC + mobile), exact match only
   - `related`: related keywords `[{ "keyword", "volume", "comp" }, ...]`,
     sorted by search volume (anchored to the seed's head token, deduped)

Output is saved to `trends.json` and served via GitHub Pages.

## Required GitHub Secrets

Set these in **Settings → Secrets and variables → Actions**:

| Secret | Used by | Description |
| --- | --- | --- |
| `NAVER_CLIENT_ID` | DataLab | Naver Developers application Client ID |
| `NAVER_CLIENT_SECRET` | DataLab | Naver Developers application Client Secret |
| `NAVER_SAD_CUSTOMER_ID` | Search Ad | Naver Search Ad customer ID |
| `NAVER_SAD_API_KEY` | Search Ad | Naver Search Ad API access license |
| `NAVER_SAD_SECRET` | Search Ad | Naver Search Ad secret key (for HMAC signature) |
| `EONSFLOW` | workflow | GitHub token used to commit `trends.json` |

Each source degrades gracefully: if its credentials are missing or the call
fails, `trend` falls back to `[]` and `volume` falls back to a random value,
so the job never breaks.

## Notes

DataLab ratios are relative to the maximum **within each request**, so values
are comparable inside a keyword's own time series but not across batches. The
absolute `volume` comes from the Search Ad keyword tool.
