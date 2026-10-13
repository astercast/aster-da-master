# GO LIVE — Aster da Master ("The Signal")

> **LIVE-READY, NOT DEPLOYED. Do not connect Vercel until the user approves.**

> **TWO-TRACK RELEASE MODEL (user's standing order 2026-10-11 — supersedes the
> git-integration hookup steps in §2 below).** This working repo
> (`astercast/aster-da-master`) is NEVER deployed and NEVER connected to Vercel;
> the wave engine builds here continuously. The deployable release lives in the
> private snapshot repo **`astercast/aster-da-master-live`** (clean static
> snapshot, built 2026-10-12 from this working tree).
> - Deploy = **one-time Vercel CLI deploy from a local clone of
>   `aster-da-master-live`. No git integration** (can never auto-deploy).
> - The `-live` snapshot is static-only: no generators, no server functions,
>   no build step. The `api/` server-functions + cron roadmap documented below
>   stays in this working repo and is NOT part of the `-live` snapshot.
> - Future work is GitHub-only: waves keep building here; the `-live` repo is
>   re-synced ONLY on the user's explicit "push"/"ship it". Never push to
>   `-live` from wave-engine automation. Before every push, verify the remote
>   URL matches the intended track.

Last updated: 2026-10-12 (two-track release note; Vercel Wave B — frontend integration).

## 1. What deploys

One Vercel project containing two things:

- **Static frontend** — the whole artist site served from the repo root
  (the existing 22-generator build output; `index.html`, `assets/`, section
  pages, `data/v1/*.json` static files).
- **Server functions** (zero npm dependencies, Node — runtime never pinned in `vercel.json`, envelope-only):
  - `api/health.js` → `GET /api/health`
  - `api/stats.js` → `GET /api/stats`
  - `api/uploads.js` → `GET /api/uploads`
  - `api/watch.js` → `GET /api/watch` (Signal 2.0: watch diff + live-date board)
  - `api/cron/signal.js` → `GET /api/cron/signal` (the one daily cron job)
- **Shared helpers** (never routes): `lib/envelope.js`, `lib/fetchx.js`,
  `lib/ratelimit.js`, `lib/cronauth.js`, `lib/github.js`, `lib/signal-watch.js` (Signal 2.0 diff logic).

Spec: `~/workspace/server-program/ARCHITECTURE.md` §7.4 ("The Signal",
service `aster-signal`). Envelope schema: `data/v1/schema/envelope.json`.

## 2. Hookup steps (exact clicks)

1. **vercel.com/new → Import Git Repository** → select the
   `aster-da-master` repo (private, GitHub-only).
