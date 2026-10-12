---
name: session-compare
description: Head-to-head comparison of any two of the 61 upload sessions — track counts, play totals, date spans, standout tracks, collaborator overlap — plus the transparently-formulated deepest-sessions ranking, from session-tools.json (drives sessions-explorer.html's compare / deepest-cuts / timeline-scrubber sections).
---

# Compare two sessions

## Use when

An agent (or a human) wants to *compare* two upload sessions side by side
("which ran deeper — session-02 or session-43?"), rank sessions by how
quietly they play (the deepest-sessions editorial ranking), or scrub the 61
sessions chronologically. Feeds the `sessions-explorer.html` compare /
deepest-cuts / timeline-scrubber sections.

## Inputs

- `api/v1/session-tools.json` — endpoint #20:
  - `sessions[]` — per-session compare profiles: id, name, span, days,
    `track_count`, `total_plays`, `avg_plays_per_track`, era (with
    `era_deep_dive`), `loudest` + `deepest_cut` tracks (title, plays, date,
    release-page link), title-credited `collaborators[]`, `deep_dive` /
    `journey` / codex `families[]` cross-links, and `play_profile` (each
    transmission's lifetime plays in upload order)
  - `deepest_cuts` — the editorial ranking: stated `formula`, `min_tracks`
    (2), `excluded_single_track_sessions` (33), `ranking[]`
  - `snapshot_history` — the honest no-trajectory state
- Method notes: read `method` first. Play counts are the single 2026-10-11
  snapshot; upload dates ≠ recording dates.

## Procedure

1. Fetch `api/v1/session-tools.json`. Read `method` and `snapshot_history`
   first: the archive holds **one** play-count snapshot (2026-10-11), so no
   per-track play trajectory exists anywhere. `play_profile` is each
   transmission's **lifetime plays in upload order** — never call it a
   trend, and say the snapshot date out loud.
2. For a comparison: pick two sessions from `sessions[]` (by `id`). Report
   track count, total plays, average plays per transmission, date span, era,
   loudest and deepest-cut tracks, and collaborator overlap (only in A /
   in both / only in B). State deltas as B-minus-A arithmetic.
3. For the deepest sessions: read `deepest_cuts.formula` and quote it —
   average plays per transmission = `total_plays / track_count`, ranked
   ascending, minimum 2 transmissions (a single-transmission session is a
   quiet single, not a deep session — the stated editorial rule), tiebreaks:
   lower `total_plays`, then fewer transmissions, then session id. The
   ranking is **editorial**, not an artist fact — say so.
4. For a chronological walk: `sessions[]` is already chronological
   (session-01 → session-61); each profile carries the stop's key stats and
   every cross-link (`deep_dive`, `era_deep_dive`, `journey`,
   `families[].page`).
5. Cross-link out: session deep dives (`sessions/<slug>.html` where
   `deep_dive` is set), era deep dives (`eras/<id>.html`), the Transmission
   journey (`transmission.html#era-<id>`), codex families (`codex/<slug>.html`).

## Worked example

"Compare the loudest session with the deepest session."

- `GET api/v1/session-tools.json` → session-02 ("The February 4th Session",
  2018-02-04): 1 transmission, 30,088 plays, avg 30,088.0 — loudest =
  deepest cut = "Take Me (prod. Em Klebold)" (30,088). Solo run
  (`collaborators: []`). Era: The First Rite.
- session-43 ("The April 16th–18th Session", 2024-04-16 → 2024-04-18):
  2 transmissions, 167 plays, avg 83.5 — the deepest multi-track session on
  record (ranking #1). Loudest: "u Not at the Table (Sunsetzer0) #litemode"
  (139); deepest cut: "Im tha Bouncerrr prod. sustain" (28). Solo run.
  Era: The SomeLowLifes Era; codex family `the-modes`.
- Deltas (session-43 vs session-02): +1 transmission, −29,921 plays,
  −30,004.5 average plays per transmission. Collaborator overlap: none in
  either — both solo runs. Cross-links: session-43's `journey` →
  `transmission.html#era-the-somelowlifes-era`; session-02's era deep dive
  → `eras/the-first-rite.html`.

## API references

- `api/v1/session-tools.json` — 61 compare profiles, the deepest-sessions
  editorial ranking, snapshot-history state (endpoint #20; drives the
  compare / deepest-cuts / scrubber sections of `sessions-explorer.html`)
- `api/v1/session-clusters.json` — the timeline the profiles enrich
  (endpoint #17)
- `api/v1/sessions.json` — raw per-session track lists (endpoint #9)
- `api/v1/codex-families.json` — family pages behind `families[].page`
  (endpoint #18)

## Pitfalls

- **Never draw a play trajectory.** `play_profile` is lifetime totals in
  upload order from one snapshot — calling it a trend invents data.
- The deepest-cuts ranking excludes 33 single-transmission sessions by the
  stated editorial rule — don't re-add them or "correct" the ranking.
- Loudest and deepest cut are the same track in single-transmission
  sessions — say so, don't treat it as a data error.
- `deep_dive` is `null` for sessions outside the top-10 deep dives — fall
  back to the era deep dive or the explorer card anchor.
- Play counts are the 2026-10-11 snapshot; upload dates ≠ recording dates.
  Never quote or reproduce lyrics — titles and metadata only.
