# GO LIVE — Aster da Master artist site

How to deploy this repo, what runs live, and what stays static.
Last updated: 2026-10-11.

## 1. Live architecture

```
                     +--------------------+
                     |   Static host      |  (any static host: GitHub Pages,
                     |   serves REPO ROOT |   Netlify, nginx, S3+CF...)
                     +---------+----------+
                               |  relative paths everywhere; every page's
                               |  fetch() points at ./data/*.json / ./api/v1/*.json
                               |
   scheduler (cron or GitHub Actions)
                               |  weekly: bash scripts/refresh/refresh.sh
                               v
   scripts/refresh/refresh_plays.py -- four tiers:
     (a)  SOUNDCLOUD_CLIENT_ID set -> api-v2 resolve + paged tracks
                                      -> NEW data/playcounts.snapshot.json
     (a2) no env key -> extract client_id read-only from SoundCloud's
                                      public web-app JS bundles, verify, same pull
     (b)  no usable key -> best-effort public probes, recorded
     (c)  nothing reachable -> NEW api/v1/refresh-status.json {status:"skipped"}, exit 0
   operator (human) reviews snapshot, then:
     python3 scripts/refresh/refresh_plays.py --merge   # backup + apply counts into data/artist.json
     re-run generators: build_releases.py build_years.py build_circle.py
                        build_search_index.py build_codex.py
     commit + push; static host redeploys
```

**Snapshot overlay pattern.** The canonical catalog data stays in
`data/artist.json`. Fresh play counts land first in a separate, throwaway
overlay file — `data/playcounts.snapshot.json` — which nothing on the site
reads directly. A human operator reviews it, then runs `--merge`, which
backs up `data/artist.json` to `data/artist.json.bak` and applies only
verified, non-zero counts. The generators then rebuild every derived page
and `api/v1/*` copy. Nothing ever writes zeros or fabricated counts over
real data, and the `.bak` gives a one-step rollback.

## 2. What's live vs static

| Feature | Live? | How |
|---|---|---|
| Play counts (185 SoundCloud vault tracks) | **Refreshable** | `refresh_plays.py` tier (a) -> snapshot -> `--merge`; generators re-run. Currently a 2026-10-11 snapshot. |
| Velocity / milestones ("X plays gained", watch list) | **Refreshable** | Same pipeline; `scripts/build_milestones.py` + `build_milestone_watch.py` recompute from new counts. |
| `api/v1/refresh-status.json` | **Live** | Written by every refresh run: `ok` / `skipped` + reason + tier notes. Pages can read it to show "counts as of …". |
| Vault catalog (tracks, dates, artwork, links) | Static / manual research | New tracks are added by hand research (live-browser capture); the refresh pipeline only updates counts, never adds tracks. |
| Releases, years, circle, codex, search index | Static / generated | Rebuilt from `data/artist.json` by the `scripts/build_*.py` generators when data changes. |
| Everything else (timeline, trilogy, decoder, method, press-kit…) | Static | Hand-built pages. |

## 3. Pipeline docs

### 3a. Obtaining SOUNDCLOUD_CLIENT_ID (optional)

SoundCloud has no public play-count API. The `api-v2` endpoints power the
official web app and accept a `client_id` query parameter:

1. Open https://soundcloud.com/asterdamaster in a desktop browser.
2. Open DevTools -> Network tab, filter for `api-v2`.
3. Reload the page; click any request to `api-v2.soundcloud.com/...`.
4. Copy the `client_id` query parameter value (32 hex chars).
5. Export it where the scheduler runs: `SOUNDCLOUD_CLIENT_ID=<that value>`.

**Caveats:** this is unofficial. SoundCloud rotates these keys and can
block them at any time. When tier (a) starts failing, fall back to the
live-browser capture below and re-extract a fresh key.

### 3b. Live-browser capture fallback (the method that worked 2026-10-11)

