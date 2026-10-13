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
- Second Capture wave (2026-10-12): fresh refresh capture
  2026-10-12T23:22:57Z (185 tracks, 257,409 plays, +13 vs the stand-up
  capture, 3 movers, first honest per-day rates — gap 1.05 days).
  Captures archived whole under `data/captures/`; snapshot ledger at
  2 rows. `scripts/test_signal_watch.js` 27/27 (both real capture pairs
  pinned; JS/Python diff parity proven). `refresh_plays.py` status path
  fixed: `data/v1/refresh-status.json`, never `api/v1/` again.
- Signal 2.1 wave (2026-10-13): capture #3 NOT taken — the 24h gate from
  capture #2 opens 2026-10-13T23:22:57Z; the ledger honestly stays at
  2 rows / 257,409 plays and `signal.html` prints the gate. Live-date
  board re-swept 2026-10-13 (`checked_at` 2026-10-13): Oct 15 party,
  Oct 16 release, Oct 28 Seattle and Oct 29 Portland all held; the
  Oct 29 Gold Diggers card gained a JamBase listing (7:00 PM start +
  5632 Santa Monica Blvd address, price still unrecorded); the JamBase
  Sam Buck conflict for Oct 15 still stands. `tests/api.test.sh` 37/37
  (start `tests/local_server.js` first or every check fails
  environmentally); release-week tests 20/20.
- Rotation 6 final pre-event check (2026-10-13 02:29 UTC):
  capture #3 NOT taken — the ledger was checked first and still holds
  2 rows / 2 archive files, so the daily cron has not produced a
  post-gate capture to adopt; the gate opens 2026-10-13T23:22:57Z
  (20h 54m after this pass) and the Rotation 5 six-step procedure
  stays armed. All eight focus sources were opened a third time —
  venue calendar, Bandsintown, JamBase (Sam Buck + Gold Diggers),
  Stereogum, upcomingvinyl, both Eventbrite listings — and every
  date held again; the JamBase Sam Buck conflict still stands and
  the Gold Diggers $15 line stays noted, not priced. Post-event
  steps confirmed armed in `data/release-week-uncle.json`
  (`post_party_recheck` + the five-step release flip, capture slot
  honestly null). Tests: signal-watch 27/27, release-week 20/20,
  api 37/37; screenshots clean.
- Rotation 5 readiness pass (2026-10-13, later the same UTC day):
  capture #3 NOT taken — gate opens 2026-10-13T23:22:57Z and is armed
  in WAVELOG with the exact six-step procedure. All focus dates held a
  second time against live sources opened directly (venue calendar,
  Bandsintown, JamBase's own Sam Buck listing, Stereogum, upcomingvinyl,
  Faygoluvers, AltPress, both Eventbrite listings); the JamBase Sam Buck
  conflict still stands. JamBase's Gold Diggers listing now shows a $15
  ticket line — noted in the event note, price field still unrecorded
  (aggregator, not primary). Post-event work armed in
  `data/release-week-uncle.json`: `post_party_recheck` (post–Oct 15)
  alongside the five-step post–Oct 16 release flip. Tests: signal-watch
  27/27, release-week 20/20, api 37/37; screenshots clean.
- Static validation: 19,851 relative links, 0 broken; 23/23 JSON schemas
  in validate.sh's stage-3 list (the 2 Signal 2.0 schemas validate against
  their files separately); lyric-grep clean; chain byte-stable; data
  version 0.19.0, 25 manifest endpoints.
- **Not deployed.** Deploy = one-time Vercel CLI from a local clone of
  `-live` (`vercel --prod`), then run the GO_LIVE.md §2 checklist
  (health assert, cron assert, curl roster, functions-disabled pass).

## Free-tier / best-pattern audit (Rotation 12, 2026-10-13)

Measured in the working repo; the `-live` snapshot inherits all of it on
the next user-ordered sync.

- **Function count: 5 of the ≤12/site cap** (Hobby allows 100k
  invocations/mo). All explicit paths in `vercel.json`, each
  `{"maxDuration": 10}`, no `runtime` keys, zero npm dependencies.
  Handler sizes: health 115 lines, stats 167, uploads 142, watch 119,
  cron/signal 488 (the only non-trivial handler; it is cron-only).
- **Estimated monthly invocations.** Assumption, stated: a niche archive
  at **5,000 visits/month**. Pages are static-first and pre-rendered;
  the only client-side function calls are `/api/watch` (Signal page),
  `/api/stats` + `/api/uploads` (glance / transmission / signal) —
  ≈1.3 calls per visit before caching. Every GET envelope already
  ships `Cache-Control: public, s-maxage=600,
  stale-while-revalidate=86400`, so the edge collapses repeat hits:
  realistic origin invocations ≈ **6,500/month** (every visit a cache
  miss), hard worst case ≈ **17,300/month** (4 public endpoints ×
  4,320 ten-minute windows) — **6–17% of the Hobby cap**. Cron adds
  30/month (one daily job). Nothing bills: no paid APIs anywhere
  (SoundCloud public api-v2 + GitHub Contents API only), static
  bandwidth is pre-built HTML + JSON (largest data file 220 KB).
- **Worst-case duration vs the 10s ceiling.** Public handlers measured
  against the local emulator: health 17 ms, watch 47 ms, stats 55 ms
  (its per-source reads report 1–14 ms), uploads 123 ms — three
  orders of magnitude under the ceiling, cold starts included at this
  payload size. The cron is the only handler that can approach it:
  with `SOUNDCLOUD_CLIENT_ID` set (the recommended configuration) it
  is one 4 s-bounded resolve + one tracks page (185 tracks ≤ the
  200/page limit) with state reads and commit-back writes in
  parallel — a few seconds typical.
- **First degradation point: the cron's no-env-key path.** Without
  `SOUNDCLOUD_CLIENT_ID`, client-id extraction runs up to three
  sequential 3 s-bounded phases (≈9 s) before the tracks pull
  (up to 3 sequential 4 s pages) — that stack can exceed 10 s and
  Vercel will kill the run. The failure is bounded and honest by
  construction: writes happen only after a successful pull, so
  nothing is half-written, the next daily run retries, and the
  public site never notices (static JSON + honest "cached" badges).
  Mitigation is configuration, not code: keep
  `SOUNDCLOUD_CLIENT_ID` set in Production. Second degradation
  point: the per-instance in-memory rate limiter (60 req/min/IP)
  resets on cold start — best-effort by design, backstopped by the
  edge cache.
- **Pattern alignment.** Static-first (every page reads correctly
  with no JS and no functions); precomputed JSON for everything
  (`data/v1/*.json`, 25 manifest endpoints); SWR caching on function
  GETs via the shared envelope; **fixed this rotation:** `data/v1/*`
  static JSON previously had no explicit cache header in
  `vercel.json` — it now carries the same
  `public, max-age=0, s-maxage=600, stale-while-revalidate=86400`
  rule as the envelope, so precomputed data gets identical edge
  treatment. Honest upstream-failure fallbacks everywhere: handlers
  return a degraded envelope or a plain 502 and the frontend falls
  back to the static file with a "cached · updated HH:MM" badge
  (`ApiClient.fetchWithFallback`); `/api/health` surfaces the
  function roster + per-file freshness against a 24 h SLA and never
  returns 5xx (degraded ≠ down). The Signal ledger's printed state
  (2 captures, gate armed) is this site's health surface in public:
  what is stale says so, in plain words, on the page.

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
