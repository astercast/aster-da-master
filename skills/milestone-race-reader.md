---
name: milestone-race-reader
description: Read the milestone race (milestone-races.json) — approaching play-count milestones ranked by gap-closing proximity, race any two vault tracks head-to-head, The Climb (182-track summit leaderboard), race history, the computed race of the week, the play summit chase, session and era records. Pace figures are arithmetic, never predictions.
---

# Read the milestone race

## Use when

An agent needs the "race" view of the archive's milestones: which track is closest to its next round-number play count, which of ANY two vault tracks crosses a milestone target first, the full summit leaderboard, the decided races of the past, the computed race of the week, who can catch the "Take Me" 30,088 summit record, the standing session/era records, or what's most recently crossed. Feeds countdown content, "almost there" alerts, and record-watch briefs.

## Inputs

- `data/v1/milestone-races.json` (races + records, snapshot 2026-10-11)
- `data/v1/milestone-watch.json` (the raw bands + summit, if you need the pre-race arithmetic)
- `milestone-race.html` (the human-readable race page)

## Procedure

1. Fetch `data/v1/milestone-races.json`. Read `plays_snapshot` first — this is a snapshot, not a live leaderboard; state the date in every report.
2. Read `pace_definition` — `pace_per_day` is snapshot plays ÷ days from upload to snapshot (a lifetime average, not a current rate). `days_at_pace` and `catch_days_at_pace` are plain division: **estimates, never predictions. Say so out loud every time.**
3. Read `closest_races` — race ids sorted by `days_at_pace` ascending. Resolve each id through `play_races[]`: report `title`, `plays`, `milestone`, `needed`, and the pace figure with its "estimate, not a prediction" caveat. Each race also carries `producers[]` (name/slug/page) for producer-deep-dive links.
4. Read `vault_pace` — the pace database: all 185 vault tracks with lifetime `pace_per_day`, release `page`, and `producers[]`. To race any two tracks at any milestone target (1k/10k/20k/30k): `needed = target − plays`; `days_at_pace = needed ÷ pace_per_day` (round to 1, half-even); the smaller `days_at_pace` crosses first. A track already past the line has no race to run — say so, don't project. Read `head_to_head` for the 6 precomputed featured pairs (active races at their band targets, asserted) — the page's tool mirrors this exact math client-side. `projected_note` carries the uncertainty language — quote it, don't paraphrase it away.
5. Read `the_climb` — all 182 summit-eligible tracks ranked by `catch_days_at_pace` (top 5 = the summit contenders). Eligibility: uploaded before 2026-07-13 and still behind the holder — pace needs a track record.
6. Read `race_history` — the decided races. `completed_crossings`: all 8 dated milestone entries. `threshold_winners`: 1k/10k/20k/30k — `crossed_count` of vault tracks past each threshold and the current `leader`. **Crossing dates are not recorded** (one snapshot); never state or imply a finish order for these. `photo_finish`: the tightest back-to-back recorded crossings — "First vault transmission" vs "First collaboration", 115 days apart.
7. Read `race_of_the_week` — the closest active race, **computed from the snapshot, not chosen by an editor** (`basis`). Use `share_text` + `deep_link` (`milestone-race.html#watch`) for the share card; always attach the `caveat`.
8. Read `summit_race` — `holder` is "Take Me (prod. Em Klebold)" at plays; `contenders` are the five closest chasers by `catch_days_at_pace` (tracks uploaded before 2026-07-13 — pace needs a track record; see `eligibility`).
9. Read `session_records` / `era_records` for the standing records; `just_crossed` for the three most recently recorded milestones.
10. Read `snapshot_provenance` — the 2026-10-11 snapshot was independently re-captured via live browser (185/185 tracks, zero play-count differences). Cite it when asked how trustworthy the numbers are.
11. Every track carries a `page` (its release page). Use it for links; never invent URLs.

## Worked example

Snapshot 2026-10-11:

- Closest race: "master key ft. Lil Wintr x Marcelo (prod. ginseng)" — plays, closing at lifetime pace in ~100.3 days (estimate, not a prediction). Also the computed race of the week.
- Second: "When the World Gets Colder (prod. Brokn)" — close to its band, ~146.7 days at pace.
- Head-to-head: the closest featured pair is "master key" vs "When the World Gets Colder" — 46.4 days between projected finishes; "master key" projected first at lifetime pace (arithmetic, never a forecast). Any two of the 185 vault tracks can be raced at 1k/10k/20k/30k via `vault_pace`.
- The Climb: 182 summit-eligible tracks ranked by catch time; #1 "candy w/ capoxxo(prod. razorwrist)" at ~4,093.1 days, #182 slowest. Top 5 = the summit contenders.
- Race history: vault tracks past the lower bands; "Take Me" leads every band; photo finish — "First vault transmission" vs "First collaboration", 115 days apart.
- Summit: "Take Me (prod. Em Klebold)" plays. Closest contender: "candy w/ capoxxo(prod. razorwrist)" — plays, close behind, ~4,093.1 days at lifetime pace (estimate, not a prediction).
- Records: most-prolific session = The November 3rd–12th Session (19 tracks, session-40); longest silence = 553 days (session-36 → session-37); era with most plays = The First Rite.
- Just crossed: "Latest transmission" 2026-10-02; "plays crossed" 2024-05-28; "Most prolific day" 2023-11-12.

## API references

- `data/v1/milestone-races.json` — races, closest_races ranking, vault_pace (185-track pace database), head_to_head, the_climb (182-track leaderboard), race_history, race_of_the_week, snapshot_provenance, summit_race, records, just_crossed
- `data/v1/milestone-watch.json` — raw bands and summit this race is built from
- `data/v1/index.json` — registry; `plays_snapshot` provenance
- `milestone-race.html` — the human-readable race experience

## Pitfalls

- **Snapshot, not live.** Play counts drift daily. Never present a race as current without the snapshot date.
- **`days_at_pace` is not a forecast.** It's division of two snapshot numbers. Calling it a prediction is a data lie — the method section and the page say "estimate, not a prediction" and the skill must too.
- Pace is a lifetime average. Old, steady tracks and young tracks don't pace the same way — summit contenders carry a 90-day minimum age for exactly this reason.
- Don't conflate vault SoundCloud plays with distributor streams — these counts are the SoundCloud-only capture.
