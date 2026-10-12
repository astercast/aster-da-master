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
| `api/v1/index.json` | Manifest — start here | 22 endpoints |
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
| `api/v1/scene-figures.json` | Producer/scene figures outside the 21 (e.g. Fish Narc), with facts + sources; figures carrying an announced record add an optional `watch` block (`label`, `status` = `announced`/`released`, `expected`, `as_of`, `note`) — `announced` means not yet confirmed released, never read it as released early | 1 |
| `api/v1/transmission.json` | The guided journey: 13 stops — six eras with stats, top tracks, key sessions, collaborators, milestones, computed "signal" lines, plus seven live data chapters (The Race, The Record Book, The Codex, The Architects, The Seasons, The Deep Cuts, The Horizon) | 6 eras + 7 chapters |
| `api/v1/network.json` | Collaboration network: 23 nodes, 27 track-weighted edges, co-credit links, computed insights | 23 nodes |
| `api/v1/eras.json` | Era deep-dives: six eras with full transmission lists (every track + plays), ALL in-era collaborators, active codex families, milestones, computed signal lines and summaries | 6 |
| `api/v1/session-clusters.json` | Session archaeology, interactive: the 61 sessions as an explorable timeline — per-session enrichment (era, loudest + deepest-cut tracks, cross-links), the 60 inter-session gaps, 9 activity seasons, asserted insights. Drives `sessions-explorer.html` | 9 seasons |
| `api/v1/codex-families.json` | Codex family deep-dives: 16 vocabulary families with decoded readings, era-by-era evolution, key sessions, title-credited collaborators. Drives the `codex/<slug>.html` pages | 16 |
| `api/v1/milestone-races.json` | The milestone race 2.0: approaching play-count milestones ranked by gap-closing proximity (current value, target, gap, pace arithmetic — estimates, never predictions), race any two of the 185 vault tracks head-to-head at any milestone target (the vault pace database, client-side mirror of the asserted pair math), The Climb (all 182 summit-eligible tracks ranked by catch time), race history (decided races: dated crossings, 1k/10k/20k/30k threshold winners, the 115-day photo finish), the computed race of the week (share card), the 30,088-play summit chase, session + era records. The 2026-10-11 snapshot was independently re-captured (185/185 tracks, zero play-count differences). Drives `milestone-race.html` | 4 races, 185-track pace db, 182-track climb |
| `api/v1/session-tools.json` | Session explorer 2.0 tooling: 61 per-session compare profiles (stats, loudest + deepest-cut tracks, collaborators, play profiles, family/session/era/journey cross-links), the deepest-sessions editorial ranking (lowest average plays per transmission, min 2 transmissions, formula stated in the payload — editorial, not an artist fact), and the honest snapshot-history state (one 2026-10-11 snapshot: no play trajectories exist). Drives the compare / deepest-cuts / timeline-scrubber sections of `sessions-explorer.html` | 61 profiles |
| `api/v1/codex-network.json` | The codex relationship graph: 16 word families as nodes, shared title-credited collaborators and title-parsed producers as edges, BFS degrees of separation from Aster, the family-overlap graph, and connect-the-dots shortest-path data. Drives `codex-network.html` | 70 nodes |
| `api/v1/producer-deepdives.json` | Producer deep-dives: every as-credited producer (title prod./produced-by fragments, verbatim) with credited productions (release/session links, co-producers, title-credited voices), codex family ties, a computed production fingerprint, and sourced research where a research pass exists. Drives `producers/<slug>.html` | 113 producers |

Example requests (Node; swap `fs` for `fetch` in a browser):

