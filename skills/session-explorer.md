---
name: session-explorer
description: Browse the 61 upload sessions as an explorable timeline — activity seasons, the 553-day silence, most-prolific and quietest sessions, era/year filters — from session-clusters.json (and the sessions-explorer.html page).
---

# Explore the sessions timeline

## Use when

An agent (or a human) wants to *browse* the upload sessions rather than
reconstruct one: the nine activity seasons, the silences between sessions,
which session was most prolific, which is the quietest, which era a session
sits in. Feeds the `sessions-explorer.html` page and any timeline feature.

## Inputs

- `api/v1/session-clusters.json` — the whole explorable timeline in one file:
  per-session enrichment, the 60 inter-session gaps, the 9 activity seasons,
  the top-5 silences, asserted insights
- Optional: `api/v1/sessions.json` — per-session track lists with plays
  (the explorer lazy-loads it when a session card expands)

## Procedure

1. Fetch `api/v1/session-clusters.json`. Read `method` first — it states the
   computed conventions: the **7-day upload-gap rule** builds the 61 sessions;
   **activity seasons** group consecutive sessions while the separating silence
   is ≤ 90 days (a browsing convention, not an artist fact); upload dates are
   **not** recording dates; plays are the 2026-10-11 snapshot.
2. `insights` holds the headline numbers, all recomputed and asserted by
   `scripts/build_session_clusters.py`:
   - `most_prolific` — session-40, "The November 3rd–12th Session" (2023-11-03
     → 2023-11-12, 19 tracks, 7,601 plays)
   - `longest_silence` — 553 days, session-36 → session-37 (2022-02-22 →
     2023-08-29); the full top-5 silences live in `silences`
   - `loudest_session` — session-02 (30,088 plays);
     `quietest_session` — session-52 (17 plays)
   - `season_count` — 9; `session_count` — 61
3. Walk `clusters[]` for the seasons (span, session/tracks/plays counts,
   `session_ids`) and `sessions[]` for the per-session story: `era_id` /
   `era_name` (six eras, cross-linked via `journey` →
   `transmission.html#era-<id>` and the era `deep_dive` page),
   `loudest` / `deepest_cut` (session min/max plays), `collaborators`
   (w//ft. title credits, producers excluded), `deep_dive`
   (`sessions/<slug>.html` for the top-10 sessions, `null` otherwise).
4. For track-level detail on any session, fetch `api/v1/sessions.json` and
   find the session by `id` — `tracks[]` carries title, date, plays, page.
5. The human-facing page `sessions-explorer.html` renders all of this with
   era/year filters, the gap visualization, and the session cards.

## Worked example

"Which session is the most prolific, and what is its deepest cut?"

- `GET api/v1/session-clusters.json` → `insights.most_prolific`:
  session-40, "The November 3rd–12th Session", 2023-11-03 → 2023-11-12,
  19 tracks, 7,601 plays, season-06.
- The session row's `deepest_cut`: "For Brian (Neck Deep) outro
  [produced by AWFL]" — 43 plays (2023-11-12); its `loudest`:
  "On Our Way (Baseline)" — 696 plays. No title-credited collaborators
  (`collaborators: []` — producer credits excluded by rule).
- Cross-links: `deep_dive` → `sessions/the-november-3rd-12th-session.html`,
  `era_id` → `the-somelowlifes-era` (`eras/the-somelowlifes-era.html`,
  `transmission.html#era-the-somelowlifes-era`).

## API references

- `api/v1/session-clusters.json` — the explorable timeline: 61 enriched
  sessions, 60 gaps, 9 seasons, insights (endpoint #17; drives
  `sessions-explorer.html`)
- `api/v1/sessions.json` — the 61 sessions with per-track plays
  (track lists for expanded session cards)
- `api/v1/eras.json` — the six eras with deep-dive pages and journey links
- `api/v1/milestones.json` — `longest-silence` record (canonical source the
  generator asserts against)

## Pitfalls

- Upload dates are **not** recording dates. Never claim a track was recorded
  in its upload week.
- Sessions and seasons are **computed** (7-day rule / 90-day convention),
  not artist-named. Say "clustered" when the distinction matters.
- The 553-day silence is measured upload-to-upload (2022-02-22 → 2023-08-29);
  the gap objects count it canonically the same way.
- Plays are a 2026-10-11 snapshot. Session "importance" is about the story,
  not the play rank.
- If a collaborator isn't in `circle.json`, check `scene-figures.json` before
  concluding they're unknown — producers are excluded from the circle by
  rule, not by absence.
- No invented color: no studio details, no moods, no quotes — unless an
  endpoint (or a cited source on a circle page) says it.
