---
name: deep-cuts-finder
description: Surface overlooked vault tracks — the quietest plays in the archive — for playlists, listens, and "you haven't heard this" moments.
---

# Find deep cuts in the vault

## Use when

An agent (or a human) wants the overlooked end of the catalog: deep-cut playlists, "tracks nobody found yet" listening sessions, or the opposite of a greatest-hits list. Not for ranking by quality — plays measure discovery, not worth.

## Inputs

- `api/v1/sessions.json` (per-track play counts, 2026-10-11 snapshot)
- A cutoff: how many tracks to return (default 10)
- Optional floor/ceiling: e.g. "between 100 and 500 plays" to skip one-listen accidents

## Procedure

1. Fetch `api/v1/sessions.json`. Flatten `sessions[].tracks` into one list of `{title, date, plays, page}`. (The 185 SoundCloud-only tracks are the ones with play counts; the 34 distributor releases have platform links, not vault plays.)
2. Sort ascending by `plays`. The median vault track sits around 450 plays — anything far below that is a genuine deep cut.
3. Take the bottom N (or the tracks inside your floor/ceiling window). Keep the date and release page link with each.
4. Optional: enrich each pick with `api/v1/codex.json` — the codex families explain what a title word signals, which gives a playlist theme to hang on.
5. Present as a list: title, plays, date, why it qualifies (e.g. "17 plays — the quietest transmission in the vault").

## Worked example

Bottom 5 of the 185-track vault (snapshot 2026-10-11):

- "nitemode2019 w/ Max+Vetty prod. NaXi.wav" — 17 plays
- "No Puppets A11owed prod. xtasane" — 24 plays
- "Im tha Bouncerrr prod. sustain" — 28 plays
- "For Brian (Neck Deep) outro [produced by AWFL]" — 43 plays
- "6 stop telling myself i'm not" — 46 plays

Median vault plays: ~450, so each of these sits at roughly a tenth of the median or less. All titles verbatim as uploaded; `.wav` in the first title is part of the original upload name.

## API references

- `api/v1/sessions.json` — the only per-track play-count source in the API (flatten `sessions[].tracks`)
- `api/v1/milestone-watch.json` — the mirror image: tracks *near* round numbers (approach milestones, not deep cuts)
- `api/v1/codex.json` — title-word families for playlist themes
- `api/v1/index.json` — registry + `plays_snapshot` provenance (`observed: 2026-10-11`)

## Pitfalls

- Play counts are a **snapshot** (2026-10-11), not live. Say the date; never present them as current.
- A low count is a discovery fact, not a quality judgment. Never frame a deep cut as "bad" or "failed."
- Titles are quoted verbatim only. **Never quote lyrics** — the archive is titles and metadata only.
- Don't mix vault plays with distributor streams: the 34 distributor releases don't carry per-track SoundCloud plays, so they can't be ranked the same way.
