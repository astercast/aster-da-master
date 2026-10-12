---
name: milestone-watcher
description: Track vault tracks approaching round-number play counts — who is close, how close, and to what — from the milestone-watch endpoint.
---

# Watch the play-count milestones

## Use when

An agent needs a "watch list": which tracks are closing in on 1,000 / 10,000 / 30,000 plays, and the archive's current highest-play transmission. Feeds milestone alerts, "almost there" posts, and countdown content.

## Inputs

- `api/v1/milestone-watch.json` (bands + summit, snapshot 2026-10-11)
- Optional: a band id (`near-1k`, `near-10k`, `near-30k`) to focus on

## Procedure

1. Fetch `api/v1/milestone-watch.json`. Read `plays_snapshot` first — this is a snapshot, not a live leaderboard; state the date in every report.
2. Read `summit` — the single highest-play vault transmission. That's the ceiling reference.
3. Walk each `bands[]` entry: `name`, `target`, `blurb`, and every track with `plays` and `needed` (plays still required to hit the target).
4. Sort the approaching tracks by `needed` ascending — the smallest `needed` is the closest to its milestone.
5. Report in three lines: **the summit** (ceiling), **the watch list** (band → tracks with plays and needed), **the quiet bands** (empty bands are a fact too — say so).

## Worked example

Snapshot 2026-10-11:

- Summit: "Take Me (prod. Em Klebold)" — 30,088 plays. The highest-play transmission in the vault; nothing else is within 3,000 plays of 30,000.
- Near 1,000 (`near-1k`, target 1000): "[outro] Off Beat ft. Yung Vetta (prod. Addy)" — 935 plays, 65 needed; "Lucid Boi (prod. $ T.N.C $)" — 918 plays, 82 needed.
- Near 10,000 (`near-10k`, target 10000): "master key ft. Lil Wintr x Marcelo (prod. ginseng)" — 9,615 plays, 385 needed.
- Near 30,000 (`near-30k`): empty — no track is near the summit's band.

## API references

- `api/v1/milestone-watch.json` — bands, summit, `needed` per track, snapshot date
- `api/v1/sessions.json` — full per-track play counts if you need to compute your own bands
- `api/v1/index.json` — registry; `plays_snapshot` provenance

## Pitfalls

- **Snapshot, not live.** Play counts drift daily. Never present a watch list as current without the snapshot date.
- An empty band is information ("nobody is near 30k"), not a data error.
- Don't conflate vault SoundCloud plays with distributor streams — these counts are the SoundCloud-only capture.
- `needed` is simple arithmetic on the snapshot (target − plays). It's not a prediction of when the milestone lands.
