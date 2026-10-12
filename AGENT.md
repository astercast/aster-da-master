# AGENT.md — How an agent uses the Aster da Master archive

This repo is built to be driven by agents, not just read by humans. Two
interfaces: **skills** (task procedures — the primary interface for *doing*
work) and the **JSON API** (the data layer behind them). `llms.txt` is the
short index, `llms-full.txt` the full brief, `API.md` the human-readable API
reference, `agents.html` the browsable agentic surface. This file is the
operator's manual.

## Base URL pattern

Base: **`api/v1/`** relative to the repo root or the deployed site root.
Static files — **no auth, no keys, no rate limits**. Works on any static host.

- Start at **`api/v1/index.json`** — the self-describing manifest: every
  endpoint with its `description`, schema URL (`api/v1/schema/*.json`),
  `updated` timestamp, `records` count, and deprecation `notes`. Also carries
  `meta` (version/generated/base/auth), the `skills` registry, and the
  `documents` map (this file, `agents.html`, `API.md`, `llms.txt`,
  `llms-full.txt`).
- For task procedures: **`skills/index.json`** → load the skill file whose
  task matches the request. Each skill is: Use when, Inputs, Procedure,
  Worked example, API references, Pitfalls.
- Shared conventions (timestamps, versions, errors, pagination, freshness):
  the "Shared API conventions" block in `API.md`.

## Key endpoints