```js
const fs = require("fs");
const J = p => JSON.parse(fs.readFileSync(p, "utf8"));

// manifest first: confirm version before caching anything
const idx = J("api/v1/index.json");
console.log(idx.meta.version, idx.endpoints.network.records); // 0.15.0 23

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

## Example workflow 4 — deep-dive one era

*Skill: [`era-briefing`](skills/era-briefing.md). Question → "deep-dive the
SomeLowLifes era."*

1. **`GET api/v1/eras.json`** — pick the era by `id` (`the-somelowlifes-era`).
   One file now answers the whole brief: `summary`, `tracks[]`,
   `collaborators[]`, `codex_families[]`, `key_sessions[]`, `milestones[]`.
2. **Read `summary` first** — every figure there is recomputed and asserted
   by `scripts/build_eras.py`: The SomeLowLifes Era is rank #2 of 6 by
   transmissions (58) and by plays (14,982 — 5.82% of the archive); busiest
   year 2023 (31 transmissions, 10,179 plays); loudest transmission "Clock
   In The Benz w/ Lil Yu prod shinju" (725 plays); deepest cut "nitemode2019
   w/ Max+Vetty prod. NaXi.wav" (17 plays); most-played codex family "The
   Rites" (7 transmissions, 2,243 plays); 5 collaborators carrying 8.5% of
   the era's plays; 3 milestones filed.
3. **Walk `tracks[]`** for the full transmission list (every entry with
   release-page link; distributor releases carry no vault play count),
   **`collaborators[]`** for every in-era voice (lil yu, and 4 more —
   `transmission.json` keeps only the top 3), **`codex_families[]`** for the
   era's vocabulary.
4. Pitfall check: play counts are the 2026-10-11 snapshot; upload dates ≠
   recording dates. Never quote or reproduce lyrics — titles and metadata
   only.

## Example workflow 5 — explore the sessions timeline

*Skill: [`session-explorer`](skills/session-explorer.md). Question → "walk me
through the upload sessions: the seasons, the silences, the standout
sessions."*

1. **`GET api/v1/session-clusters.json`** — the whole timeline in one file.
   Read `method` first: the 61 sessions come from the 7-day upload-gap rule;
   the 9 `clusters[]` ("activity seasons") are a *computed browsing
   convention* — consecutive sessions while the separating silence is ≤ 90
   days — not artist-named eras.
2. **`insights`** holds the headline numbers (all recomputed and asserted by
   `scripts/build_session_clusters.py`): `most_prolific` is session-40, "The
   November 3rd–12th Session" (2023-11-03 → 2023-11-12, 19 tracks, 7,601
   plays); `longest_silence` is 553 days, session-36 → session-37
   (2022-02-22 → 2023-08-29, matches `milestones.json`'s longest-silence
   record); `loudest_session` is session-02 (30,088 plays), `quietest_session`
   is session-52 (17 plays).
3. **Drill into `sessions[]`**: session-40's `deepest_cut` is "For Brian
   (Neck Deep) outro [produced by AWFL]" (43 plays), its `loudest` is "On Our
   Way (Baseline)" (696 plays), `collaborators` is empty (solo run — producer
   credits excluded by rule), `deep_dive` points at
   `sessions/the-november-3rd-12th-session.html`, and `journey` lands on the
   SomeLowLifes node of the transmission journey. `silences` names the five
   longest upload gaps; `gaps[]` carries all 60 for charting.
4. Pitfall check: sessions and seasons are computed clusters — say
   "clustered" when the distinction matters. Play counts are the 2026-10-11
   snapshot; upload dates ≠ recording dates. Never quote or reproduce lyrics
   — titles and metadata only.

## Example workflow 6 — trace a codex family

*Skill: [`codex-reader`](skills/codex-reader.md). Question → "trace The Modes
family: what does it mean, and how did it evolve?"*

1. **`GET api/v1/codex-families.json`** — find the family by `slug`
   (`the-modes`): 5 transmissions, 10,864 plays, words `litemode`,
   `nitemode`, `night mode`, page `codex/the-modes.html`.
2. **Read `decoded` FIRST** — `status` is `"unknown"`: the archive assigns no
   meaning to the mode-words. `litemode`/`nitemode` appear in titles but no
   index source defines them — tallied, never translated (the unknowns
   register on `method.html`, re-checked 2026-10-11). **Do not supply a
   meaning the archive doesn't claim.**
3. **Walk `eras[]` for the evolution** — first appearance "NIGHT MODE ft.
   MAX FERRARI x YUNG VETTA x JAX" (2019-07-09, 10,083 plays, The First
   Rite), latest "big litemode (prod runawway, ilyagargod & k3nik)"
   (2025-11-23, 455 plays, The Silence); 3 family
   transmissions sit in The SomeLowLifes Era (326 plays — the word's quiet
   middle years). `deep_dive` and `journey` links land on the era pages.
4. **`key_sessions[]`** names the 5 upload sessions carrying the words
   (session deep-dive link where one exists, e.g. The July 9th Session);
   **`collaborators[]`** names the voices — JAX, Max Ferrari, Yung Vetta
   ("NIGHT MODE"), Max, Vetty ("nitemode2019") — with `circle/` page links.
5. Pitfall check: a `decoded.status` of `"stated"` means the reading is the
   family's `epithet` quoted verbatim (site framing of title vocabulary,
   not an artist statement). Distributor releases have no session record
   and no vault play count. Never quote or reproduce lyrics — titles and
   metadata only.

## Example workflow 7 — race the milestones

*Skill: [`milestone-race-reader`](skills/milestone-race-reader.md). Question → "what's the closest race in the archive, and who can catch the summit?"*

1. **`GET api/v1/milestone-races.json`** — read `plays_snapshot` first
   (2026-10-11): this is a snapshot, not a live leaderboard.
2. **`closest_races[0]`** — the closest race in the archive: "master key ft.
   Lil Wintr x Marcelo (prod. ginseng)", 9,615 of 10,000 plays, 385 needed,
   pace ~3.84 plays/day → at this lifetime pace, ~100.3 days (estimate, not a
   prediction). **`race_of_the_week`** names the same race — computed from
   the snapshot, not editorial — with a share card.
3. **`head_to_head` + `vault_pace`** — race any two of the 185 vault tracks at any milestone target (1k/10k/20k/30k): `needed = target − plays`, `days_at_pace = needed ÷ pace_per_day` (the page mirrors the generator's `project_pair` exactly, banker's rounding included). A track already past the line has no race to run — the table says so. The 6 featured pairs (active races at their band targets) are precomputed and asserted; the closest is "master key" vs "When the World Gets Colder (prod. Brokn)", 46.4 days apart. **`the_climb`** — all 182 summit-eligible tracks ranked by catch time at lifetime pace (top 5 = the summit contenders).
4. **`summit_race`** — holder "Take Me (prod. Em Klebold)" at 30,088 plays
   (2018-02-04). Closest contender: "candy w/ capoxxo(prod. razorwrist)" —
   11,587 plays, 18,501 behind, catch time ~4,093.1 days at lifetime pace.
   Contenders are tracks uploaded before 2026-07-13 (`eligibility`): pace
   needs a track record.
5. **`race_history`** — the decided races: all 8 dated milestone crossings,
   the 1k/10k/20k/30k threshold winners (57 / 5 / 1 / 1 tracks past it; "Take
   Me" leads every band; crossing dates are NOT recorded — the archive holds
   one snapshot, and the method says so), and the photo finish — "First vault
   transmission" vs "First collaboration", 115 days apart, the tightest
   back-to-back recorded crossings.
6. **`session_records` / `era_records`** — the standing records: most-prolific
   session = The November 3rd–12th Session (19 tracks); longest silence =
   553 days (session-36 → session-37); era with most plays = The First Rite
   (220,688). **`just_crossed`** — most recent: "Latest transmission"
   (2026-10-02), then "250,000 plays crossed" (2024-05-28).
7. Pitfall check: `pace_per_day` is snapshot plays ÷ days from upload to
   snapshot — a lifetime average, not a current rate. `days_at_pace` and
   `catch_days_at_pace` are plain division. **Say "estimate, not a prediction"
   out loud in every report.** Never quote or reproduce lyrics — titles and
   metadata only.

## Rates & expectations

- **Static JSON; no auth, no keys, no rate limits.** Fetch freely, but serve
  over HTTP: browsers block `fetch()` from `file://` pages.
- **Play counts are a 2026-10-11 snapshot** (`plays_snapshot` / `observed`
  fields). They drift daily — always state the snapshot date, never present
  them as live.
- **Upload dates ≠ recording dates.** Sessions are computed clusters (7-day
  upload-gap rule), not artist-named studio sessions.
- **Sizes are small.** Largest: `artist.json` (~155 KB). Cache aggressively;
  check `index.json → meta.version` (currently `0.15.0`) to invalidate.
- **The rules of the archive:** titles and metadata only — **never lyrics**;
  never invent biography; unknowns are listed as unknowns (`method.html` →
  "The unknowns register"); the circle is title-credit only (producers live
  in `scene-figures.json`).
- **Empty results are `[]`, never `null`.** A missing endpoint means a wrong
  path — re-read `index.json`.