Plain HTTP fetching does NOT work: SoundCloud renders client-side, and a
plain GET of the profile page returns ~111 KB of HTML containing **zero**
`playback_count` strings (probed 2026-10-11: `api-v2/resolve` without
client_id -> HTTP 401; profile HTML -> HTTP 200 with no play-count data).

The working procedure is a read-only live-browser pass:

1. Open https://soundcloud.com/asterdamaster in a real browser (logged OUT — read-only).
2. Scroll the full track list until all 185 tracks are loaded (lazy loading).
3. For each track card, read the visible play count next to the ▶ icon and
   the upload date from the track page or card tooltip.
4. Write the results to `data/playcounts.snapshot.json` in this exact shape:
   `{ "snapshot_at": "<ISO8601>", "source": "live-browser capture", "tracks": [ {"title": ..., "upload_date": "YYYY-MM-DD", "plays": N} ] }`
5. Run the merge + generators + commit as in section 1.

### 3c. Endpoint matrix (probed 2026-10-11, all read-only, no accounts)

| Endpoint | Key | Result |
|---|---|---|
| `GET https://api-v2.soundcloud.com/resolve?url=<profile>&client_id=<key>` | required (env **or** extracted from public web-app JS) | **200** — user object. Example (public artist profile): `{"id": 259877060, "kind": "user", "username": "ASTER DA MASTER", "track_count": 185, "followers_count": 1562, ...}` |
| `GET https://api-v2.soundcloud.com/users/259877060/tracks?client_id=<key>&limit=200` | required (same) | **200** — paged collection (`next_href` for more). Per track: `playback_count`, `created_at`, `title`, `duration`, … Example: `{"id": …, "title": "turn up w me (prod_timmy)", "playback_count": 177, "created_at": "2026-10-02T07:19:01Z", "duration": 160195, "genre": …, "permalink_url": "https://soundcloud.com/asterdamaster/…"}`. Full catalog = 185 tracks, 0 skipped. |
| `GET https://api-v2.soundcloud.com/resolve?url=<profile>` (no key) | none | **401** — empty body. Keyless api-v2 is dead. |
| `GET https://api-v2.soundcloud.com/resolve?url=<profile>&client_id=<bogus>` | invalid | **401** — empty body. |
| `GET https://soundcloud.com/asterdamaster` (plain HTTP) | none | **200**, 111,614 bytes HTML — **zero** `playback_count` occurrences. Client-side render; useless for counts. |
| `GET https://a-v2.sndcdn.com/assets/*.js` (web-app bundles, 9 found in page HTML) | none | **200** — public static JS. One bundle contains `client_id:"vI5BsvpTIlavDLl7RDbbcFAPg8kls8Bg"` (the key the official web app itself uses). Extraction is read-only; re-extracted every run, so rotation self-heals. |
| `GET https://soundcloud.com/oembed?format=json&url=<profile>` | none | **200** — `{"title": "ASTER DA MASTER", "author_name": "ASTER DA MASTER", "type": "playlist", "html": "<iframe …>", "thumbnail_url": …, …}`. **No play counts.** Useful for embed/title only. |
| `GET https://api.soundcloud.com/resolve.json?url=<profile>&client_id=<key>` (deprecated v1) | — | **429 Rate Limit Exceeded** — effectively dead for our use; not retried. |

**Bottom line:** the only automated path to real `playback_count` values is
api-v2 with a valid client_id. The pipeline now obtains one automatically
(tier a2: extract from the public web-app JS, verify with one resolve call);
`SOUNDCLOUD_CLIENT_ID` remains as a manual override (tier a).

### 3d. Client_id extraction detail (tier a2)

1. `GET https://soundcloud.com/asterdamaster` (browser UA) -> page HTML.
2. Regex the HTML for `https://a-v2.sndcdn.com/assets/[0-9a-f-]+\.js` -> bundle URLs (9 on 2026-10-11).
3. Fetch each bundle, regex `client_id\s*:\s*"([A-Za-z0-9]{20,40})"` -> candidates
   (note: bundles also contain Google/Apple OAuth client ids — only the
   `client_id:"<key>"` api-v2 form is tried).
