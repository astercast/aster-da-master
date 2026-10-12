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
  requests), `data/v1/*.json` static endpoints, `data/`, `skills/`,
  `llms.txt` / `llms-full.txt`.
- **Server functions** (`api/`, zero npm deps, Node — `runtime` never pinned, envelope-only):
  | route | file | purpose |
  |---|---|---|
  | `GET /api/health` | `api/health.js` | status/degraded, functions roster, data freshness |
  | `GET /api/stats` | `api/stats.js` | live-computed track/play counts + top-10 |
  | `GET /api/uploads` | `api/uploads.js` | newest-first upload log (`?since=`, `?limit=` ≤200) |
  | `GET /api/watch` | `api/watch.js` | Signal 2.0 watch board: capture diff (new uploads, movers, crossings) + live-date board (`?kind=`) |
  | `GET /api/cron/signal` | `api/cron/signal.js` | daily refresh: SoundCloud pull → diff → `data/v1/*.json` commit-back (incl. `signal-watch.json`) |
- **Shared helpers** (never routes): `lib/envelope.js`, `lib/fetchx.js`,
  `lib/ratelimit.js`, `lib/cronauth.js`, `lib/github.js`, `lib/signal-watch.js`.
- **Function count: 5** (Hobby limit is plenty; ≤12/site rule respected).
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
| `REPO_STATIC_PREFIX` | with the token | empty string (`data/v1/*.json` at the root) |
| `SOUNDCLOUD_CLIENT_ID` | recommended | public-webapp client_id; skips the ~5.5s key-extraction path |

No secrets in the repo. Ever. Functions degrade gracefully without keys:
no token → read-only cron; no client_id → slower key extraction; pages
always render pre-built static data with an honest "cached · updated HH:MM"
badge when `/api/*` is unreachable.

## Known-good status (2026-10-12, NOT yet deployed)

- `tests/api.test.sh` 37/37 green against the local Vercel-routing emulator
  (Signal 2.0 wave added the `/api/watch` checks + 2 static fallbacks).
- Live cron rehearsal (read-only): 185 tracks fresh from SoundCloud,
  0 new uploads, 7/7 sources ok.
- Static validation: 19,851 relative links, 0 broken; 23/23 JSON schemas
  in validate.sh's stage-3 list (the 2 Signal 2.0 schemas validate against
  their files separately); lyric-grep clean; chain byte-stable; data
  version 0.19.0, 25 manifest endpoints.
- **Not deployed.** Deploy = one-time Vercel CLI from a local clone of
  `-live` (`vercel --prod`), then run the GO_LIVE.md §2 checklist
  (health assert, cron assert, curl roster, functions-disabled pass).

## Build machine

**Standard. Never Turbo.** (Sept 2026 Turbo invoice 1ZU1WJJS-0012: $38.64 —
never repeat it. Static sites = negligible build minutes; Hobby covers them.)

**Function runtime: NEVER pin `runtime` for Node functions — omit the key.**
(Vercel's build validation rejects ANY `"runtime": "nodejsXX.x"` value in the
`functions` map. Node.js is officially supported: omit `runtime` entirely and
Vercel auto-detects Node from `api/`.) The `functions` map must list EXPLICIT
paths (never broad globs), each with at least one valid property — working
choice: `"api/health.js": {"maxDuration": 10}` (10s = Hobby execution limit).
Static data files under `api/` (e.g. `data/v1/trends.flat.js` style JSONP twins)
must NOT live under `api/` — Vercel auto-deploys every `.js` under `api/` as a
serverless function regardless of the `functions` map.

**Vercel never serves static files under `api/` — all static data lives in
`data/v1/`; only real function handlers under `api/`.** (2026-10-12: every
frontend fetch of `api/v1/*.json` 404'd in production — the static JSON was
moved `api/v1/` → `data/v1/`, all generators/JS/docs rewritten. The ONLY
things under `api/` are `.js` files with exported handlers.)

**Generator scripts must emit to `data/v1/`** — a generator that writes
static JSON anywhere under `api/` reintroduces the production 404. Static
`.js` data files (JSONP twins and the like) never live under `api/` either:
they go to `static/v1/` with a `vercel.json` `rewrites` entry preserving
their public URL.