2. **Framework Preset: Other.**
   - Build Command: `python3 scripts/api_manifest.py`
     (timed 0.94s — the full 22-generator chain stays wave-engine
     territory; it is NOT part of the Vercel build).
   - Output Directory: *(leave empty — Vercel default = project root =
     this repo's served root)*.
   - Install Command: `echo 'no dependencies'`.
3. **Environment Variables (Production scope)** — see §3 table.
4. **Build machine: Standard.** Dashboard → Project → Settings → Build &
   Deployment → Build Machine → **Standard**. **Never Turbo** — September
   2026 Turbo build CPU billed **$38.64** (invoice 1ZU1WJJS-0012). These are
   static sites with near-instant builds; Turbo buys nothing.
5. **Deploy.** Open `/api/health` — assert `"status": "ok"` and
   `"functions": ["health", "stats", "uploads", "watch", "cron/signal"]`.
6. **Dashboard → Cron Jobs** — assert one cron: `/api/cron/signal`,
   schedule `0 16 * * *` (UTC). Trigger it once manually (Functions → ⋯ →
   Test) with the secret; read the Functions → Logs lines: every `[cron]`
   line must show `start` + `done` with `sources_ok`.
7. **Curl the roster:**
   `curl https://<site>.vercel.app/api/stats`,
   `curl https://<site>.vercel.app/api/uploads`,
   `curl https://<site>.vercel.app/api/watch`,
   `curl https://<site>.vercel.app/data/v1/uploads.json` —
   assert the envelope schema on the first two, raw JSON on the third.
8. **Disable test** (functions-disabled pass): block `/api/*` (or deploy
   with the functions temporarily removed) → reload `index.html`,
   `glance.html`, `transmission.html` → assert every numbers widget shows
   its pre-rendered static data with an amber **"cached · updated HH:MM"**
   badge and zero blank widgets.

## 3. Env vars

| name | required? | where set | notes |
|---|---|---|---|
| `CRON_SECRET` | **yes** | Vercel → Project → Settings → Environment Variables (Production) | 32+ random hex chars. Vercel auto-sends it as `Authorization: Bearer` on cron invocations. Generate: `node -e "console.log(require('crypto').randomBytes(32).toString('hex'))"`. Rotate by replacing the value + redeploying; cron 401s until both match. |
| `GITHUB_REPO_TOKEN` | required for commit-back | same | Fine-grained PAT, **contents:write on this repo only**, no other scopes. **Pending the user's decision** — until it is set, the cron job runs read-only: it computes fresh data, returns it in its response envelope with `read_only:true`, and does not persist (documented in the Wave A report). |
| `GITHUB_REPO` | yes (with the token) | same | `owner/aster-da-master` — the repo the cron commits to. |
| `REPO_STATIC_PREFIX` | yes (with the token) | same | Empty string for this repo (`data/v1/*.json` at the root). |
| `SOUNDCLOUD_CLIENT_ID` | recommended | same | Public-webapp client_id. Set it and the cron skips the ~5.5s bundle-extraction path (10.6s → ~5s per run on this VM; Vercel datacenter peering is faster). Without it the job extracts + verifies the key from SoundCloud's public webapp itself — no login, no private API. It only reads public track data; it cannot spend anything. |

No secrets in the repo. Ever. Not in code, not in `vercel.json`, not in comments, not in test fixtures.

## 4. Hobby limits

| resource | Hobby limit | our usage |
|---|---|---|
| Bandwidth | 100 GB/mo | static + small JSON; personal-use site ≈ MBs |
| Build minutes | 6,000/mo | seconds per deploy; daily cron redeploys ≈ negligible |
| Function invocations | 100k/mo | edge cache absorbs reads (10-min `s-maxage`); ~1 cron + trickle |
| Function duration | 10s default (Hobby) | all functions designed ≤10s; no `maxDuration` overrides |
| Cron jobs | daily minimum cadence, UTC, ±60min window, prod only | 1 job, `0 16 * * *` UTC (staggered vs the other six sites) |
| Overage billing | **none — usage pauses instead of charging** | design stays far under limits; a pause is a visible signal, not a bill |

If any site approaches 80% of any limit, the wave report flags it and the fix
is *less* work (longer edge TTL, smaller payloads) — never a plan upgrade
without the user's explicit word.

## 5. Cold-start behavior

- First hit 1–3s typical on Hobby (measured on the preview deploy in Wave A;
  the cron's SoundCloud pull is the slowest path at ~4.2s upstream + ~3.2s
  key extraction when `SOUNDCLOUD_CLIENT_ID` is unset — set it at hookup).
- The client gives the live function **7s** (`LIVE_TIMEOUT_MS`), then falls
  back to the static JSON. A cold function that misses the window simply
  loses the race — the user saw a complete page the whole time.
- **First paint never waits for `/api/*`.** Every numbers surface ships
  pre-rendered: `index.html` stat cards + newest-uploads list,
  `glance.html` headline numbers + top-5, `transmission.html` end stats
  (rendered from the bundled JSON). The live swap is progressive enhancement.
- Badge states: `live` (green) = fresh data; `waking server…` (dim pulse) =
  fetch in flight, static data shown meanwhile; `cached · updated HH:MM`
  (amber) = static/stale data with the honest data timestamp; hidden when
  neither source exists (never happens — pages are pre-rendered).
- A degraded live answer (upstreams down) keeps real data with the badge
  flipped to `cached` and the function's `meta.note` as the tooltip — stale
  real data beats fresh fake data, always.

## 6. Cron behavior

- Daily, `0 16 * * *` UTC, production deployments only; Vercel guarantees
  timing only within the hour (may fire 16:00–17:00 UTC).
- Best-effort delivery: missed or duplicate invocations happen. The job is
  idempotent — content-hash commits (`writeJsonIfChanged`: no change → no
  commit → no redeploy), 60-second global duplicate cooldown, dedupe on
  stable upstream IDs.
- Reads current state via the GitHub Contents API (falls back to the
  deployment bundle when the token is unset); bounded incremental refresh
  inside the 10s budget: state reads + SoundCloud pull concurrent,
  per-source 4s/3s timeouts, `Promise.allSettled` (partial success is normal).
- **Alerting is logs only** (`console.log` with fixed prefixes, reviewed in
  Vercel Dashboard → Functions → Logs):
  - `[cron] signal start request_id=...`
  - `[cron] signal done changed=true|false committed=<sha|false> sources_ok=7/7 request_id=...`
  - `[cron] signal fail stage=<fetch|merge|commit> error=<one line> request_id=...`
  - `[upstream] <source> fail error=<one line> latency_ms=...`
  - `[ratelimit] ip=<hash> bucket=public path=...` (hash, never raw IP)
- **A cron job with no `[cron]` line in 48h is itself the alert.**

## 7. Custom domain notes

No custom domain is assigned yet (the SoundCloud profile's recorded
site-link spelling `astredamaster.com` was re-checked 2026-10-13: a plain
fetch of the profile page, HTTP 200, contains no occurrence of that domain
and no external link of any kind, so the spelling remains unverified — do
not invent a domain, and do not visit a guessed one). When one is assigned: add it in Vercel dashboard →
Domains; the `api/*` paths move with the domain automatically (same-origin
`fetch("/api/stats")` needs no changes); update absolute URLs in `llms.txt`
/ sitemap if the domain changes.

**Absolutize at deploy (deploy-time checklist — blocking for social sharing and canonical resolution):** every page
on the site carries `og:image` / `twitter:image` meta pointing at the shared
card, `assets/og-card.png` (Foundry round 2) — but the wiring is
**relative** (`assets/og-card.png` at the root, `../assets/og-card.png` in
subdirectories), because this deployment has no domain yet and none may be
invented. Social crawlers require **absolute** image URLs and do not
resolve relative ones: shared links will render card-less until this is
done. In the `-live` pass, once the deployment's domain exists, absolutize
every `og:image` / `twitter:image` value against it (a root-relative
`/assets/og-card.png` rewrite plus the domain is the minimal form; the
meta lives in the generator HEAD templates and the hand-maintained heads,
so the change is made once per template/head, then the site is rebuilt
and re-grepped for `og:image` to confirm no relative value survives).
**Canonical links (Commons round 10) absolutize in the same pass:** every
page also carries a self-referential `<link rel="canonical">` in the
repo's own canonical path form — a root-relative absolute path
(`/releases/<slug>.html`, `/circle/<slug>.html`, `/index.html`, …) with
no domain, for the same reason. In the `-live` pass, prefix each
canonical's path with the deployment's domain so it becomes a full
absolute URL; a canonical left root-relative is treated as relative by
crawlers and does not consolidate. The canonical lives in the same
generator HEAD templates and hand-maintained heads as the OG meta, so
one edit per template/head covers both; rebuild, then re-grep for
`rel="canonical"` and confirm every value is absolute and each page's
canonical still names itself.

## 8. Rollback

- **Frontend/functions:** `git revert` the offending commit → push → Vercel
  redeploys the previous good state. Functions are stateless; no data
  migration exists.
- **Data (static JSON):** the repo is the database — every cron commit is a
  git commit with a diff. Revert the data commit the same way; the cron's
  content-hash writes mean the next run re-converges instead of fighting you.
- **Snapshot overlay** (`data/playcounts.snapshot.json`): throwaway by
  design; `--merge` backs up `data/artist.json` to `data/artist.json.bak`
  before applying verified counts.

## 9. Cost rules ($38.64 lesson — never repeat)

- **Build machine: Standard. Never Turbo.** Vercel dashboard → Project →
  Settings → Build & Deployment → Build Machine → **Standard**. Turbo is what
  billed $38.64 in September 2026 (invoice 1ZU1WJJS-0012); these static sites
  build in under a second — Turbo buys nothing.
- `installCommand`: `echo 'no dependencies'` — zero npm packages, nothing to
  install, builds stay seconds-long.
- Static builds are the only builds. Function bundling is part of the static
  build (no separate build minutes).
- Hobby gives 100k function invocations/month; the 10-minute edge TTL
  absorbs reads. The one daily cron is the only scheduled invocation.
- The user's standing order: automated loops must never hammer the repo with
  pushes — that, not the build machine, was the real cost driver.

## 10. What Wave B wired (frontend integration)

- `assets/js/api-client.js` — the spec's `fetchWithFallback` reference
  implementation, verbatim (7s live timeout; `live`/`waking`/`cached`/`none`
  badge states; never rejects).
- `assets/js/signal.js` — site-specific wiring: numbers refresh from
  `/api/stats` → fallback `data/v1/stats-snapshots.json`; newest-uploads
  refresh from `/api/uploads` → fallback `data/v1/uploads.json`. Repaints only
  on live answers; cached results keep the pre-rendered numbers.
- Wired surfaces (each ships pre-rendered; badge = `<span class="api-badge"
  role="status" aria-live="polite">`):
  - `index.html` — "Let the work speak" stat cards + "Fresh from the source"
    newest-uploads list (pre-rendered: 257,394 plays / 185 vault tracks /
    219 transmissions / 2017–2026; newest upload 2026-10-02).
  - `glance.html` (generator: `scripts/build_glance.py`) — headline numbers
    (`data-signal="plays"` / `"tracks"` hooks) + top-5 plays
    (`data-signal-top` per title).
  - `transmission.html` — end-journey stats (plays cell repainted live).
- Badge CSS in `assets/css/components.css` (`.api-badge`, four states,
  reduced-motion safe, mobile-sized).
- The Signal deals in numbers only. No lyrics reproduced, no bio facts invented.

## 11. Verification status (Wave B, 2026-10-12)

- `scripts/validate.sh` — 8/8 stages pass (16,835+ links, 0 broken; 23/23
  schemas; lyric-grep clean; 22-generator chain byte-stable).
- `tests/api.test.sh` — 31/31 green against `tests/local_server.js`.
- Functions-disabled pass: static fallback renders fully; every widget shows
  cached data with honest "updated HH:MM" badges; zero blank widgets.
- Cold-start: first paint is static-complete; live swap lands when the
  function warms (verified locally; preview-deploy timing recorded at
  hookup).
- Do NOT deploy until the user reviews all seven sites and says go.