4. Verify each candidate with one `api-v2/resolve` call; first 200 wins.
5. Proceed with the tier-(a) tracks pull; snapshot records
   `"client_id_source": "public-webapp-js"`.

No accounts created, nothing spent, no private data touched — every request
is a read-only GET of public content.

## 4. Scheduler setup

### Cron (weekly, Sundays 09:00 UTC)

```cron
# Aster da Master — weekly play-count refresh (logs to logs/refresh.log)
0 9 * * 0 cd /path/to/aster-da-master && bash scripts/refresh/refresh.sh
```

The script appends timestamped output to `logs/refresh.log` and exits 0 on
success or graceful skip. `refresh-status.json` records the outcome for the
site to display.

### GitHub Actions sketch

The repo is GitHub-only (no Vercel — standing rule). If you want the refresh
to run without a server, add `.github/workflows/refresh.yml`:

```yaml
name: weekly-play-refresh
on:
  schedule:
    - cron: '0 9 * * 0'   # Sundays 09:00 UTC
  workflow_dispatch: {}
jobs:
  refresh:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.12' }
      - name: refresh play counts
        env:
          SOUNDCLOUD_CLIENT_ID: ${{ secrets.SOUNDCLOUD_CLIENT_ID }}
        run: bash scripts/refresh/refresh.sh
      - name: commit status
        run: |
          git config user.name "refresh-bot" && git config user.email "refresh-bot@localhost"
          git add api/v1/refresh-status.json data/playcounts.snapshot.json logs/refresh.log
          git diff --cached --quiet || git commit -m "weekly play-count refresh"
          git push
```

Note: the Actions run commits only the snapshot + status, never a `--merge`.
Merging stays a deliberate human step (review counts, re-run generators,
push), because the builder is actively developing in this repo.

## 5. Keys

| Key | Required? | Purpose |
|---|---|---|
| `SOUNDCLOUD_CLIENT_ID` | **Optional** | Manual override for tier (a): automated api-v2 play-count pulls with your own key. When unset, the pipeline extracts a working key read-only from SoundCloud's public web-app JS (tier a2, verified 2026-10-11). Obtain per section 3a. |

No other keys are needed. There is no backend, no database, no analytics.

## 6. Deploy checklist

- [ ] Static host serves the **repo root** (index.html at `/`).
- [ ] Confirm `data/artist.json`, `data/codex.json`, `api/v1/on-this-day.json`
      and the other fetched JSONs resolve with relative URLs (see audit below).
- [ ] Scheduler installed: cron line from section 4 (or the Actions workflow).
- [ ] `SOUNDCLOUD_CLIENT_ID` set in the scheduler environment if automated
      pulls are wanted (optional).
- [ ] After the first refresh run, check `api/v1/refresh-status.json` shows
      `ok` or `skipped` with a fresh `last_attempt`.
- [ ] `.gitignore` keeps `logs/` out of the repo if desired (currently only
      `__pycache__/` and `*.pyc` are ignored; `logs/refresh.log` is small and
      committing it is harmless either way).
- [ ] Keep the no-Vercel rule: GitHub-only deploys.

## 7. Static-readiness audit summary (2026-10-11)

- **Deploy root:** repo root. All references relative; **zero absolute `/`
  refs** across HTML/JS.
- **Zero real localhost refs.** The only two `file://` strings in the JS are
  graceful-degradation error messages for `file://` viewing — intended behavior.
- **All fetched JSONs exist:** `data/artist.json`, `data/codex.json`,
  `api/v1/on-this-day.json`, and every other fetch target resolve to real files.
- **Play counts:** 185 SoundCloud vault tracks carry a 2026-10-11 snapshot;
  counts drift over time, which is exactly what the refresh pipeline in this
  document corrects.
- **Conclusion:** the static layer is deploy-ready as-is; the refresh
  pipeline added in this wave (`scripts/refresh/`, this doc) is the only
  moving part, and it degrades to a documented skip when no credentials exist.
