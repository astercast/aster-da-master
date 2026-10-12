# LIVE CHECKLIST — aster-da-master-live (release track)

> Working repo (`astercast/aster-da-master`) is NEVER deployed and NEVER
> connected to Vercel. This file tracks what is wired in the **`-live`
> release repo** (`astercast/aster-da-master-live`), the only deployable
> artifact. The `-live` repo is re-synced ONLY on the user's explicit
> "push"/"ship it". Never push to `-live` from wave-engine automation.

## Snapshot contents (2026-10-12, first snapshot)

- **Static frontend** — full site from the repo root: `index.html`, section
  pages, generated dirs (`releases/`, `years/`, `circle/`, `codex/`,
  `sessions/`, `eras/`, `producers/`, `scene/`), `assets/` (incl. self-hosted
  fonts: Anton + IBM Plex Mono WOFF2 in `assets/fonts/`, zero remote font
  requests), `api/v1/*.json` static endpoints, `data/`, `skills/`,
  `llms.txt` / `llms-full.txt`.
- **Server functions** (`api/`, zero npm deps, `nodejs22.x`, envelope-only):
  | route | file | purpose |
  |---|---|---|
  | `GET /api/health` | `api/health.js` | status/degraded, functions roster, data freshness |
  | `GET /api/stats` | `api/stats.js` | live-computed track/play counts + top-10 |
  | `GET /api/uploads` | `api/uploads.js` | newest-first upload log (`?since=`, `?limit=` ≤200) |
  | `GET /api/cron/signal` | `api/cron/signal.js` | daily refresh: SoundCloud pull → `api/v1/*.json` commit-back |
- **Shared helpers** (never routes): `lib/envelope.js`, `lib/fetchx.js`,
  `lib/ratelimit.js`, `lib/cronauth.js`, `lib/github.js`.
- **Function count: 4** (Hobby limit is plenty; ≤12/site rule respected).
- **`vercel.json`** — adapted from the working repo: functions + cron +
  security headers + `cleanUrls`/`trailingSlash:false` kept; **no
  `buildCommand`** (pre-built snapshot, `scripts/` is not in `-live`);
  `installCommand: echo 'no dependencies'`. Publish dir = repo root.
- **Excluded from `-live`**: `scripts/` (generators), `tests/`, `logs/`,
  dev notes (`AGENT.md`, `API.md`, `GO_LIVE.md`, `WAVELOG.md`,
  `LIVE_CHECKLIST.md`), `.github/` (none in this repo).

## Cron

- One job: `/api/cron/signal`, schedule `0 16 * * *` UTC (daily, prod only).
- Bearer `CRON_SECRET`, fail-closed 401, 60s duplicate cooldown.

## Env vars (set in Vercel → Project → Settings → Environment Variables)

| name | required? | notes |
|---|---|---|
| `CRON_SECRET` | **yes** | 32+ random hex chars; Vercel auto-sends as `Authorization: Bearer` |
| `GITHUB_REPO_TOKEN` | for commit-back | fine-grained PAT, contents:write on the `-live` repo only. **Without it the cron runs read-only** (fresh data returned in the envelope with `read_only:true`, nothing persisted) |
| `GITHUB_REPO` | with the token | `astercast/aster-da-master-live` (the repo the cron commits back to) |
| `REPO_STATIC_PREFIX` | with the token | empty string (`api/v1/*.json` at the root) |
| `SOUNDCLOUD_CLIENT_ID` | recommended | public-webapp client_id; skips the ~5.5s key-extraction path |

No secrets in the repo. Ever. Functions degrade gracefully without keys:
no token → read-only cron; no client_id → slower key extraction; pages
always render pre-built static data with an honest "cached · updated HH:MM"
badge when `/api/*` is unreachable.

## Known-good status (2026-10-12, NOT yet deployed)

- `tests/api.test.sh` 31/31 green against the local Vercel-routing emulator.
- Live cron rehearsal (read-only): 185 tracks fresh from SoundCloud,
  0 new uploads, 7/7 sources ok.
- Static validation: 19,737 relative links, 0 broken; 23/23 JSON schemas;
  lyric-grep clean; chain byte-stable; data version 0.18.0.
- **Not deployed.** Deploy = one-time Vercel CLI from a local clone of
  `-live` (`vercel --prod`), then run the GO_LIVE.md §2 checklist
  (health assert, cron assert, curl roster, functions-disabled pass).

## Build machine

**Standard. Never Turbo.** (Sept 2026 Turbo invoice 1ZU1WJJS-0012: $38.64 —
never repeat it. Static sites = negligible build minutes; Hobby covers them.)

**Function runtime: nodejs20.x, never nodejs22.x.** (Vercel rejects nodejs22.x —
"use nodejs20.x" — 2026-10-12: all 5 first deploys failed validation on nodejs22.x.)
