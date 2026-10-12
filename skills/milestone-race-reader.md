---
name: milestone-race-reader
description: Read the milestone race (milestone-races.json) — approaching play-count milestones ranked by gap-closing proximity, the 30,088-play summit chase, session and era records, and the most recently crossed milestones. Pace figures are arithmetic, never predictions.
---

# Read the milestone race

## Use when

An agent needs the "race" view of the archive's milestones: which track is closest to its next round-number play count, who can catch the "Take Me" 30,088 summit record, the standing session/era records, or what's most recently crossed. Feeds countdown content, "almost there" alerts, and record-watch briefs.

## Inputs

- `api/v1/milestone-races.json` (races + records, snapshot 2026-10-11)
- `api/v1/milestone-watch.json` (the raw bands + summit, if you need the pre-race arithmetic)
- `milestone-race.html` (the human-readable race page)

## Procedure

1. Fetch `api/v1/milestone-races.json`. Read `plays_snapshot` first — this is a snapshot, not a live leaderboard; state the date in every report.
2. Read `pace_definition` — `pace_per_day` is snapshot plays ÷ days from upload to snapshot (a lifetime average, not a current rate). `days_at_pace` and `catch_days_at_pace` are plain division: **estimates, never predictions. Say so out loud every time.**
3. Read `closest_races` — race ids sorted by `days_at_pace` ascending. Resolve each id through `play_races[]`: report `title`, `plays`, `milestone`, `needed`, and the pace figure with its "estimate, not a prediction" caveat.
4. Read `summit_race` — `holder` is "Take Me (prod. Em Klebold)" at 30,088 plays; `contenders` are the five closest chasers by `catch_days_at_pace` (tracks uploaded before 2026-07-13 — pace needs a track record; see `eligibility`).
5. Read `session_records` / `era_records` for the standing records; `just_crossed` for the three most recently recorded milestones.
6. Every track carries a `page` (its release page). Use it for links; never invent URLs.

## Worked example

Snapshot 2026-10-11:

- Closest race: "master key ft. Lil Wintr x Marcelo (prod. ginseng)" — 9,615 of 10,000 plays, 385 needed, pace ~3.84 plays/day → at this lifetime pace, ~100.1 days (estimate, not a prediction).
- Second: "When the World Gets Colder (prod. Brokn)" — 9,535 of 10,000, 465 needed, ~146.6 days at pace.
- Summit: "Take Me (prod. Em Klebold)" 30,088 plays. Closest contender: "candy w/ capoxxo(prod. razorwrist)" — 11,587 plays, 18,501 behind, ~4,093.1 days at lifetime pace (estimate, not a prediction).
- Records: most-prolific session = The November 3rd–12th Session (19 tracks, session-40); longest silence = 553 days (session-36 → session-37); era with most plays = The First Rite (220,688).
- Just crossed: "Latest transmission" 2026-10-02; "250,000 plays crossed" 2024-05-28; "Most prolific day" 2023-11-12.

## API references

- `api/v1/milestone-races.json` — races, closest_races ranking, summit_race, records, just_crossed
- `api/v1/milestone-watch.json` — raw bands and summit this race is built from
- `api/v1/index.json` — registry; `plays_snapshot` provenance
- `milestone-race.html` — the human-readable race experience

## Pitfalls

- **Snapshot, not live.** Play counts drift daily. Never present a race as current without the snapshot date.
- **`days_at_pace` is not a forecast.** It's division of two snapshot numbers. Calling it a prediction is a data lie — the method section and the page say "estimate, not a prediction" and the skill must too.
- Pace is a lifetime average. Old, steady tracks and young tracks don't pace the same way — summit contenders carry a 90-day minimum age for exactly this reason.
- Don't conflate vault SoundCloud plays with distributor streams — these counts are the SoundCloud-only capture.
