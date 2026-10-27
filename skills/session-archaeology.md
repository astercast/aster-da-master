---
name: session-archaeology
description: Reconstruct a recording session's story — when it happened, what came out of it, who was in the room — from sessions.json plus the codex and circle endpoints.
---

# Reconstruct a session's story

## Use when

An agent wants the narrative behind one of the 61 upload sessions: what was happening, who collaborated, what the titles signal. Feeds writeups, timelines, "this week in the archive" features.

## Inputs

- A session id (`session-01` … `session-61`) from `data/v1/sessions.json`
- Optional: a collaborator slug or codex word to angle the story

## Procedure

1. Fetch `data/v1/sessions.json`. Find the session by `id`. Read `name`, `start`, `end`, `days`, `track_count`, `total_plays`, and every entry in `tracks[]` (title, date, plays, page).
2. Time-frame it: date span, and how it sits next to neighboring sessions. Sessions cluster by a **7-day upload gap rule** — upload dates, not recording dates (say so).
3. Who's in the room: scan titles for `ft.` / `w/` / `prod.` fragments, then pull `data/v1/circle.json` for any title-credited collaborator (`shared_transmissions`, `years_active`, `verified_notes`) and `data/v1/scene-figures.json` for producer-only figures (they are excluded from the circle by rule).
4. What the titles signal: cross each title word against `data/v1/codex.json` families ("The Modes", "The Cold", "Lucid States", …). The decoder page (`decoder.html`) runs this same matching — reuse its logic, don't re-derive it.
5. Place it in history: match the session dates to an era in `data/v1/artist.json` → `eras[]`.
6. Write the story in three moves: **when** (dates, gap context), **what** (the tracks, standout plays), **why it matters** (collaborators, codex signals, era position). Every claim must trace to an endpoint field.

## Worked example

`session-01` — "The January 3rd–8th Session" (2018-01-03 → 2018-01-08, 6 days, 2 tracks, 13,862 total plays):

- "Soul Shaking (prod. Fish Narc)" — 2018-01-03, plays. Fish Narc is a *scene figure*, not a circle member: producer credit only, documented in `scene-figures.json` (b. 1992 Seattle/Olympia; GothBoiClique; produced Lil Peep's *Goth Angel Sinner*). "Soul" sits in the codex family "Soul".
- "Lucid Boi (prod. $ T.N.C $)" — 2018-01-08, plays. "Lucid" sits in the codex family "Lucid States".
- Era: "The First Rite" (2017–2019). This is the opening session of the archived vault — the first cluster of the whole catalog.

## API references

- `data/v1/sessions.json` — 61 sessions, 7-day gap clustering, per-track plays
- `data/v1/session-clusters.json` — the same sessions precomputed for
  exploration: per-session enrichment (era, loudest + deepest-cut tracks,
  cross-links), the 60 inter-session gaps, the 9 activity seasons, asserted
  insights (drives `sessions-explorer.html`; see the `session-explorer` skill)
- `data/v1/circle.json` — 21 title-credited collaborators (`shared_transmissions`, `shared_plays`, `years_active`, `verified_notes`)
- `data/v1/scene-figures.json` — producer-only scene figures (outside the 21)
- `data/v1/codex.json` — 16 title-word families with per-family track lists
- `data/v1/artist.json` — `eras[]` for historical placement; `decoder.html` for the live decoder

## Pitfalls

- Upload dates are **not** recording dates. Never claim a track was recorded in its upload week.
- Sessions are computed clusters (7-day gap rule), not artist-named studio sessions. Say "clustered" when the distinction matters.
- If a collaborator isn't in `circle.json`, check `scene-figures.json` before concluding they're unknown — producers are excluded from the circle by rule, not by absence.
- Plays are a 2026-10-11 snapshot. Session "importance" is about the story, not the play rank.
- No invented color: no studio details, no moods, no quotes — unless an endpoint (or a cited source on a circle page) says it.