| Endpoint | Contents | Records |
|---|---|---|
| `api/v1/index.json` | Manifest — start here | 15 endpoints |
| `api/v1/artist.json` | The source of truth: bio, facts, discography (219 entries), platforms, eras, vault, upcoming | 219 |
| `api/v1/codex.json` | The vocabulary codex: 16 word families with per-family track lists | 16 |
| `api/v1/release-slugs.json` | Slug index: ordinal string → release-page slug (the search overlay's corpus) | 219 |
| `api/v1/on-this-day.json` | Calendar index: transmissions keyed by MM-DD upload date | 96 days |
| `api/v1/years.json` | Year-in-review archive: per-year stats and highlights, 2018–2026 | 9 |
| `api/v1/circle.json` | The 21 title-credited collaborators and their per-track footprint | 21 |
| `api/v1/milestones.json` | Career firsts computed from the verified discography: firsts, records, silences | 9 |
| `api/v1/sessions.json` | 61 upload sessions clustered from vault upload dates (7-day gap rule) | 61 |
| `api/v1/changelog.json` | Site construction history, generated from the git log | 29 entries |
| `api/v1/first-last.json` | Per year 2018–2026: the opening and closing transmissions | 9 |
| `api/v1/milestone-watch.json` | Vault tracks near round-number play counts | bands |
| `api/v1/scene-figures.json` | Producer/scene figures outside the 21 (e.g. Fish Narc), with facts + sources | 1 |
| `api/v1/transmission.json` | The guided journey: six eras with stats, top tracks, key sessions, collaborators, milestones, computed "signal" lines | 6 |
| `api/v1/network.json` | Collaboration network: 23 nodes, 27 track-weighted edges, co-credit links, computed insights | 23 nodes |

Example requests (Node; swap `fs` for `fetch` in a browser):

```js
const fs = require("fs");
const J = p => JSON.parse(fs.readFileSync(p, "utf8"));

// manifest first: confirm version before caching anything
const idx = J("api/v1/index.json");
console.log(idx.meta.version, idx.endpoints.network.records); // 0.12.0 23

// top 5 vault tracks by plays (plays = 2026-10-11 snapshot)
const artist = J("api/v1/artist.json");
const vault = artist.discography.filter(e => e.type === "SoundCloud-only" && Number.isInteger(e.plays));
vault.sort((a, b) => b.plays - a.plays).slice(0, 5)
  .forEach(e => console.log(e.plays, e.title));

// a collaborator's footprint
const circle = J("api/v1/circle.json");
const mf = circle["max-ferrari"];
console.log(mf.shared_transmissions, mf.shared_plays, mf.years_active); // 8 13618 2018–2025
```

## Example workflow 1 — brief me on the SomeLowLifes era

*Skill: [`era-briefing`](skills/era-briefing.md). Question → "what happened in the SomeLowLifes era?"*

1. **`GET api/v1/transmission.json`** — find the era named "The SomeLowLifes Era"
   (`span` "2023 – 2024"): 58 transmissions, 14,982 plays, 2 distributor
   releases. Read its `signal`: "After a 553-day silence — the longest gap on
   record — the vault returned with 58 transmissions…"
2. **`GET api/v1/milestones.json`** — pull `longest-silence`: 553 days,
   2022-02-22 → 2023-08-29. This is the gap the era's signal refers to; the
   era is where the silence *broke*.
3. Same era object: `key_sessions` → "The November 3rd–12th Session"
   (19 tracks, 7,601 plays — the most prolific session on record) and
   `milestones` → `prolific-day` ("17 transmissions uploaded in a single day",
   2023-11-12). `collaborators` → lil yu, Max Ferrari, Max (1 track each).
4. **`GET api/v1/years.json`** — 2023: 26 vault transmissions; 2024: 20.
   Cross-check the era totals (58 = 2023+2024 discography entries).
5. Write the brief as: **the span** (2023–2024, after the 553-day silence),
   **the numbers** (58 transmissions / 14,982 plays, every figure traced to a
   field), **the story** (the vault's return, the November 2023 outpouring).
   State what is unknown — e.g. *why* the silence happened is not in the
   archive; do not speculate.

## Example workflow 2 — find the 10 quietest deep cuts

*Skill: [`deep-cuts-finder`](skills/deep-cuts-finder.md). Question → "what are the 10 quietest deep cuts?"*

1. **`GET api/v1/artist.json`** (or `api/v1/sessions.json` flattened) —
   take `discography[]`, filter `type === "SoundCloud-only"` with integer
   `plays`. Median vault track ≈ 450 plays; anything far below is a genuine
   deep cut.
2. Sort ascending by `plays`; take the bottom 10. Verified 2026-10-11 bottom
   ten: "nitemode2019 w/ Max+Vetty prod. NaXi.wav" (17), "No Puppets A11owed
   prod. xtasane" (24), "Im tha Bouncerrr prod. sustain" (28), "For Brian
   (Neck Deep) outro [produced by AWFL]" (43), "6 stop telling myself i'm not"
   (46), "10 stuck in the mix v2" (58), "7 don't say u love me" (69),
   "2 menace" (97), "11 dismissed" (98), "8 i would do mine" (104).
3. **`GET api/v1/codex.json`** — match title words to families for a playlist
   theme (several picks carry "The Modes" words).
4. Present title, plays, upload date, and one line on why each qualifies.
   Quote titles verbatim; **never quote lyrics** — the archive carries titles
   and metadata only.

## Example workflow 3 — trace every Max Ferrari collaboration

*Skill: [`collaborator-tracer`](skills/collaborator-tracer.md) +
[`network-graph-reader`](skills/network-graph-reader.md). Question → "trace every Max Ferrari collaboration."*

1. **`GET api/v1/circle.json`** — look up slug `max-ferrari`: 8 shared
   transmissions, 13,618 shared plays, active 2018–2025. Read all 8 tracks
   chronologically, from "DESTINY (ft. JAX & Max Ferrari) ~ [prod. louky]"
   (2018-08-20, 2,000 plays) through "Sti11 waiting/tunnel freestyle w/ Max
   Ferrari prod. suli" and "ARCSNOWWW w/ Max Ferrari prod. sustain"
   (2025-11-11). Note the 2019 peak: "NIGHT MODE ft. MAX FERRARI x YUNG VETTA
   x JAX" (10,083 plays — the loudest shared track).
2. **`GET api/v1/network.json`** — `insights.most_frequent_collaborator` is
   Max Ferrari ×8 (confirmation, not a new claim). Find his co-credit edges:
   `jax ↔ max-ferrari` (weight 2 — "DESTINY" and "NIGHT MODE") and
   `max-ferrari ↔ yung-vetta` (weight 1 — "NIGHT MODE"). These are the only
   multi-collaborator tracks in his footprint.
3. Pitfall check: the circle also has separate `max` and `vetty` entries
   ("nitemode2019 w/ Max+Vetty") — near-duplicate slugs, different people.
   Match exactly; do not merge.
4. Summarize as: **who** (Max Ferrari, most frequent collaborator ×8),
   **footprint** (8 tracks, 13,618 plays, 2018–2025), **the tracks**
   (chronological, with plays), **the network** (co-credit links to JAX and
   Yung Vetta). Anything beyond the endpoints — how they met, who introduced
   whom — is unknown; say so.

## Rates & expectations

- **Static JSON; no auth, no keys, no rate limits.** Fetch freely, but serve
  over HTTP: browsers block `fetch()` from `file://` pages.
- **Play counts are a 2026-10-11 snapshot** (`plays_snapshot` / `observed`
  fields). They drift daily — always state the snapshot date, never present
  them as live.
- **Upload dates ≠ recording dates.** Sessions are computed clusters (7-day
  upload-gap rule), not artist-named studio sessions.
- **Sizes are small.** Largest: `artist.json` (~155 KB). Cache aggressively;
  check `index.json → meta.version` (currently `0.12.0`) to invalidate.
- **The rules of the archive:** titles and metadata only — **never lyrics**;
  never invent biography; unknowns are listed as unknowns (`method.html` →
  "The unknowns register"); the circle is title-credit only (producers live
  in `scene-figures.json`).
- **Empty results are `[]`, never `null`.** A missing endpoint means a wrong
  path — re-read `index.json`.
